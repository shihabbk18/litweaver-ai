import httpx
import pytest

from litweaver.models import Paper
from litweaver.scholarly import ScholarlyClient, ScholarlyError, deduplicate, invert_abstract, normalize_doi, rank_papers, verify_publication_metadata


def paper(**kwargs):
    return Paper(**({"id":"p", "title":"Neural Networks for Traffic", "year":2024, "doi":"10.1234/test", "url":"https://doi.org/10.1234/test", "provider":"test"} | kwargs))


def test_doi_and_title_deduplication():
    assert normalize_doi("https://doi.org/10.1234/Test") == "10.1234/test"
    assert normalize_doi("javascript:fake") is None
    assert len(deduplicate([paper(), paper(title="Alternative indexed title")])) == 1
    assert len(deduplicate([paper(doi=None), paper(title="NEURAL NETWORKS: for Traffic!")])) == 1
    assert len(deduplicate([paper(), paper(doi="10.1234/different")])) == 2


def test_abstract_and_ranking():
    assert invert_abstract({"world": [1], "Hello": [0]}) == "Hello world"
    assert invert_abstract(None) is None
    assert rank_papers("neural traffic", [paper(title="Bananas", id="b"), paper()])[0].id == "p"


def test_openalex_real_schema_and_auth_without_leaking_key():
    def handler(request):
        assert request.headers["Authorization"] == "Bearer test-secret"
        assert "test-secret" not in str(request.url)
        return httpx.Response(200, json={"results":[{"id":"https://openalex.org/W1", "display_name":"Example", "publication_year":2024, "doi":"https://doi.org/10.1234/test", "abstract_inverted_index":{"Hello":[0]}, "primary_location":None}]})
    client = ScholarlyClient(api_key="test-secret", client=httpx.Client(transport=httpx.MockTransport(handler)))
    result = client.search_papers("neural traffic")
    assert result[0].abstract == "Hello"
    assert result[0].doi == "10.1234/test"


def test_rate_limit_retries_and_fails_without_fake_results(monkeypatch):
    calls = []
    monkeypatch.setattr("litweaver.scholarly.time.sleep", lambda _: None)
    def handler(request):
        calls.append(request)
        return httpx.Response(429)
    client = ScholarlyClient(client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ScholarlyError, match="429"):
        client.search_papers("traffic")
    assert len(calls) == 3


def test_metadata_mismatch_is_review_not_scientific_fraud():
    result = verify_publication_metadata(paper(), paper(title="A completely different registered work", year=2023))
    assert result["review_required"]
    assert result["verdict"] == "INSUFFICIENT_EVIDENCE"
    assert "2023" not in result["limitation"]


def test_crossref_record_and_cache():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"message":{"DOI":"10.1234/test", "title":["Test work"], "author":[{"given":"A", "family":"Person"}], "published":{"date-parts":[[2020]]}, "abstract":"<jats:p>Real abstract</jats:p>"}})
    client = ScholarlyClient(client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert client.retrieve_publication_metadata("10.1234/test").year == 2020
    assert client.retrieve_publication_metadata("10.1234/test").authors == ["A Person"]
    assert len(calls) == 1
