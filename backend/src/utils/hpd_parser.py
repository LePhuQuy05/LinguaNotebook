"""HPD-Parsing wrapper — PDF → structured markdown.

Implements the pipeline from HPD-PARSING-GUIDE.md:
  PyMuPDF render → PIL Image → Dynamic tiling (448×448) → HPD inference → Markdown

Supports CPU and GPU execution paths.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

import fitz  # PyMuPDF
import torch
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class ProgressInfo:
    """Progress emitted after each page during parsing."""
    status: str = "running"
    current_page: int = 0
    total_pages: int = 0
    elapsed_sec: float = 0.0
    eta_sec: float = 0.0
    pages_per_sec: float = 0.0
    errors: list = field(default_factory=list)


class HPDFParser:
    """Parse PDF page-by-page using the HPD model.

    The model is loaded once and kept resident in memory.
    Supports: CUDA (NVIDIA), XPU (Intel Arc), CPU (fallback).

    Per HPD-PARSING-GUIDE.md Section 2.2, 3.1, 7.3
    """

    def __init__(self, model_dir: str = "./model", use_gpu: bool = False, gpu_type: str = "cuda"):
        self.model_dir = model_dir
        self.use_gpu = use_gpu
        self.gpu_type = gpu_type  # "cuda" for NVIDIA, "xpu" for Intel Arc
        self.model = None
        self.tokenizer = None
        self._loaded = False

    def load_model(self) -> None:
        """Load HPD model and tokenizer. Called once at worker startup.

        Per guide: use_fast=False on tokenizer, attn_implementation='eager'
        for non-CUDA, load_mtp_weights() after loading.
        """
        import sys
        sys.path.insert(0, self.model_dir)

        from transformers import AutoModel, AutoTokenizer

        logger.info(f"Loading HPD model from {self.model_dir}...")
        t0 = time.time()

        # Tokenizer: use_fast=False is CRITICAL (guide §3.3)
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_dir, trust_remote_code=True, use_fast=False,
        )

        # Model: always eager attention for safety (guide §7.3)
        self.model = AutoModel.from_pretrained(
            self.model_dir,
            trust_remote_code=True,
            dtype=torch.bfloat16,
            attn_implementation="eager",
        )

        # Move to GPU (guide §3.1)
        if self.use_gpu:
            if self.gpu_type == "xpu" and hasattr(torch, 'xpu') and torch.xpu.is_available():
                self.model = self.model.to("xpu")
                logger.info("HPD model loaded on Intel XPU GPU")
            elif torch.cuda.is_available():
                self.model = self.model.to("cuda")
                logger.info("HPD model loaded on NVIDIA CUDA GPU")
            else:
                self.model = self.model.to("cpu")
                logger.warning("GPU requested but not available, using CPU")
        else:
            self.model = self.model.to("cpu")
            logger.info("HPD model loaded on CPU")

        self.model.eval()
        self.model.load_mtp_weights()  # Activate P-MTP (guide §3.1)
        self._loaded = True

        logger.info(f"HPD model ready in {time.time() - t0:.1f}s")

    def _preprocess_image(self, pil_image: Image.Image) -> torch.Tensor:
        """PIL Image → tile tensor (same logic as image_preprocess.load_image)."""
        from image_preprocess import (
            MIN_DYNAMIC_PATCH,
            MAX_DYNAMIC_PATCH,
            USE_THUMBNAIL,
            IMAGE_SIZE,
            get_target_ratios,
            dynamic_preprocess,
            build_transform,
        )

        min_num, max_num = MIN_DYNAMIC_PATCH, MAX_DYNAMIC_PATCH
        if USE_THUMBNAIL and max_num != 1:
            max_num += 1

        target_ratios = get_target_ratios(min_num, max_num)
        transform = build_transform(IMAGE_SIZE)
        tiles = dynamic_preprocess(pil_image, target_ratios, IMAGE_SIZE, USE_THUMBNAIL)
        return torch.stack([transform(t) for t in tiles])

    def parse_page(self, pil_image: Image.Image, page_num: int, max_tokens: int = 2048) -> str:
        """Parse a single page image. Returns markdown text."""
        if not self._loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        pixel_values = self._preprocess_image(pil_image)
        pixel_values = pixel_values.to(
            dtype=torch.bfloat16, device=self.model.device
        )
        num_tiles = pixel_values.shape[0]

        gen_config = dict(
            max_new_tokens=max_tokens,
            do_sample=False,
            num_beams=1,
            pad_token_id=self.tokenizer.pad_token_id,
            repetition_penalty=1.15,
            no_repeat_ngram_size=10,
        )

        with torch.no_grad():
            result = self.model.generate_hpd(
                tokenizer=self.tokenizer,
                pixel_values=pixel_values,
                question="Parse this document page into structured markdown. "
                         "Identify and label: headers, paragraphs, tables (use |--| format), "
                         "numbered lists, image captions, page numbers, and footers. "
                         "For tables, output as markdown tables with | col1 | col2 | format. "
                         "Preserve the original language exactly — do not translate.",
                generation_config=gen_config,
                use_mtp=False,
                num_patches_list=[num_tiles],
                verbose=False,
            )

        del pixel_values
        if result is None:
            raise RuntimeError("HPD model returned None — page may be blank or unsupported format")
        return result

    def parse_pdf(
        self,
        pdf_path: str,
        page_start: int = 1,
        page_end: Optional[int] = None,
        dpi: int = 100,
        max_tokens: int = 4096,
        progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> tuple[str, list[tuple[int, str]]]:
        """Parse a full PDF. Returns (combined_markdown, errors).

        Errors are (page_number, error_message) tuples.
        """
        doc = fitz.open(pdf_path)
        total = doc.page_count

        start = max(1, page_start) - 1
        end = min(page_end or total, total)
        to_process = end - start

        results: list[tuple[int, str]] = []
        errors: list[tuple[int, str]] = []
        t_start = time.time()

        for idx in range(start, end):
            if cancel_check and cancel_check():
                logger.info("Parse cancelled by user")
                break
            page_num = idx + 1
            try:
                page = doc.load_page(idx)
                zoom = dpi / 72
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                pix = None
                page = None

                text = self.parse_page(img, page_num, max_tokens)
                results.append((page_num, text))

            except Exception as exc:
                import traceback
                errors.append((page_num, f"{exc}\n{traceback.format_exc()}"))
                logger.error(f"Page {page_num} failed: {exc}")

            finally:
                if "pixel_values" in dir():
                    del pixel_values
                if "img" in dir():
                    del img
                if idx % 10 == 9:
                    if self.gpu_type == "xpu" and hasattr(torch, 'xpu'):
                        torch.xpu.empty_cache()
                    elif torch.cuda.is_available():
                        torch.cuda.empty_cache()

            if progress_callback:
                elapsed = time.time() - t_start
                done = len(results) + len(errors)
                pps = done / elapsed if elapsed > 0 else 0
                left = to_process - done
                info = ProgressInfo(
                    status="running",
                    current_page=done,
                    total_pages=to_process,
                    elapsed_sec=elapsed,
                    eta_sec=(left / pps) if pps > 0 else 0,
                    pages_per_sec=pps,
                    errors=list(errors),
                )
                progress_callback(info)

        doc.close()

        # Combine into final markdown
        parts: list[str] = []
        for pn, text in results:
            parts.append(f"\n--- Page {pn} ---\n")
            parts.append(text)
            parts.append("")

        if errors:
            parts.append("\n--- Parsing Errors ---\n")
            for pn, msg in errors:
                short = msg.split("\n")[0][:200]
                parts.append(f"- **Page {pn}**: {short}\n")

        return "".join(parts), errors
