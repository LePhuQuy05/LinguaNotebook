"""HPDFParser generation-config tests.

Pins the generation contract that keeps OCR usable on Intel Arc XPU:
P-MTP speculative decoding ON (measured ~6.8x faster, 2026-08-01) plus the
repetition safeguards that were added when MTP was disabled — and that make
MTP safe to re-enable (greedy verification keeps output identical).
"""

import types

import pytest
import torch


class FakeGenerateModel:
    """Records the generate_hpd kwargs and returns canned markdown."""

    def __init__(self):
        self.device = torch.device("cpu")
        self.calls = []
        self.mtp = True  # load_mtp_weights() no-op

    def eval(self):
        return self

    def load_mtp_weights(self):
        pass

    def generate_hpd(self, **kwargs):
        self.calls.append(kwargs)
        return "# fake page"


@pytest.fixture
def parser():
    from src.utils.hpd_parser import HPDFParser

    p = HPDFParser(model_dir="./model", use_gpu=False)
    p._loaded = True
    p.tokenizer = types.SimpleNamespace(pad_token_id=0)
    p.model = FakeGenerateModel()
    return p


def test_generation_uses_mtp_speculative_decoding(parser, monkeypatch):
    """P-MTP must stay enabled — disabling it costs ~6.8x throughput."""
    monkeypatch.setattr(
        parser,
        "_preprocess_image",
        lambda img: torch.zeros(1, 3, 448, 448),
    )

    parser.parse_page(object(), page_num=1)

    call = parser.model.calls[0]
    assert call["use_mtp"] is True


def test_generation_keeps_repetition_safeguards(parser, monkeypatch):
    """The penalties that prevent MTP degeneration must stay in place."""
    monkeypatch.setattr(
        parser,
        "_preprocess_image",
        lambda img: torch.zeros(1, 3, 448, 448),
    )

    parser.parse_page(object(), page_num=1)

    gen = parser.model.calls[0]["generation_config"]
    assert gen["repetition_penalty"] == 1.15
    assert gen["no_repeat_ngram_size"] == 10
