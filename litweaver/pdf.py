"""Bounded PDF extraction; no OCR, execution, or guessed table reconstruction."""
import hashlib
import re
import time
from pathlib import Path

import pymupdf

from .models import Document, Evidence

MAX_BYTES = 15 * 1024 * 1024
MAX_PAGES = 60
MAX_CHARS = 300_000
MAX_ITEMS = 2500
MAX_SECONDS = 30


def sentences(text: str) -> list[str]:
    # Preserve decimals and abbreviations reasonably; extraction remains heuristic.
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\[])|\n\s*\n", text) if s.strip()]


def explicit_context(text: str) -> str | None:
    contexts = {re.sub(r"\s+", " ", x).strip().casefold() for x in re.findall(r"\[context:\s*([^\]]+)\]", text, re.I)}
    contexts.update(f"dataset={name.lower()}; {details.lower()}" for name, details in
                    re.findall(r"\b(?:on|for)\s+(?:the\s+)?dataset\s+([\w-]+)\s*\(([^)]+)\)", text, re.I))
    return next(iter(contexts)) if len(contexts) == 1 else None


def extract_pdf_text(data: bytes, name: str = "uploaded.pdf") -> Document:
    if len(data) > MAX_BYTES:
        raise ValueError("PDF exceeds the 15 MB limit")
    if not data or b"%PDF-" not in data[:1024]:
        raise ValueError("Upload a valid PDF file")
    digest = hashlib.sha256(data).hexdigest()
    name = Path(name.replace("\\", "/")).name[:160]
    try:
        pdf = pymupdf.open(stream=data, filetype="pdf")
    except Exception:
        raise ValueError("The PDF is damaged or cannot be opened") from None
    with pdf:
        if pdf.needs_pass:
            raise ValueError("Password-protected PDFs are not supported. Upload an unlocked copy.")
        if pdf.page_count > MAX_PAGES:
            raise ValueError(f"PDF has {pdf.page_count} pages; the MVP limit is {MAX_PAGES}")
        doc = Document(name=name, sha256=digest, page_count=pdf.page_count, evidence=[])
        section = "Unrecognized section"
        started, total_chars = time.monotonic(), 0
        for page_index, page in enumerate(pdf):
            if time.monotonic() - started > MAX_SECONDS:
                doc.warnings.append(f"Extraction stopped before page {page_index+1} at the time limit; results are partial.")
                break
            blocks = page.get_text("blocks", sort=True)
            if not any(len(b[4].strip()) > 20 for b in blocks if b[6] == 0):
                doc.warnings.append(f"Page {page_index+1}: little or no usable text; scanned content/figures are not analyzed.")
            for block_no, block in enumerate(blocks):
                if block[6] != 0:
                    continue
                raw = block[4].strip()
                text = re.sub(r"\s+", " ", raw)
                if re.fullmatch(r"(?:\d+[. ]+)?(?:abstract|introduction|methods?|methodology|results?|discussion|conclusions?|limitations|references)(?:\s+and\s+\w+)?", text, re.I):
                    section = text
                    continue
                context = explicit_context(text)
                for sentence_no, sentence in enumerate(sentences(text)):
                    if len(sentence) < 5:
                        continue
                    total_chars += len(sentence)
                    if total_chars > MAX_CHARS or len(doc.evidence) >= MAX_ITEMS:
                        doc.warnings.append("Text/item limit reached; extraction is partial.")
                        return doc
                    doc.evidence.append(Evidence(id=f"{digest[:10]}-p{page_index+1}-b{block_no}-s{sentence_no}",
                        document=name, page=page_index+1, text=sentence, section=section,
                        context=explicit_context(sentence) or context, bbox=tuple(block[:4])))
            # Bordered table detection only: avoids inventing alignment in running prose.
            if time.monotonic() - started < MAX_SECONDS:
                try:
                    tables = page.find_tables(strategy="lines_strict").tables
                    for table_no, table in enumerate(tables[:10]):
                        cells = [[str(cell or "").strip() for cell in row] for row in table.extract()]
                        if len(cells) < 2 or not cells[0] or any(len(row) != len(cells[0]) for row in cells):
                            doc.warnings.append(f"Page {page_index+1}: ambiguous table omitted.")
                            continue
                        text = "\n".join(" | ".join(row) for row in cells)
                        if len(doc.evidence) >= MAX_ITEMS or total_chars + len(text) > MAX_CHARS:
                            doc.warnings.append("Table extraction truncated at document limits.")
                            break
                        total_chars += len(text)
                        doc.evidence.append(Evidence(id=f"{digest[:10]}-p{page_index+1}-t{table_no}",
                            document=name, page=page_index+1, text=text, kind="table", section=section,
                            context=explicit_context(text), cells=cells, bbox=tuple(table.bbox)))
                except Exception:
                    doc.warnings.append(f"Page {page_index+1}: table extraction failed; text remains available.")
        if sum(len(e.text) for e in doc.evidence) < 40:
            doc.warnings.append("No substantial machine-readable text. OCR is outside this MVP; use a text-based PDF.")
        return doc
