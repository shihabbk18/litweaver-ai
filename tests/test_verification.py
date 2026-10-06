import json
from pathlib import Path

import pytest

from evaluation.run import make_document
from litweaver.models import Claim, Document, Evidence, Verdict
from litweaver.verification import extract_scientific_claims, observations_from_evidence, verify_numerical_claim

ROOT = Path(__file__).parents[1] / "evaluation"
CASES = json.loads((ROOT / "cases.json").read_text())
EXPECTED = json.loads((ROOT / "expected.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_synthetic_case(case):
    document, claim = make_document(case)
    result = verify_numerical_claim(claim, document)
    expected = EXPECTED[case["id"]]
    assert result.verdict.value == expected["verdict"]
    assert set(expected["required_evidence"]) <= {e.id for e in result.evidence}
    if "calculation_contains" in expected:
        assert expected["calculation_contains"] in result.calculation
    by_id = {e.id: e for e in document.evidence}
    assert all(e == by_id[e.id] and e.page <= document.page_count for e in result.evidence)


def test_fabricated_claim_rejected():
    doc, claim = make_document(CASES[0])
    claim.text = "Accuracy improved by 15% from 80% to 92%."
    result = verify_numerical_claim(claim, doc)
    assert result.verdict == Verdict.INSUFFICIENT_EVIDENCE
    assert "rejected" in result.explanation.lower()


def test_self_citation_does_not_support_a_value():
    doc, claim = make_document({"id":"self", "claim":"Model A achieved 92.0% accuracy.", "context":"same", "evidence":[]})
    assert verify_numerical_claim(claim, doc).verdict == Verdict.INSUFFICIENT_EVIDENCE


def test_table_values_support_claim():
    doc, claim = make_document(CASES[0])
    doc.evidence = [doc.evidence[0], Evidence(id="T1", document=doc.name, page=1, text="Model | Accuracy (%) | Context\nModel A | 87.4 | dataset=demo; split=test; run=1\nModel B | 84.2 | dataset=demo; split=test; run=1", kind="table",
        cells=[["Model", "Accuracy (%)", "Context"],["Model A","87.4","dataset=demo; split=test; run=1"],["Model B","84.2","dataset=demo; split=test; run=1"]])]
    result = verify_numerical_claim(claim, doc)
    assert result.verdict == Verdict.SUPPORTED
    assert "T1" in {e.id for e in result.evidence}


def test_no_context_table_is_not_silently_assigned():
    evidence = Evidence(id="T1", document="x.pdf", page=1, text="Model | Accuracy (%)\nModel A | 90", kind="table", cells=[["Model","Accuracy (%)"],["Model A","90"]])
    assert observations_from_evidence(evidence) == []


def test_claim_limit_and_references_ignored():
    doc = Document(name="x", sha256="x", page_count=1, evidence=[Evidence(id=f"E{i}", document="x", page=1, text="Model A accuracy = 92.0%.") for i in range(100)])
    assert len(extract_scientific_claims(doc)) == 80
    doc.evidence[0].section = "References"
    assert extract_scientific_claims(doc)[0].source_id == "E1"


def test_context_cannot_be_fabricated_on_claim():
    doc, claim = make_document(CASES[0])
    claim.context = "invented experiment"
    assert verify_numerical_claim(claim, doc).verdict == Verdict.INSUFFICIENT_EVIDENCE


def test_percentage_difference_is_labelled_percentage_points():
    doc, claim = make_document(CASES[0])
    assert "3.2 percentage points" in verify_numerical_claim(claim, doc).calculation


def test_mixed_units_are_never_subtracted():
    doc, claim = make_document(next(c for c in CASES if c["id"] == "different_units"))
    result = verify_numerical_claim(claim, doc)
    assert result.verdict == Verdict.INSUFFICIENT_EVIDENCE
    assert "difference" not in result.calculation


def test_multiple_assertions_abstain():
    doc, claim = make_document(CASES[0])
    claim.text += " Model B achieved higher accuracy than Model A."
    doc.evidence[0].text = claim.text
    assert verify_numerical_claim(claim, doc).verdict == Verdict.INSUFFICIENT_EVIDENCE


def test_user_confirmed_table_context_is_supported_and_disclosed():
    doc, claim = make_document(CASES[0])
    claim.context = doc.evidence[0].context = "user-confirmed: demo test"
    doc.evidence = [doc.evidence[0], Evidence(id="T", document=doc.name, page=1, text="Model | Accuracy (%)\nModel A | 87.4\nModel B | 84.2", kind="table", context=claim.context,
        cells=[["Model","Accuracy (%)"],["Model A","87.4"],["Model B","84.2"]])]
    result = verify_numerical_claim(claim, doc)
    assert result.verdict == Verdict.SUPPORTED
    assert any("analyst assumption" in x for x in result.limitations)
