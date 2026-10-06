from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Verdict(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class Evidence(StrictModel):
    id: str
    document: str
    page: int = Field(ge=1)
    text: str
    kind: Literal["text", "table"] = "text"
    section: str = "Unrecognized section"
    context: str | None = None
    cells: list[list[str]] | None = None
    bbox: tuple[float, float, float, float] | None = None


class Document(StrictModel):
    name: str
    sha256: str
    page_count: int
    evidence: list[Evidence]
    warnings: list[str] = Field(default_factory=list)


class Observation(StrictModel):
    model: str
    metric: str
    value: float
    unit: str
    decimals: int
    context: str
    evidence_id: str


class Claim(StrictModel):
    id: str
    text: str
    source_id: str
    kind: Literal["comparison", "value", "change", "interpretive"] = "interpretive"
    context: str | None = None


class VerificationResult(StrictModel):
    claim: Claim
    verdict: Verdict
    explanation: str
    evidence: list[Evidence] = Field(default_factory=list)
    method: str = "Deterministic verification"
    calculation: str | None = None
    limitations: list[str] = Field(default_factory=list)
    review_required: bool = False


class Paper(StrictModel):
    id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    doi: str | None = None
    venue: str | None = None
    abstract: str | None = None
    url: str
    provider: str
    citations: int = 0
    score: float = 0
    metadata_notes: list[str] = Field(default_factory=list)
    retracted: bool = False


class ToolEvent(StrictModel):
    tool: str
    arguments: dict
    status: str
    summary: str
    elapsed_ms: int = 0


class LiteratureInvestigation(StrictModel):
    topic: str
    queries: list[str]
    papers: list[Paper]
    warnings: list[str] = Field(default_factory=list)
    trace: list[ToolEvent] = Field(default_factory=list)
