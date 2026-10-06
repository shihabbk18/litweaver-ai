import json
import pytest

from litweaver.agent import AgentSession, LLMConfig
from litweaver.models import Document, Evidence, LiteratureInvestigation, Paper
from litweaver.scholarly import ScholarlyClient


class FakeProvider:
    """Protocol double; not evidence of a successful live LLM invocation."""
    config = LLMConfig(provider="openai_compatible", model="test")

    def __init__(self, responses):
        self.responses = iter(responses)
        self.messages = []

    def chat(self, messages, tools):
        self.messages.append(list(messages))
        return next(self.responses)


def call(name, args, id="x"):
    return {"role":"assistant", "tool_calls":[{"id":id, "type":"function", "function":{"name":name, "arguments":json.dumps(args)}}]}


def session():
    doc = Document(name="x.pdf", sha256="abc", page_count=1, evidence=[Evidence(id="E1", document="x.pdf", page=1, text="Model A accuracy = 92.0%. Only one trial was performed.")])
    return AgentSession(ScholarlyClient(), document=doc)


def test_actual_tool_call_protocol_dispatches_and_returns_result():
    s = session()
    provider = FakeProvider([call("extract_scientific_claims", {}), {"role":"assistant", "content":"Done"}])
    s.run(provider, "Inspect paper")
    assert s.trace[0].tool == "extract_scientific_claims"
    assert s.trace[0].status == "ok"
    tool_message = provider.messages[1][-1]
    assert tool_message["role"] == "tool" and tool_message["tool_call_id"] == "x"
    assert "E1" in tool_message["content"]


def test_injection_and_fabricated_evidence_rejected():
    s = session()
    assert "error" in s.execute("exec", {"code":"delete everything"})
    assert "error" in s.execute("flag_review_concern", {"evidence_id":"E1", "quote":"An invented and absent evidence passage", "concern":"Possible missing experimental controls"})
    assert not s.concerns
    output = s.execute("flag_review_concern", {"evidence_id":"E1", "quote":"Only one trial was performed.", "concern":"Potential concern: run-to-run variability is not described in this excerpt."})
    assert output["review_required"]
    assert s.concerns[0]["verdict"] == "INSUFFICIENT_EVIDENCE"


def test_bounded_loop_and_repeated_calls():
    s = session()
    provider = FakeProvider([call("extract_scientific_claims", {})] * 10)
    s.run(provider, "Never stop", max_calls=3)
    assert len([e for e in s.trace if e.tool == "extract_scientific_claims" and e.status == "ok"]) == 1
    assert s.trace[-1].tool == "agent_limit"


def test_exact_quote_annotation_only():
    p = Paper(id="p", title="Test", abstract="We evaluate a method. The sample is limited to one city.", url="https://example.org", provider="test")
    s = AgentSession(ScholarlyClient(), literature=LiteratureInvestigation(topic="test", queries=[], papers=[p]))
    assert "error" in s.execute("annotate_paper", {"paper_id":"p", "field":"Methodology", "quote":"We used a randomized controlled clinical trial."})
    assert not s.annotations
    assert s.execute("annotate_paper", {"paper_id":"p", "field":"Explicit limitations", "quote":"The sample is limited to one city."})["accepted"]


def test_provider_failure_retains_deterministic_work():
    s = session()
    class Failed:
        def chat(self, *args):
            raise RuntimeError("Provider unavailable")
    s.run(Failed(), "Inspect paper")
    assert s.trace[-1].status == "error"
    assert s.claims


def test_model_cannot_strip_negation_from_a_proposed_claim():
    s = session()
    source = s.document.evidence[0]
    source.text = "There is no evidence that the method generalizes to unseen patients."
    assert "error" in s.execute("propose_scientific_claim", {"evidence_id":"E1", "quote":"the method generalizes to unseen patients."})


def test_model_can_add_a_complete_previously_missed_sentence():
    s = session()
    s.document.evidence.append(Evidence(id="E2", document="x.pdf", page=1, text="The test cohort contained exclusively adult subjects."))
    result = s.execute("propose_scientific_claim", {"evidence_id":"E2", "quote":"The test cohort contained exclusively adult subjects."})
    assert result["source_id"] == "E2"
    assert len(s.claims) == 2


@pytest.mark.parametrize("response", [None, {"tool_calls":"invalid"}, {"tool_calls":[{"function":None}]}])
def test_malformed_provider_responses_retain_results(response):
    s = session()
    s.run(FakeProvider([response]), "Inspect paper")
    assert s.trace[-1].status == "error"
    assert s.claims
