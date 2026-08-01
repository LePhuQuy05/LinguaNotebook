"""Parse routing tests — the single OCR route (spec 006, ticket 04).

Guards the ticket's core acceptance: parse routing has exactly two branches
(text layer → PyMuPDF, otherwise → HPD) and no Marker/hybrid/Qwen-VL branch
is reachable — whatever the (compat-only) `mode` parameter carries.
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

        def parse_pdf(self, pdf_path, page_start=1, page_end=None, dpi=100,
                      max_tokens=2048, progress_callback=None, cancel_check=None):
            return "# fake md", []

    module = types.ModuleType("src.utils.hpd_parser")
    module.HPDFParser = FakeHPD
    monkeypatch.setitem(sys.modules, "src.utils.hpd_parser", module)


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
        pdf_parser, "extract_text_pymupdf",
        lambda *a, **k: ("md", []),
    )


def test_text_layer_routes_to_pymupdf(text_layer_pdf, monkeypatch):
    calls: dict[str, tuple] = {}

    def fake_extract(pdf_path, page_start=1, page_end=None,
                     progress_callback=None, cancel_check=None):
        calls["args"] = (pdf_path, page_start, page_end)
        return "extracted md", []

    monkeypatch.setattr(pdf_parser, "extract_text_pymupdf", fake_extract)

    markdown, errors, method = pdf_parser.parse_pdf_hybrid(
        "/book.pdf", page_start=2, page_end=5,
    )

    assert method == "text_layer"
    assert markdown == "extracted md"
    assert errors == []
    assert calls["args"] == ("/book.pdf", 2, 5)


def test_scanned_pdf_routes_to_hpd(scanned_pdf, stub_hpd, unreachable_parser_modules):
    markdown, errors, method = pdf_parser.parse_pdf_hybrid("/scan.pdf")

    assert method == "ocr"
    assert markdown == "# fake md"
    assert errors == []


@pytest.mark.parametrize("mode", ["fast", "balanced", "hybrid", "hpd", "garbage"])
def test_mode_is_ignored_for_scanned_pdfs(scanned_pdf, stub_hpd,
                                          unreachable_parser_modules, mode):
    _, _, method = pdf_parser.parse_pdf_hybrid("/scan.pdf", mode=mode)

    assert method == "ocr"


@pytest.mark.parametrize("mode", ["fast", "balanced", "hybrid"])
def test_mode_is_ignored_for_text_pdfs(text_layer_extraction,
                                       unreachable_parser_modules, mode):
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


def test_has_text_layer_true_for_text_pdf(tmp_path):
    assert pdf_parser._has_text_layer(_make_text_pdf(str(tmp_path / "text.pdf"))) is True


def test_has_text_layer_false_for_blank_pdf(tmp_path):
    assert pdf_parser._has_text_layer(_make_blank_pdf(str(tmp_path / "blank.pdf"))) is False


def test_has_text_layer_false_for_unreadable_path():
    assert pdf_parser._has_text_layer("nonexistent.pdf") is False


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
        pdf, page_start=1, page_end=2, progress_callback=seen.append,
    )

    assert errors == []
    assert len(seen) == 2
    assert seen[0].current_page == 1 and seen[0].total_pages == 2
    assert seen[1].current_page == 2 and seen[1].total_pages == 2


def test_extract_text_pymupdf_stops_on_cancel(tmp_path):
    pdf = _make_text_pdf(str(tmp_path / "book.pdf"), pages=5)

    markdown, errors = pdf_parser.extract_text_pymupdf(
        pdf, cancel_check=lambda: True,
    )

    assert errors == []
    assert markdown == ""
