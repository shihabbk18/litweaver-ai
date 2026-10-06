from pathlib import Path

import pandas as pd
import pymupdf
import pytest

from litweaver.pdf import MAX_BYTES, extract_pdf_text
from litweaver.reports import bibtex_export, critic_report, csv_export
from litweaver.verification import analyze_document


def pdf_bytes(text="", pages=1, encrypted=False):
    with pymupdf.open() as doc:
        for _ in range(pages):
            page = doc.new_page()
            page.insert_text((50, 50), text)
        return doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="secret") if encrypted else doc.tobytes()


def test_pdf_provenance_and_page():
    doc = extract_pdf_text(pdf_bytes("Model A accuracy = 92.0%."), "../../paper.pdf")
    assert doc.name == "paper.pdf"
    assert len(doc.sha256) == 64
    assert doc.evidence[0].page == 1
    assert "92.0" in doc.evidence[0].text


@pytest.mark.parametrize("value,match", [(b"not a pdf", "valid PDF"), (b"%PDF-"+b"0"*MAX_BYTES, "15 MB"), (pdf_bytes(pages=61), "60"), (pdf_bytes(encrypted=True), "Password")], ids=["invalid", "oversized", "too-many-pages", "encrypted"])
def test_bounded_pdf_failures(value, match):
    with pytest.raises(ValueError, match=match):
        extract_pdf_text(value)


def test_scanned_or_empty_pdf_reports_limitation():
    doc = extract_pdf_text(pdf_bytes())
    assert not doc.evidence
    assert any("OCR" in w for w in doc.warnings)


def test_sample_pdf_end_to_end():
    path = Path(__file__).parents[1]/"examples"/"numerical-audit.pdf"
    doc = extract_pdf_text(path.read_bytes(), path.name)
    results = analyze_document(doc)
    assert any(r.verdict.value == "CONTRADICTED" and "higher" in r.claim.text for r in results)
    assert any(r.verdict.value == "CONTRADICTED" and "improved by 12%" in r.claim.text for r in results)
    assert any(e.kind == "table" for e in doc.evidence)
    report = critic_report(doc, results)
    assert "page 2" in report
    assert doc.sha256 in report


def test_exports_defend_csv_formula_injection():
    data = csv_export(pd.DataFrame({"Title":["=HYPERLINK(\"malicious\")", "Normal title"]})).decode("utf-8-sig")
    assert "'=HYPERLINK" in data
    assert "Normal title" in data
