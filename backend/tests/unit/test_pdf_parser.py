"""Parse routing tests — the single OCR route (spec 006, ticket 04).

Guards the ticket's core acceptance: parse routing has exactly two branches
(text layer → PyMuPDF, otherwise → OCR backend) and no Marker/hybrid/Qwen-VL
branch is reachable — whatever the (compat-only) `mode` parameter carries.
The OCR backend itself is config-switchable: local HPD vs PaddleOCR-VL cloud
(OCR_BACKEND setting) — routing tests pin the backend so they never touch
the network or torch.
"""

import sys
import types

import fitz
import pytest

from src.services import pdf_parser


class _UnimportableModule:
    """Module stub whose every attribute access raises ImportError.

    Installed under the Marker/Qwen-VL module names so that any surviving
    import in the parse path fails loudly instead of silently degrading.
    """

    def __getattr__(self, name):
        raise ImportError("module must not be imported by the parse path")


@pytest.fixture
def unreachable_parser_modules(monkeypatch):
    """Make Marker/Qwen-VL imports fail if the parse path ever touches them."""
    for name in ("src.services.marker_parser", "src.services.qwen_vlm_parser"):
        monkeypatch.setitem(sys.modules, name, _UnimportableModule())


@pytest.fixture
def stub_hpd(monkeypatch):
    """Stub HPDFParser so routing tests never import torch-backed hpd_parser."""

    class FakeHPD:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def load_model(self):
            pass

        def parse_pdf(
            self,
            pdf_path,
            page_start=1,
            page_end=None,
            dpi=100,
            max_tokens=2048,
            progress_callback=None,
            cancel_check=None,
        ):
            return "# fake md", []

    module = types.ModuleType("src.utils.hpd_parser")
    module.HPDFParser = FakeHPD
    monkeypatch.setitem(sys.modules, "src.utils.hpd_parser", module)


@pytest.fixture
def stub_paddle(monkeypatch):
    """Stub PaddleOcrService so routing tests never hit the network."""

    calls: dict[str, tuple] = {}

    class FakePaddle:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def parse_pdf(
            self,
            pdf_path,
            page_start=1,
            page_end=None,
            dpi=100,
            max_tokens=2048,
            progress_callback=None,
            cancel_check=None,
        ):
            calls["args"] = (pdf_path, page_start, page_end, dpi, max_tokens)
            return "# paddle md", []

    module = types.ModuleType("src.services.paddle_ocr_service")
    module.PaddleOcrService = FakePaddle
    monkeypatch.setitem(sys.modules, "src.services.paddle_ocr_service", module)
    return calls


@pytest.fixture
def local_backend(monkeypatch):
    monkeypatch.setattr(pdf_parser, "_ocr_backend", lambda: "local")


@pytest.fixture
def paddle_backend(monkeypatch):
    monkeypatch.setattr(pdf_parser, "_ocr_backend", lambda: "paddle")


@pytest.fixture
def text_layer_pdf(monkeypatch):
    """A PDF that reports an embedded text layer."""
    monkeypatch.setattr(pdf_parser, "_has_text_layer", lambda path: True)


@pytest.fixture
def scanned_pdf(monkeypatch):
    """A PDF that reports no embedded text layer."""
    monkeypatch.setattr(pdf_parser, "_has_text_layer", lambda path: False)


@pytest.fixture
def text_layer_extraction(monkeypatch):
    """Text-layer PDF whose extraction returns a canned result."""
    monkeypatch.setattr(pdf_parser, "_has_text_layer", lambda path: True)
    monkeypatch.setattr(
        pdf_parser,
        "extract_text_pymupdf",
        lambda *a, **k: ("md", []),
    )


def test_text_layer_routes_to_pymupdf(text_layer_pdf, monkeypatch):
    calls: dict[str, tuple] = {}

    def fake_extract(
        pdf_path, page_start=1, page_end=None, progress_callback=None, cancel_check=None
    ):
        calls["args"] = (pdf_path, page_start, page_end)
        return "extracted md", []

    monkeypatch.setattr(pdf_parser, "extract_text_pymupdf", fake_extract)

    markdown, errors, method = pdf_parser.parse_pdf_hybrid(
        "/book.pdf",
        page_start=2,
        page_end=5,
    )

    assert method == "text_layer"
    assert markdown == "extracted md"
    assert errors == []
    assert calls["args"] == ("/book.pdf", 2, 5)


def test_scanned_pdf_routes_to_hpd(
    scanned_pdf, stub_hpd, local_backend, unreachable_parser_modules
):
    markdown, errors, method = pdf_parser.parse_pdf_hybrid("/scan.pdf")

    assert method == "ocr"
    assert markdown == "# fake md"
    assert errors == []


@pytest.mark.parametrize("mode", ["fast", "balanced", "hybrid", "hpd", "garbage"])
def test_mode_is_ignored_for_scanned_pdfs(
    scanned_pdf, stub_hpd, local_backend, unreachable_parser_modules, mode
):
    _, _, method = pdf_parser.parse_pdf_hybrid("/scan.pdf", mode=mode)

    assert method == "ocr"


def test_scanned_pdf_routes_to_paddle_cloud(
    scanned_pdf, stub_paddle, paddle_backend, unreachable_parser_modules
):
    markdown, errors, method = pdf_parser.parse_pdf_hybrid(
        "/scan.pdf",
        page_start=1,
        page_end=None,
        dpi=150,
    )

    assert method == "ocr"
    assert markdown == "# paddle md"
    assert errors == []


def test_paddle_receives_parse_arguments(
    scanned_pdf, stub_paddle, paddle_backend, unreachable_parser_modules
):
    calls = stub_paddle

    pdf_parser.parse_pdf_hybrid("/scan.pdf", page_start=2, page_end=5, dpi=150)

    assert calls["args"] == ("/scan.pdf", 2, 5, 150, 2048)


def test_auto_backend_picks_paddle_when_token_configured(
    scanned_pdf, stub_paddle, monkeypatch, unreachable_parser_modules
):
    from src.core.config import settings

    monkeypatch.setattr(settings, "ocr_backend", "auto")
    monkeypatch.setattr(settings, "paddle_ocr_token", "secret")

    _, _, method = pdf_parser.parse_pdf_hybrid("/scan.pdf")

    assert method == "ocr"


def test_auto_backend_picks_local_without_token(
    scanned_pdf, stub_hpd, monkeypatch, unreachable_parser_modules
):
    from src.core.config import settings

    monkeypatch.setattr(settings, "ocr_backend", "auto")
    monkeypatch.setattr(settings, "paddle_ocr_token", "")

    markdown, _, method = pdf_parser.parse_pdf_hybrid("/scan.pdf")

    assert method == "ocr"
    assert markdown == "# fake md"


def test_paddle_never_imported_for_text_pdfs(
    text_layer_extraction, unreachable_parser_modules, monkeypatch
):
    monkeypatch.setitem(sys.modules, "src.services.paddle_ocr_service", _UnimportableModule())

    markdown, _, method = pdf_parser.parse_pdf_hybrid("/book.pdf")

    assert method == "text_layer"
    assert markdown == "md"


@pytest.mark.parametrize("mode", ["fast", "balanced", "hybrid"])
def test_mode_is_ignored_for_text_pdfs(text_layer_extraction, unreachable_parser_modules, mode):
    _, _, method = pdf_parser.parse_pdf_hybrid("/book.pdf", mode=mode)

    assert method == "text_layer"


def test_hpd_never_imported_for_text_pdfs(text_layer_extraction, monkeypatch):
    """The HPD branch must not be reached when a text layer exists."""
    monkeypatch.setitem(sys.modules, "src.utils.hpd_parser", _UnimportableModule())

    markdown, _, method = pdf_parser.parse_pdf_hybrid("/book.pdf")

    assert method == "text_layer"
    assert markdown == "md"


# ---------------------------------------------------------------------------
# Real-PDF behaviour (fitz generates tiny PDFs in-memory)
# ---------------------------------------------------------------------------


def _make_text_pdf(path: str, pages: int = 2) -> str:
    """Generate a PDF with an embedded text layer (ASCII only)."""
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Hello page {i + 1} " * 20)
    doc.save(path)
    doc.close()
    return path


def _make_blank_pdf(path: str) -> str:
    """Generate a scanned-style PDF (pages with no text layer)."""
    doc = fitz.open()
    doc.new_page()
    doc.save(path)
    doc.close()
    return path


def _make_scan_pdf(path: str, text: str, pages: int = 3, image: bool = True) -> str:
    """Generate a scanned-style PDF: a full-page raster image with an
    embedded text layer on top (the CHOUKAI structure — scan + baked-in
    OCR). Text is drawn on several lines so enough of it lands inside the
    page for the quality gate to judge."""
    doc = fitz.open()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 600, 200))
    pix.clear_with(200)  # a non-black solid background
    for _ in range(pages):
        page = doc.new_page(width=600, height=200)
        if image:
            page.insert_image(page.rect, pixmap=pix)
        for ln in range(3):
            page.insert_text((5, 40 + ln * 40), text, fontsize=10)
    doc.save(path)
    doc.close()
    return path


GARBAGE_TEXT = "tf=fv7r- E6=EfrWt=ilfiffi +filr)*D' t'J' iEEffifE' EfiA'H7"
CLEAN_TEXT = "Hello world, this is a normal page of embedded text."


def test_has_text_layer_true_for_text_pdf(tmp_path):
    assert pdf_parser._has_text_layer(_make_text_pdf(str(tmp_path / "text.pdf"))) is True


def test_has_text_layer_false_for_blank_pdf(tmp_path):
    assert pdf_parser._has_text_layer(_make_blank_pdf(str(tmp_path / "blank.pdf"))) is False


def test_has_text_layer_false_for_unreadable_path():
    assert pdf_parser._has_text_layer("nonexistent.pdf") is False


def test_has_text_layer_routes_garbage_scan_to_ocr(tmp_path):
    """A scanned page whose embedded text layer is noise (bad baked-in
    OCR) must not be trusted — route it to the OCR backend."""
    pdf = _make_scan_pdf(str(tmp_path / "garbage.pdf"), GARBAGE_TEXT)

    assert pdf_parser._has_text_layer(pdf) is False


def test_has_text_layer_keeps_clean_scan_with_good_embedded_text(tmp_path):
    """A searchable scan (clean embedded OCR text over the image) is a
    genuine text layer — keep it."""
    pdf = _make_scan_pdf(str(tmp_path / "searchable.pdf"), CLEAN_TEXT)

    assert pdf_parser._has_text_layer(pdf) is True


def test_has_text_layer_keeps_noisy_text_without_image(tmp_path):
    """Noise text on a digital page (no raster image) is not a scan —
    keep the text layer. Guards code/math-heavy digital books."""
    pdf = _make_scan_pdf(str(tmp_path / "noimage.pdf"), GARBAGE_TEXT, image=False)

    assert pdf_parser._has_text_layer(pdf) is True


def test_garbage_scan_routes_through_parse_to_ocr(
    tmp_path, stub_paddle, paddle_backend, unreachable_parser_modules
):
    """End to end: a garbage-text-layer scan ends up on the OCR backend,
    not PyMuPDF."""
    pdf = _make_scan_pdf(str(tmp_path / "garbage.pdf"), GARBAGE_TEXT)

    markdown, errors, method = pdf_parser.parse_pdf_hybrid(pdf)

    assert method == "ocr"
    assert markdown == "# paddle md"
    assert errors == []


def test_page_image_fraction_full_page(tmp_path):
    pdf = _make_scan_pdf(str(tmp_path / "scan.pdf"), CLEAN_TEXT)
    doc = fitz.open(pdf)
    frac = pdf_parser._page_image_fraction(doc[0])
    doc.close()

    assert frac >= 0.9


def test_page_image_fraction_no_images(tmp_path):
    pdf = _make_text_pdf(str(tmp_path / "text.pdf"))
    doc = fitz.open(pdf)
    frac = pdf_parser._page_image_fraction(doc[0])
    doc.close()

    assert frac == 0.0


def test_extract_text_pymupdf_produces_page_markers(tmp_path):
    pdf = _make_text_pdf(str(tmp_path / "book.pdf"), pages=2)

    markdown, errors = pdf_parser.extract_text_pymupdf(pdf)

    assert errors == []
    assert markdown.count("--- Page") == 2
    assert "--- Page 1 ---" in markdown
    assert "--- Page 2 ---" in markdown
    assert "Hello page 1" in markdown


def test_extract_text_pymupdf_reports_progress(tmp_path):
    pdf = _make_text_pdf(str(tmp_path / "book.pdf"), pages=3)
    seen: list[object] = []

    _, errors = pdf_parser.extract_text_pymupdf(
        pdf,
        page_start=1,
        page_end=2,
        progress_callback=seen.append,
    )

    assert errors == []
    assert len(seen) == 2
    assert seen[0].current_page == 1 and seen[0].total_pages == 2
    assert seen[1].current_page == 2 and seen[1].total_pages == 2


def test_extract_text_pymupdf_stops_on_cancel(tmp_path):
    pdf = _make_text_pdf(str(tmp_path / "book.pdf"), pages=5)

    markdown, errors = pdf_parser.extract_text_pymupdf(
        pdf,
        cancel_check=lambda: True,
    )

    assert errors == []
    assert markdown == ""
