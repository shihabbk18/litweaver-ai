"""Reproducible MVP evaluation. Expected verdicts are never passed to the verifier."""
import json
from datetime import datetime, timezone
from pathlib import Path

from litweaver.models import Claim, Document, Evidence
from litweaver.verification import verify_numerical_claim

ROOT = Path(__file__).parent


def make_document(case):
    evidence = [Evidence(id="E0", document="synthetic.pdf", page=2, text=case["claim"], context=case.get("context"))]
    for i, item in enumerate(case["evidence"], 1):
        text = item if isinstance(item, str) else item["text"]
        context = case.get("context") if isinstance(item, str) else item.get("context")
        evidence.append(Evidence(id=f"E{i}", document="synthetic.pdf", page=1, text=text, context=context))
    doc = Document(name="synthetic.pdf", sha256="synthetic-fixture", page_count=2, evidence=evidence)
    return doc, Claim(id=case["id"], text=case["claim"], source_id="E0", context=case.get("context"))


def evaluate():
    cases = json.loads((ROOT / "cases.json").read_text())
    outputs = []
    for case in cases:
        doc, claim = make_document(case)
        result = verify_numerical_claim(claim, doc)
        by_id = {e.id: e for e in doc.evidence}
        outputs.append({"id": case["id"], "category": case["category"], "result": result.model_dump(mode="json"),
                        "references_valid": bool(result.evidence) and all(e.id in by_id and e == by_id[e.id] and 1 <= e.page <= doc.page_count for e in result.evidence)})
    # Compare only after predictions are complete.
    expected = json.loads((ROOT / "expected.json").read_text())
    correct = numerical_correct = numerical_count = abstention_correct = abstention_count = refs = 0
    for item in outputs:
        target, result = expected[item["id"]], item["result"]
        item["verdict_correct"] = result["verdict"] == target["verdict"]
        correct += item["verdict_correct"]
        ref_ids = {e["id"] for e in result["evidence"]}
        item["required_evidence_present"] = set(target["required_evidence"]).issubset(ref_ids)
        refs += item["references_valid"] and item["required_evidence_present"]
        if "calculation_contains" in target:
            numerical_count += 1
            item["numerical_correct"] = item["verdict_correct"] and target["calculation_contains"] in (result["calculation"] or "")
            numerical_correct += item["numerical_correct"]
        if target["verdict"] == "INSUFFICIENT_EVIDENCE":
            abstention_count += 1
            abstention_correct += item["verdict_correct"]
    return {"run_at_utc": datetime.now(timezone.utc).isoformat(), "disclaimer": "Small synthetic MVP evaluation, not a validated scientific peer-review benchmark. Cases exercise supported grammar, not general-paper recall.",
            "cases": len(cases), "verdict_accuracy": correct/len(cases), "correct_verdicts": correct,
            "numerical_correctness": numerical_correct/numerical_count, "numerical_cases": numerical_count,
            "evidence_reference_validity": refs/len(cases), "abstention_accuracy": abstention_correct/abstention_count,
            "abstention_cases": abstention_count, "outputs": outputs}


if __name__ == "__main__":
    result = evaluate()
    (ROOT / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "outputs"}, indent=2))
