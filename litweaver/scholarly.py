"""Bounded real metadata retrieval. No generated records or fake fallbacks."""
import html
import re
import time
from difflib import SequenceMatcher
from urllib.parse import quote

import httpx
import numpy as np

from .models import LiteratureInvestigation, Paper, ToolEvent


class ScholarlyError(RuntimeError):
    pass


def normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", doi.strip(), flags=re.I)
    return value.lower().rstrip(".,; ") if re.fullmatch(r"10\.\d{4,9}/\S+", value, re.I) else None


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", text.lower())) - {"the", "and", "for", "with", "from", "this", "that"}


def normalize_title(title: str) -> str:
    return " ".join(re.findall(r"\w+", title.casefold()))


def clean_abstract(value: str | None) -> str | None:
    return html.unescape(re.sub(r"<[^>]+>", " ", value)).strip() if value else None


def invert_abstract(index: dict | None) -> str | None:
    if not index:
        return None
    positions = [(p, word) for word, ps in index.items() for p in ps if isinstance(p, int) and 0 <= p < 20000]
    return " ".join(word for _, word in sorted(positions)) or None


class ScholarlyClient:
    def __init__(self, api_key: str = "", mailto: str = "", client: httpx.Client | None = None):
        self.api_key = api_key
        self.mailto = mailto
        self.client = client or httpx.Client(timeout=httpx.Timeout(20, connect=8), follow_redirects=False)
        self._cache: dict = {}

    def close(self):
        self.client.close()

    def _get(self, provider: str, path: str, params: dict | None = None) -> dict:
        bases = {"OpenAlex": "https://api.openalex.org", "Crossref": "https://api.crossref.org"}
        params = dict(params or {})
        headers = {"User-Agent": "LitWeaverAI/0.1 (academic metadata MVP)"}
        if provider == "OpenAlex" and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.mailto:
            params["mailto"] = self.mailto
        key = (provider, path, str(sorted(params.items())))
        if key in self._cache:
            return self._cache[key]
        for attempt in range(3):
            try:
                response = self.client.get(bases[provider] + path, params=params, headers=headers)
                if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                    delay = response.headers.get("Retry-After", "")
                    time.sleep(min(float(delay), 3) if delay.isdigit() else 0.5 * (2 ** attempt))
                    continue
                if response.status_code >= 400:
                    hint = " Configure a free OpenAlex key or retry later." if provider == "OpenAlex" and response.status_code in (401, 403, 429) else ""
                    raise ScholarlyError(f"{provider} returned HTTP {response.status_code}.{hint}")
                result = response.json()
                self._cache[key] = result
                return result
            except (httpx.RequestError, ValueError) as exc:
                if attempt == 2:
                    raise ScholarlyError(f"{provider} request failed ({type(exc).__name__}); no records were invented.") from None
                time.sleep(0.5)
        raise ScholarlyError(f"{provider} unavailable")

    def search_papers(self, query: str, limit: int = 10, provider: str = "OpenAlex") -> list[Paper]:
        query = query.strip()[:300]
        if not query:
            raise ValueError("A search query is required")
        limit = max(1, min(int(limit), 25))
        if provider == "OpenAlex":
            data = self._get(provider, "/works", {"search": query, "per-page": limit})
            result = []
            for w in data.get("results", []):
                loc = w.get("primary_location") or {}
                result.append(Paper(
                    id=w["id"], title=w.get("display_name") or "Untitled", doi=normalize_doi(w.get("doi")),
                    authors=[a.get("author", {}).get("display_name", "Unknown") for a in w.get("authorships", [])],
                    year=w.get("publication_year"), venue=(loc.get("source") or {}).get("display_name"),
                    abstract=invert_abstract(w.get("abstract_inverted_index")),
                    url=loc.get("landing_page_url") or w["id"], provider=provider,
                    citations=w.get("cited_by_count", 0), retracted=w.get("is_retracted", False)))
            return result
        if provider == "Crossref":
            data = self._get(provider, "/works", {"query.bibliographic": query, "rows": limit})
            return [self._crossref_paper(w) for w in data.get("message", {}).get("items", [])]
        raise ValueError("Unknown scholarly provider")

    @staticmethod
    def _crossref_paper(w: dict) -> Paper:
        doi = normalize_doi(w.get("DOI"))
        dates = (w.get("published") or w.get("issued") or {}).get("date-parts", [[]])
        return Paper(id=f"https://doi.org/{doi}" if doi else w.get("URL", "Crossref-record"),
                     title=(w.get("title") or ["Untitled"])[0], doi=doi,
                     authors=[" ".join(filter(None, [a.get("given"), a.get("family")])) or a.get("name", "Unknown") for a in w.get("author", [])],
                     year=dates[0][0] if dates and dates[0] else None,
                     venue=(w.get("container-title") or [None])[0], abstract=clean_abstract(w.get("abstract")),
                     url=f"https://doi.org/{doi}" if doi else w.get("URL", "https://search.crossref.org"), provider="Crossref")

    def retrieve_publication_metadata(self, doi: str) -> Paper:
        normalized = normalize_doi(doi)
        if not normalized:
            raise ValueError("Invalid DOI")
        return self._crossref_paper(self._get("Crossref", "/works/" + quote(normalized, safe=""))["message"])


def deduplicate(papers: list[Paper]) -> list[Paper]:
    unique: list[Paper] = []
    for paper in papers:
        duplicate = next((p for p in unique if
            (p.doi and paper.doi and p.doi == paper.doi) or
            (not (p.doi and paper.doi and p.doi != paper.doi) and p.year == paper.year and
             normalize_title(p.title) == normalize_title(paper.title))), None)
        if duplicate:
            if not duplicate.abstract and paper.abstract:
                duplicate.abstract = paper.abstract
            continue
        unique.append(paper)
    return unique


def rank_papers(topic: str, papers: list[Paper]) -> list[Paper]:
    query = tokens(topic)
    for p in papers:
        title_overlap = len(query & tokens(p.title)) / max(len(query), 1)
        abstract_overlap = len(query & tokens(p.abstract or "")) / max(len(query), 1)
        p.score = float(np.round(0.75 * title_overlap + 0.25 * abstract_overlap, 4))
    return sorted(papers, key=lambda p: (-p.score, -(p.year or 0), p.title))


def generate_queries(topic: str) -> list[str]:
    topic = topic.strip()[:250]
    if not topic:
        raise ValueError("Please enter a research topic")
    return [topic, f"{topic} methods evaluation", f"{topic} limitations survey"]


def verify_publication_metadata(paper: Paper, registered: Paper) -> dict:
    similarity = SequenceMatcher(None, normalize_title(paper.title), normalize_title(registered.title)).ratio()
    mismatches = []
    if paper.doi != registered.doi:
        mismatches.append("DOI does not match the retrieved record")
    if similarity < 0.75:
        mismatches.append("Title differs substantially from the registered title")
    if paper.year and registered.year and paper.year != registered.year:
        mismatches.append("Year differs (online and print dates may differ; human review required)")
    return {"verdict": "INSUFFICIENT_EVIDENCE" if mismatches else "SUPPORTED",
            "review_required": bool(mismatches), "notes": mismatches or ["DOI/title and available year agree with Crossref"],
            "source_url": registered.url, "registered_title": registered.title, "registered_year": registered.year,
            "limitation": "Metadata agreement is not validation of scientific findings or reference-to-claim relevance."}


def investigate(topic: str, client: ScholarlyClient, limit: int = 15, progress=None) -> LiteratureInvestigation:
    queries = generate_queries(topic)
    run = LiteratureInvestigation(topic=topic, queries=queries, papers=[])
    for i, query in enumerate(queries):
        if progress:
            progress((i + 1) / 5, f"Searching OpenAlex: {query}")
        start = time.monotonic()
        try:
            papers = client.search_papers(query, min(limit, 20))
            run.papers.extend(papers)
            run.trace.append(ToolEvent(tool="search_papers", arguments={"query": query, "provider": "OpenAlex"}, status="ok", summary=f"{len(papers)} genuine records", elapsed_ms=int((time.monotonic()-start)*1000)))
        except ScholarlyError as exc:
            run.warnings.append(str(exc))
            run.trace.append(ToolEvent(tool="search_papers", arguments={"query": query}, status="error", summary=str(exc)))
            break
    if not run.papers:
        run.warnings.append("OpenAlex returned no usable records. Trying explicitly labelled Crossref results.")
        try:
            run.papers = client.search_papers(topic, min(limit, 25), "Crossref")
            run.trace.append(ToolEvent(tool="search_papers", arguments={"query": topic, "provider": "Crossref"}, status="ok", summary=f"{len(run.papers)} records"))
        except ScholarlyError as exc:
            run.warnings.append(str(exc))
    run.papers = rank_papers(topic, deduplicate(run.papers))[:limit]
    for paper in [p for p in run.papers if p.doi][:5]:
        if progress:
            progress(0.8, "Checking DOI metadata with Crossref")
        try:
            registered = client.retrieve_publication_metadata(paper.doi)
            check = verify_publication_metadata(paper, registered)
            paper.metadata_notes.extend(check["notes"])
            if not paper.abstract and registered.abstract:
                paper.abstract = registered.abstract
                paper.metadata_notes.append("Abstract supplied by Crossref")
            run.trace.append(ToolEvent(tool="retrieve_publication_metadata", arguments={"doi": paper.doi}, status="ok", summary="; ".join(check["notes"])))
        except (ScholarlyError, ValueError) as exc:
            paper.metadata_notes.append(str(exc))
            run.trace.append(ToolEvent(tool="retrieve_publication_metadata", arguments={"doi": paper.doi}, status="error", summary=str(exc)))
    if progress:
        progress(1.0, "Source-grounded matrix ready")
    return run
