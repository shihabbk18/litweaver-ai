import csv
import io
import re
from collections import Counter
from urllib.parse import urlparse

import pandas as pd

from .models import Document, LiteratureInvestigation, Paper, VerificationResult
from .pdf import sentences

MISSING = "Not available in retrieved text"
FIELDS = {
    "Research objective": r"\b(?:aim|objective|investigat|study|propos|address|explor)\w*\b",
    "Methodology": r"\b(?:method|algorithm|framework|experiment|regression|neural|learning|simulation|randomiz)\w*\b",
    "Reported contribution": r"\b(?:result|achiev|demonstrat|improv|outperform|contribut|show)\w*\b",
    "Explicit limitations": r"\b(?:limitation|limited|future work|constraint|drawback)\w*\b",
}
THEMES = ["deep learning", "reinforcement learning", "machine learning", "neural network", "optimization", "simulation", "regression", "classification", "randomized", "systematic review"]


def safe_url(value: str) -> str:
    return value if urlparse(value).scheme in ("https", "http") else ""


def md(value: str) -> str:
    # Avoid rendering source-provided Markdown links/HTML as active content.
    return re.sub(r"([\\`*_{}\[\]()<>|#!])", r"\\\1", str(value)).replace("\n", " ")


def excerpt(abstract: str | None, pattern: str) -> str:
    if not abstract:
        return MISSING
    candidates = [s for s in sentences(abstract) if re.search(pattern, s, re.I)]
    if not candidates:
        return MISSING
    value = candidates[0]
    return value[:650] + ("… [truncated excerpt]" if len(value) > 650 else "")


def generate_comparison_matrix(papers: list[Paper], annotations: dict | None = None) -> pd.DataFrame:
    rows = []
    for p in papers:
        row = {"Paper title": p.title, "Authors": "; ".join(p.authors) or "Not available", "Publication year": p.year,
               "DOI": p.doi or "", "Publication venue": p.venue or "Not available", "Source URL": safe_url(p.url),
               "Analysis scope": "Abstract only" if p.abstract else "Metadata only", "Metadata source": p.provider,
               "Relevance score": p.score, "Retracted flag": p.retracted}
        row.update({key: excerpt(p.abstract, pattern) for key, pattern in FIELDS.items()})
        for field, quote in (annotations or {}).get(p.id, {}).items():
            if field in FIELDS and p.abstract and quote in p.abstract:
                row[field] = quote
        rows.append(row)
    return pd.DataFrame(rows)


def observed_themes(papers: list[Paper]) -> dict[str, list[str]]:
    return {theme: [p.id for p in papers if theme in (p.abstract or "").lower()]
            for theme in THEMES if sum(theme in (p.abstract or "").lower() for p in papers) >= 2}


def csv_export(frame: pd.DataFrame) -> bytes:
    def safe_cell(value):
        if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
            return "'" + value
        return value
    return frame.map(safe_cell).to_csv(index=False, quoting=csv.QUOTE_ALL).encode("utf-8-sig")


def tex_escape(text: str) -> str:
    replacements = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "%": r"\%", "&": r"\&", "_": r"\_", "#": r"\#", "$": r"\$", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(replacements.get(char, char) for char in text.replace("\n", " "))


def bibtex_export(papers: list[Paper]) -> str:
    entries = []
    for i, p in enumerate(papers, 1):
        fields = {"title": p.title, "author": " and ".join(p.authors), "year": str(p.year) if p.year else "", "doi": p.doi or "", "journal": p.venue or "", "url": safe_url(p.url)}
        entries.append("@misc{litweaver" + str(i) + ",\n" + ",\n".join(f"  {key} = {{{tex_escape(value)}}}" for key, value in fields.items() if value) + "\n}")
    return "\n\n".join(entries)


def generate_investigation_report(run: LiteratureInvestigation, annotations: dict | None = None, opportunities: list[dict] | None = None) -> str:
    lines = ["# LitWeaver AI — Literature investigation", "", f"Topic: {md(run.topic)}", "",
             "Scope: retrieved metadata and available abstracts only. No full-paper review was performed.",
             "The matrix contains extractive source passages selected by keyword rules (or quote-validated LLM selections). Passage selection does not establish methodological quality or scientific truth.", "",
             "## Search method", "Queries: " + "; ".join(md(q) for q in run.queries),
             "Deduplication: normalized DOI, then exact normalized title plus year when DOIs do not conflict. Ranking: 75% topic-token overlap in title, 25% in abstract; not a systematic review."]
    for warning in run.warnings:
        lines.append("Warning: " + md(warning))
    lines += ["", "## Recurring terms in retrieved abstracts"]
    themes = observed_themes(run.papers)
    if not themes:
        lines.append("No recurring terms from the small configured vocabulary were found.")
    for theme, ids in themes.items():
        lines.append(f"- {md(theme)}: {len(ids)} abstracts. Source records: " + "; ".join(ids))
    matrix = generate_comparison_matrix(run.papers, annotations)
    for i, (_, row) in enumerate(matrix.iterrows(), 1):
        p = run.papers[i-1]
        lines += ["", f"## {i}. {md(p.title)}", f"Authors: {md('; '.join(p.authors))}", f"Year: {p.year or 'Unknown'} · Venue: {md(p.venue or 'Unknown')}",
                  f"DOI: {md(p.doi or 'Unavailable')}", f"Source: {safe_url(p.url)}", f"Analysis scope: {row['Analysis scope']}"]
        if p.retracted:
            lines.append("RETRACTION FLAG: OpenAlex marks this work as retracted; inspect the publisher record.")
        for field in FIELDS:
            lines.append(f"- {field} (source excerpt): {md(row[field])}")
        lines.extend("- Metadata note: " + md(note) for note in p.metadata_notes)
    lines += ["", "## Possible research questions", "Hypotheses requiring further literature verification; novelty is not established."]
    if opportunities:
        for item in opportunities:
            lines.append(f"- {md(item['question'])} — based on record {md(item['paper_id'])}, excerpt: {md(item['quote'])}")
    else:
        lines.append("Generative opportunity analysis is disabled or no source-grounded suggestions were accepted. Review the explicit limitation excerpts above to formulate follow-up questions.")
    return "\n\n".join(lines)


def critic_report(document: Document, results: list[VerificationResult], concerns: list[dict] | None = None) -> str:
    counts = Counter(r.verdict.value for r in results)
    lines = ["# LitWeaver AI — Research Critic", f"Document: {md(document.name)}", f"SHA-256: `{document.sha256}`", f"Pages: {document.page_count}",
             "Scope: accessible text and reliably detected machine-readable tables. SUPPORTED means agreement with cited reported values or arithmetic, not independent replication. CONTRADICTED describes a documented inconsistency, not misconduct.",
             "Verdicts: " + ", ".join(f"{k}: {v}" for k, v in counts.items())]
    lines.extend("Extraction warning: " + md(w) for w in document.warnings)
    for r in results:
        lines += [f"## {r.claim.id} — {r.verdict.value}", f"Claim: {md(r.claim.text)}", f"Explanation: {md(r.explanation)}", f"Method: {md(r.method)}", f"Human review flag: {r.review_required}"]
        if r.calculation:
            lines.append("Calculation: " + md(r.calculation))
        lines.extend(f"- [{md(e.id)}] {md(e.document)}, page {e.page}, {md(e.section)}: {md(e.text)}" for e in r.evidence)
        lines.extend("Limitation: " + md(x) for x in r.limitations)
    lines += ["## Model-suggested concerns", "Potential concerns requiring human review; these do not change the evidence verdicts."]
    for concern in concerns or []:
        lines.append(f"- {md(concern['concern'])} — {md(concern['evidence_id'])}, page {concern['page']}; excerpt: {md(concern['quote'])}")
    if not concerns:
        lines.append("No model-suggested concerns were generated or accepted.")
    return "\n\n".join(lines)
