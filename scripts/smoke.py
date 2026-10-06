"""Run a genuine literature lookup and synthetic PDF investigation; save actual outputs."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from litweaver.pdf import extract_pdf_text
from litweaver.reports import bibtex_export, critic_report, csv_export, generate_comparison_matrix, generate_investigation_report
from litweaver.scholarly import ScholarlyClient, investigate
from litweaver.verification import analyze_document


def main():
    out = ROOT / "examples" / "output"
    out.mkdir(exist_ok=True)
    client = ScholarlyClient()
    try:
        run = investigate("Machine Learning for Network Traffic Optimization", client, 10)
    finally:
        client.close()
    (out/"literature.json").write_text(run.model_dump_json(indent=2), encoding="utf-8")
    (out/"literature.md").write_text(generate_investigation_report(run), encoding="utf-8")
    (out/"literature.csv").write_bytes(csv_export(generate_comparison_matrix(run.papers)))
    (out/"references.bib").write_text(bibtex_export(run.papers), encoding="utf-8")
    doc = extract_pdf_text((ROOT/"examples"/"numerical-audit.pdf").read_bytes(), "numerical-audit.pdf")
    results = analyze_document(doc)
    (out/"critique.md").write_text(critic_report(doc, results), encoding="utf-8")
    (out/"critique.json").write_text(json.dumps({"document":doc.model_dump(), "results":[r.model_dump(mode="json") for r in results]}, indent=2), encoding="utf-8")
    summary = {"run_at_utc":datetime.now(timezone.utc).isoformat(), "real_papers":len(run.papers), "with_abstract":sum(bool(p.abstract) for p in run.papers), "providers":list({p.provider for p in run.papers}), "api_warnings":run.warnings, "sample_pdf_pages":doc.page_count, "sample_pdf_claims":len(results), "sample_verdicts":{v:sum(r.verdict.value==v for r in results) for v in ("SUPPORTED","CONTRADICTED","INSUFFICIENT_EVIDENCE")}, "pdf_warnings":doc.warnings}
    (out/"smoke-results.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if not run.papers:
        raise SystemExit("Real publication lookup failed; see recorded provider errors")
    if not any(r.verdict.value=="CONTRADICTED" for r in results):
        raise SystemExit("Sample PDF investigation did not detect the planted numerical errors")


if __name__ == "__main__":
    main()
