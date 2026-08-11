"""PaddleOCR-VL cloud service tests.

Pins the job lifecycle contract: submit → poll (pending/running/done) →
JSONL download → `--- Page N ---` markdown. HTTP is mocked — the API is
external and the bearer token is a secret that must never leave .env.
"""

import json

import pytest

import src.services.paddle_ocr_service as svc

TWO_PAGE_JSONL = (
    '{"result": {"layoutParsingResults": [{"markdown": {"text": '
    '"# 表紙\\n日本語のテキストです。"}}]}}\n'
    '{"result": {"layoutParsingResults": [{"markdown": {"text": '
    '"| a | b |\\n| --- | --- |\\n| c | d |"}}]}}\n'
)


def _line(text: str) -> str:
    return json.dumps({"result": {"layoutParsingResults": [{"markdown": {"text": text}}]}})


THREE_PAGE_JSONL = "\n".join(_line(f"page {n} text") for n in (1, 2, 3)) + "\n"


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        if self._json is None:
            raise ValueError("no json payload")
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise svc.PaddleOcrError(f"HTTP {self.status_code}: {self.text[:200]}")


class FakeClient:
    """httpx.Client stand-in: records calls, `get` pops a response queue."""

    def __init__(self, post_response=None, get_responses=None):
        self.post_response = post_response or FakeResponse(json_data={"data": {"jobId": "job-1"}})
        self.get_responses = list(get_responses or [])
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, **kwargs):
        self.calls.append(("post", url, kwargs))
        # Consume the multipart file now (httpx would read it during send;
        # the caller's `with open()` closes it afterwards).
        self.uploaded = {
            name: (fname, data.read(), ctype)
            for name, (fname, data, ctype) in kwargs.get("files", {}).items()
        }
        return self.post_response

    def get(self, url, **kwargs):
        self.calls.append(("get", url, kwargs))
        return self.get_responses.pop(0)


@pytest.fixture
def fake_http(monkeypatch):
    """Install a FakeClient factory and zero the poll sleep."""

    def install(post_response=None, get_responses=None):
        client = FakeClient(post_response=post_response, get_responses=get_responses)
        monkeypatch.setattr(svc.httpx, "Client", lambda *a, **k: client)
        return client

    monkeypatch.setattr(svc, "POLL_INTERVAL_SEC", 0)
    return install


def _done(total_pages: int, jsonl_url: str = "https://example.com/result.jsonl") -> dict:
    return {
        "state": "done",
        "extractProgress": {"totalPages": total_pages, "extractedPages": total_pages},
        "resultUrl": {"jsonUrl": jsonl_url},
    }


def test_full_job_lifecycle_builds_page_markdown(fake_http, tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    client = fake_http(
        get_responses=[
            FakeResponse(json_data={"data": {"state": "pending"}}),
            FakeResponse(
                json_data={
                    "data": {
                        "state": "running",
                        "extractProgress": {"totalPages": 2, "extractedPages": 1},
                    }
                }
            ),
            FakeResponse(json_data={"data": _done(2)}),
            FakeResponse(text=TWO_PAGE_JSONL),
        ]
    )
    progress = []

    markdown, errors = svc.PaddleOcrService(token="secret").parse_pdf(
        str(pdf),
        progress_callback=progress.append,
    )

    assert errors == []
    assert "--- Page 1 ---" in markdown
    assert "--- Page 2 ---" in markdown
    assert "| a | b |" in markdown

    # submit went out with bearer auth + the pdf bytes as multipart file
    post_url, post_kwargs = client.calls[0][1], client.calls[0][2]
    assert post_url == svc.settings.paddle_ocr_job_url
    assert post_kwargs["headers"] == {"Authorization": "bearer secret"}
    assert post_kwargs["data"]["model"] == "PaddleOCR-VL-1.6"
    assert client.uploaded["file"][0] == "document.pdf"
    assert client.uploaded["file"][1] == b"%PDF-1.4 fake"

    # one progress event, mirroring the API's extracted/total pages
    assert [(p.current_page, p.total_pages) for p in progress] == [(1, 2)]
    assert progress[0].status == "running"


def test_failed_job_reports_error_without_raising(fake_http, tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF")

    fake_http(
        get_responses=[
            FakeResponse(json_data={"data": {"state": "failed", "errorMsg": "out of quota"}}),
        ]
    )

    markdown, errors = svc.PaddleOcrService(token="t").parse_pdf(str(pdf))

    assert markdown == ""
    assert "out of quota" in errors[0][1]


def test_missing_token_raises_before_any_request(fake_http, tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF")

    with pytest.raises(svc.PaddleOcrError, match="PADDLE_OCR_TOKEN"):
        svc.PaddleOcrService(token="").parse_pdf(str(pdf))


def test_cancel_stops_polling_with_error(fake_http, tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF")

    fake_http(get_responses=[FakeResponse(json_data={"data": {"state": "running"}})])

    markdown, errors = svc.PaddleOcrService(token="t").parse_pdf(
        str(pdf),
        cancel_check=lambda: True,
    )

    assert markdown == ""
    assert any("cancelled" in msg.lower() for _, msg in errors)


def test_page_range_slices_pdf_and_offsets_markers(fake_http, tmp_path):
    import fitz

    doc = fitz.open()
    for i in range(5):
        page = doc.new_page(width=200, height=200)
        page.insert_text((20, 40), f"page {i + 1}")
    pdf = tmp_path / "five.pdf"
    doc.save(str(pdf))
    doc.close()

    fake_http(
        get_responses=[
            FakeResponse(json_data={"data": _done(3)}),
            FakeResponse(text=THREE_PAGE_JSONL),
        ]
    )

    markdown, errors = svc.PaddleOcrService(token="t").parse_pdf(
        str(pdf),
        page_start=3,
        page_end=5,
    )

    assert errors == []
    assert "--- Page 3 ---" in markdown
    assert "--- Page 5 ---" in markdown
    assert "--- Page 2 ---" not in markdown


def test_malformed_result_lines_become_errors(fake_http, tmp_path):
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF")

    bad_jsonl = (
        '{"result": {"layoutParsingResults": [{"markdown": {"text": "ok"}}]}}\n'
        "not json at all\n"
        '{"result": {"layoutParsingResults": []}}\n'
    )
    fake_http(
        get_responses=[
            FakeResponse(json_data={"data": _done(3)}),
            FakeResponse(text=bad_jsonl),
        ]
    )

    markdown, errors = svc.PaddleOcrService(token="t").parse_pdf(str(pdf))

    assert "--- Page 1 ---" in markdown  # good line survived
    assert markdown.count("--- Page") == 1
    assert len(errors) >= 2  # malformed line + missing page
    assert any("malformed JSONL" in msg for _, msg in errors)
