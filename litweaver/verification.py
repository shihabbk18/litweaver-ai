"""Conservative numerical checks, with evidence identities enforced at the boundary.

Supported grammar is deliberately narrow. Unparsed language is an abstention,
never a reason to trust a model's numerical interpretation.
"""
import re
import time

from .models import Claim, Document, Evidence, Observation, ToolEvent, Verdict, VerificationResult
from .pdf import explicit_context
from .scholarly import tokens

METRIC = r"(?:classification\s+accuracy|accuracy|precision|recall|f1(?:[- ]score)?|error(?:\s+rate)?|latency|runtime|computational\s+cost|cost|throughput|auc)"
MODEL = r"(?:Model\s+[A-Za-z0-9_-]+)"
NUMBER = r"(?:\d+(?:\.\d+)?)"
UNIT = r"(?:%|ms|seconds?|s|milliseconds?|MB|GB)(?![A-Za-z])"
VALUE_PATTERNS = [
    re.compile(rf"(?P<model>{MODEL})\s+(?P<metric>{METRIC})\s*(?:=|:|was|is|of)\s*(?P<value>{NUMBER})\s*(?P<unit>{UNIT})?", re.I),
    re.compile(rf"(?P<model>{MODEL})\s+(?:achieved|reported|obtained|reached)\s+(?P<value>{NUMBER})\s*(?P<unit>{UNIT})?\s+(?P<metric>{METRIC})", re.I),
]
COMPARISON = re.compile(rf"(?P<a>{MODEL})\s+(?:(?:achieved|had|has|showed|reported)\s+)?(?P<relation>higher|lower|better|worse|equal)\s+(?P<metric>{METRIC})\s+(?:than|to|as)\s+(?P<b>{MODEL})", re.I)
CHANGE = re.compile(rf"(?P<metric>{METRIC})\s+(?P<verb>improved|increased|decreased|reduced)\s+by\s+(?P<amount>{NUMBER})\s*(?P<changeunit>%|percent(?:age)?\s+points?|percent)\s+from\s+(?P<old>{NUMBER})\s*(?P<oldunit>{UNIT})?\s+to\s+(?P<new>{NUMBER})\s*(?P<newunit>{UNIT})?", re.I)
LOWER_IS_BETTER = {"error", "latency", "runtime", "cost"}
HIGHER_IS_BETTER = {"accuracy", "precision", "recall", "f1", "throughput", "auc"}


def metric_name(value: str) -> str:
    value = value.lower().replace("classification ", "").replace("computational ", "")
    if value.startswith("f1"):
        return "f1"
    return "error" if value == "error rate" else value


def unit_name(value: str | None) -> str:
    value = (value or "unspecified").lower()
    return {"second": "s", "seconds": "s", "millisecond": "ms", "milliseconds": "ms"}.get(value, value)


def decimals(value: str) -> int:
    return len(value.split(".")[1]) if "." in value else 0


def unsafe_qualifier(text: str) -> bool:
    return bool(re.search(r"\b(?:not|might|may|could|hypothetical|assuming|approximately|about|up to|at least|at most|confidence interval)\b|[<>≤≥±]", text, re.I))


def observations_from_evidence(e: Evidence) -> list[Observation]:
    if unsafe_qualifier(e.text):
        return []
    observations = []
    for pattern in VALUE_PATTERNS:
        for match in pattern.finditer(e.text):
            d = match.groupdict()
            context = e.context or explicit_context(e.text) or ""
            observations.append(Observation(model=d["model"].lower(), metric=metric_name(d["metric"]),
                value=float(d["value"]), unit=unit_name(d["unit"]), decimals=decimals(d["value"]),
                context=context, evidence_id=e.id))
    # Only unambiguous table schema: Model | Accuracy (%) | Context (etc.).
    if e.kind == "table" and e.cells:
        headers = [c.lower().strip() for c in e.cells[0]]
        if len(headers) != len(set(headers)):
            return observations
        if "model" in headers and ("context" in headers or e.context):
            for col, header in enumerate(headers):
                header_match = re.fullmatch(rf"(?P<metric>{METRIC})\s*\((?P<unit>{UNIT})\)", header, re.I)
                if not header_match:
                    continue
                for row in e.cells[1:]:
                    if len(row) != len(headers):
                        continue
                    raw = row[col].strip()
                    if header_match["unit"] == "%":
                        raw = raw.rstrip("%").strip()
                    if re.fullmatch(NUMBER, raw) and re.fullmatch(MODEL, row[headers.index("model")], re.I):
                        observations.append(Observation(model=row[headers.index("model")].lower(),
                            metric=metric_name(header_match["metric"]), value=float(raw), unit=unit_name(header_match["unit"]),
                            decimals=decimals(raw), context=(row[headers.index("context")].lower().strip() if "context" in headers else e.context), evidence_id=e.id))
    return observations


def extract_scientific_claims(document: Document, limit: int = 80) -> list[Claim]:
    claims = []
    for e in document.evidence:
        if e.kind == "table" or "references" in e.section.lower():
            continue
        kind = None
        if CHANGE.search(e.text):
            kind = "change"
        elif COMPARISON.search(e.text):
            kind = "comparison"
        elif any(p.search(e.text) for p in VALUE_PATTERNS):
            kind = "value"
        elif re.search(r"\b(?:outperform\w*|improv\w*|reduc\w*|achiev\w*|support\w*|demonstrates?|demonstrated|prove[sd]?|superior|generaliz\w*|significant\w*|conclud\w*)\b", e.text, re.I):
            kind = "interpretive"
        if kind:
            claims.append(Claim(id=f"C{len(claims)+1:03}", text=e.text, source_id=e.id, kind=kind, context=e.context))
        if len(claims) >= limit:
            break
    return claims


def retrieve_claim_evidence(claim: Claim, evidence: list[Evidence], limit: int = 12) -> list[Evidence]:
    query = tokens(claim.text)
    nums = set(re.findall(NUMBER, claim.text))
    scored = []
    for item in evidence:
        if item.id == claim.source_id or item.text == claim.text:
            continue
        overlap = len(query & tokens(item.text)) / max(len(query | tokens(item.text)), 1)
        number_overlap = len(nums & set(re.findall(NUMBER, item.text))) / max(len(nums), 1)
        score = overlap + 0.15 * number_overlap
        if score > 0:
            scored.append((score, item))
    return [e for _, e in sorted(scored, key=lambda pair: pair[0], reverse=True)[:limit]]


def uncertainty(obs: Observation) -> float:
    return 0.5 * 10 ** (-obs.decimals)


def compare_values(a: Observation, b: Observation, relation: str) -> bool | None:
    if a.unit != b.unit or a.unit == "unspecified" or a.metric != b.metric:
        return None
    diff = a.value - b.value
    radius = uncertainty(a) + uncertainty(b)
    if relation in ("better", "worse"):
        if a.metric not in LOWER_IS_BETTER | HIGHER_IS_BETTER:
            return None
        greater = (relation == "better") == (a.metric in HIGHER_IS_BETTER)
        relation = "higher" if greater else "lower"
    if relation == "equal":
        return True if diff == 0 else (False if abs(diff) > radius + 1e-9 else None)
    if diff == 0:
        return False  # equal reported values cannot substantiate a strict reported comparison
    if abs(diff) <= radius + 1e-9:
        return None
    return diff > 0 if relation == "higher" else diff < 0


def verify_numerical_claim(claim: Claim, document: Document) -> VerificationResult:
    by_id = {e.id: e for e in document.evidence}
    origin = by_id.get(claim.source_id)
    result = VerificationResult(claim=claim, verdict=Verdict.INSUFFICIENT_EVIDENCE,
        explanation="No directly comparable evidence was established.", evidence=[origin] if origin else [],
        limitations=["Checks concern reported text and arithmetic, not experimental truth or scientific validity."])
    if not origin or claim.text not in origin.text:
        result.explanation = "Claim is not an exact excerpt of its cited source. Verification rejected."
        return result
    if claim.context != origin.context:
        result.explanation = "Claim context does not match its source evidence. Verification rejected."
        return result
    if len(CHANGE.findall(claim.text)) + len(COMPARISON.findall(claim.text)) > 1:
        result.explanation = "Multiple assertions occur in this excerpt; split and review them individually."
        result.review_required = True
        return result
    if origin.context and origin.context.startswith("user-confirmed:"):
        result.limitations.append("Experimental context was confirmed by the user; equivalence is an analyst assumption.")
    if unsafe_qualifier(claim.text):
        result.explanation = "Negation, uncertainty, an inequality, or an interval requires human interpretation."
        result.review_required = True
        return result
    change = CHANGE.search(claim.text)
    if change:
        d = change.groupdict()
        old, new, amount = (float(d[k]) for k in ("old", "new", "amount"))
        u1, u2 = unit_name(d["oldunit"]), unit_name(d["newunit"])
        if u1 != u2 or u1 == "unspecified":
            result.explanation = "Change values have missing or different units; no conversion is assumed."
            return result
        points = "point" in d["changeunit"].lower()
        if points and u1 != "%":
            result.explanation = "Percentage-point checks require two percentage values."
            return result
        if not points and old == 0:
            result.explanation = "Relative change from a zero baseline is undefined."
            return result
        direction = -1 if d["verb"].lower() in ("decreased", "reduced") else 1
        if d["verb"].lower() == "improved":
            direction = -1 if metric_name(d["metric"]) in LOWER_IS_BETTER else 1
        expected = direction * (new - old) * (1 if points else 100 / old)
        # Propagate displayed precision through endpoint calculations. A point estimate
        # close to the claim can be supported; boundary-only overlap abstains.
        half_old = 0.5 * 10 ** (-decimals(d["old"]))
        half_new = 0.5 * 10 ** (-decimals(d["new"]))
        amount_half = 0.5 * 10 ** (-decimals(d["amount"]))
        if not points and old - half_old <= 0:
            result.explanation = "Rounded baseline includes zero; relative change is unstable."
            return result
        possibilities = [direction*(n-o)*(1 if points else 100/o)
                         for o in (old-half_old, old+half_old) for n in (new-half_new, new+half_new)]
        result.calculation = (f"{direction} × ({new:g} - {old:g})" + ("" if points else f" / {old:g} × 100") +
                              f" = {expected:.6g} {'percentage points' if points else '%'}; claimed {amount:g}.")
        if abs(expected-amount) <= amount_half + 1e-9:
            result.verdict = Verdict.SUPPORTED
            result.explanation = "The stated arithmetic agrees with the displayed values at the claim's precision."
        elif max(possibilities) < amount-amount_half or min(possibilities) > amount+amount_half:
            result.verdict = Verdict.CONTRADICTED
            result.explanation = "The claimed change conflicts with the stated inputs, even allowing for displayed rounding."
        else:
            result.explanation = "Displayed rounding could change the conclusion; original precision is needed."
        result.method = "Deterministic percentage/percentage-point arithmetic"
        result.limitations.append("Operands come from this statement; agreement does not independently corroborate them.")
        return result
    comparison = COMPARISON.search(claim.text)
    all_obs = [o for e in document.evidence if e.id != origin.id and e.text != origin.text for o in observations_from_evidence(e)]
    if comparison:
        d = comparison.groupdict()
        metric = metric_name(d["metric"])
        relevant = [o for o in all_obs if o.metric == metric and o.model in (d["a"].lower(), d["b"].lower())]
        # No inferred global context. Explicit matching context is required across snippets.
        context = claim.context or explicit_context(claim.text)
        if not context:
            result.explanation = "The claim has no explicit experimental context. Cross-snippet comparisons abstain."
            return result
        relevant = [o for o in relevant if o.context == context]
        a = [o for o in relevant if o.model == d["a"].lower()]
        b = [o for o in relevant if o.model == d["b"].lower()]
        if not a or not b:
            result.explanation = "Both models need values for the same metric, units, and explicit context."
            return result
        result.evidence.extend(by_id[i] for i in dict.fromkeys(o.evidence_id for o in a+b))
        for group in (a, b):
            if len({(o.value, o.unit) for o in group}) > 1:
                result.explanation = "Multiple reported values exist in the selected context; the comparison is ambiguous."
                result.review_required = True
                return result
        answer = compare_values(a[0], b[0], d["relation"].lower())
        result.calculation = f"{a[0].model}: {a[0].value:g} {a[0].unit}; {b[0].model}: {b[0].value:g} {b[0].unit}."
        if a[0].unit == b[0].unit and a[0].unit != "unspecified":
            difference_unit = "percentage points" if a[0].unit == "%" else a[0].unit
            result.calculation += f" Reported difference = {a[0].value-b[0].value:.6g} {difference_unit}."
        result.method = "Deterministic comparison of contextualized reported values"
        result.verdict = Verdict.SUPPORTED if answer is True else Verdict.CONTRADICTED if answer is False else Verdict.INSUFFICIENT_EVIDENCE
        result.explanation = "Comparison agrees with reported values." if answer is True else "Comparison conflicts with reported values." if answer is False else "Units or rounding prevent a reliable comparison."
        return result
    own = observations_from_evidence(origin)
    if len(own) == 1 and (claim.context or explicit_context(claim.text)):
        value = own[0]
        comparable = [o for o in all_obs if o.model == value.model and o.metric == value.metric and
                      o.context == value.context and o.unit == value.unit and o.unit != "unspecified"]
        if comparable:
            result.evidence.extend(by_id[i] for i in dict.fromkeys(o.evidence_id for o in comparable))
            conflicts = [o for o in comparable if abs(o.value-value.value) > uncertainty(o)+uncertainty(value)+1e-9]
            if conflicts:
                result.verdict = Verdict.CONTRADICTED
                result.review_required = True
                result.explanation = "Different values are reported for the same model, metric, unit and explicit context. Neither is established as the true value."
            elif all(o.value == value.value for o in comparable):
                result.verdict = Verdict.SUPPORTED
                result.explanation = "A separate source excerpt reports the same value in the same explicit context."
            else:
                result.explanation = "Values differ within the uncertainty implied by displayed precision."
            result.calculation = f"Claim: {value.value:g} {value.unit}; other reported values: " + ", ".join(f"{o.value:g} {o.unit}" for o in comparable)
            result.method = "Deterministic within-document numerical consistency"
            return result
    result.evidence.extend(retrieve_claim_evidence(claim, document.evidence, 5))
    result.explanation = "Related passages are candidates only. The supported grammar or explicit contextual evidence is insufficient for a verdict."
    result.review_required = claim.kind == "interpretive"
    return result


def analyze_document(document: Document, trace: list[ToolEvent] | None = None) -> list[VerificationResult]:
    started = time.monotonic()
    claims = extract_scientific_claims(document)
    if trace is not None:
        trace.append(ToolEvent(tool="extract_scientific_claims", arguments={"document_sha256":document.sha256}, status="ok", summary=f"{len(claims)} candidates; limit 80", elapsed_ms=int((time.monotonic()-started)*1000)))
    results = []
    for claim in claims:
        started = time.monotonic()
        result = verify_numerical_claim(claim, document)
        results.append(result)
        if trace is not None:
            trace.append(ToolEvent(tool="verify_numerical_claim", arguments={"claim_id":claim.id, "source_id":claim.source_id}, status="ok", summary=f"{result.verdict.value}: {result.explanation}", elapsed_ms=int((time.monotonic()-started)*1000)))
    return results
