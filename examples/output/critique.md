# LitWeaver AI — Research Critic

Document: numerical-audit.pdf

SHA-256: `15b6f9ed53dde32de58621c1cee04df19bb591751faf75e45bd543f91b463288`

Pages: 2

Scope: accessible text and reliably detected machine-readable tables. SUPPORTED means agreement with cited reported values or arithmetic, not independent replication. CONTRADICTED describes a documented inconsistency, not misconduct.

Verdicts: SUPPORTED: 5, CONTRADICTED: 2, INSUFFICIENT_EVIDENCE: 3

## C001 — SUPPORTED

Claim: \[context: demo/test/run1\] Model A accuracy = 87.4%.

Explanation: A separate source excerpt reports the same value in the same explicit context.

Method: Deterministic within-document numerical consistency

Human review flag: False

Calculation: Claim: 87.4 %; other reported values: 87.4 %

- [15b6f9ed53-p1-b13-s0] numerical-audit.pdf, page 1, Results: \[context: demo/test/run1\] Model A accuracy = 87.4%.

- [15b6f9ed53-p1-t0] numerical-audit.pdf, page 1, Results: Model \| Accuracy \(%\) \| Context Model A \| 87.4 \| demo/test/run1 Model B \| 84.2 \| demo/test/run1

Limitation: Checks concern reported text and arithmetic, not experimental truth or scientific validity.

## C002 — SUPPORTED

Claim: \[context: demo/test/run1\] Model B accuracy = 84.2%.

Explanation: A separate source excerpt reports the same value in the same explicit context.

Method: Deterministic within-document numerical consistency

Human review flag: False

Calculation: Claim: 84.2 %; other reported values: 84.2 %

- [15b6f9ed53-p1-b14-s0] numerical-audit.pdf, page 1, Results: \[context: demo/test/run1\] Model B accuracy = 84.2%.

- [15b6f9ed53-p1-t0] numerical-audit.pdf, page 1, Results: Model \| Accuracy \(%\) \| Context Model A \| 87.4 \| demo/test/run1 Model B \| 84.2 \| demo/test/run1

Limitation: Checks concern reported text and arithmetic, not experimental truth or scientific validity.

## C003 — CONTRADICTED

Claim: \[context: demo/test/run1\] Model B achieved higher classification accuracy than Model A.

Explanation: Comparison conflicts with reported values.

Method: Deterministic comparison of contextualized reported values

Human review flag: False

Calculation: model b: 84.2 %; model a: 87.4 %. Reported difference = -3.2 percentage points.

- [15b6f9ed53-p2-b1-s0] numerical-audit.pdf, page 2, Discussion: \[context: demo/test/run1\] Model B achieved higher classification accuracy than Model A.

- [15b6f9ed53-p1-b14-s0] numerical-audit.pdf, page 1, Results: \[context: demo/test/run1\] Model B accuracy = 84.2%.

- [15b6f9ed53-p1-t0] numerical-audit.pdf, page 1, Results: Model \| Accuracy \(%\) \| Context Model A \| 87.4 \| demo/test/run1 Model B \| 84.2 \| demo/test/run1

- [15b6f9ed53-p1-b13-s0] numerical-audit.pdf, page 1, Results: \[context: demo/test/run1\] Model A accuracy = 87.4%.

Limitation: Checks concern reported text and arithmetic, not experimental truth or scientific validity.

## C004 — SUPPORTED

Claim: \[context: demo/test/run1\] Model A achieved higher accuracy than Model B.

Explanation: Comparison agrees with reported values.

Method: Deterministic comparison of contextualized reported values

Human review flag: False

Calculation: model a: 87.4 %; model b: 84.2 %. Reported difference = 3.2 percentage points.

- [15b6f9ed53-p2-b2-s0] numerical-audit.pdf, page 2, Discussion: \[context: demo/test/run1\] Model A achieved higher accuracy than Model B.

- [15b6f9ed53-p1-b13-s0] numerical-audit.pdf, page 1, Results: \[context: demo/test/run1\] Model A accuracy = 87.4%.

- [15b6f9ed53-p1-t0] numerical-audit.pdf, page 1, Results: Model \| Accuracy \(%\) \| Context Model A \| 87.4 \| demo/test/run1 Model B \| 84.2 \| demo/test/run1

- [15b6f9ed53-p1-b14-s0] numerical-audit.pdf, page 1, Results: \[context: demo/test/run1\] Model B accuracy = 84.2%.

Limitation: Checks concern reported text and arithmetic, not experimental truth or scientific validity.

## C005 — CONTRADICTED

Claim: Accuracy improved by 12% from 80.0% to 92.0%.

Explanation: The claimed change conflicts with the stated inputs, even allowing for displayed rounding.

Method: Deterministic percentage/percentage-point arithmetic

Human review flag: False

Calculation: 1 × \(92 - 80\) / 80 × 100 = 15 %; claimed 12.

- [15b6f9ed53-p2-b3-s0] numerical-audit.pdf, page 2, Discussion: Accuracy improved by 12% from 80.0% to 92.0%.

Limitation: Checks concern reported text and arithmetic, not experimental truth or scientific validity.

Limitation: Operands come from this statement; agreement does not independently corroborate them.

## C006 — SUPPORTED

Claim: Accuracy improved by 15% from 80.0% to 92.0%.

Explanation: The stated arithmetic agrees with the displayed values at the claim's precision.

Method: Deterministic percentage/percentage-point arithmetic

Human review flag: False

Calculation: 1 × \(92 - 80\) / 80 × 100 = 15 %; claimed 15.

- [15b6f9ed53-p2-b4-s0] numerical-audit.pdf, page 2, Discussion: Accuracy improved by 15% from 80.0% to 92.0%.

Limitation: Checks concern reported text and arithmetic, not experimental truth or scientific validity.

Limitation: Operands come from this statement; agreement does not independently corroborate them.

## C007 — SUPPORTED

Claim: Accuracy increased by 12 percentage points from 80.0% to 92.0%.

Explanation: The stated arithmetic agrees with the displayed values at the claim's precision.

Method: Deterministic percentage/percentage-point arithmetic

Human review flag: False

Calculation: 1 × \(92 - 80\) = 12 percentage points; claimed 12.

- [15b6f9ed53-p2-b5-s0] numerical-audit.pdf, page 2, Discussion: Accuracy increased by 12 percentage points from 80.0% to 92.0%.

Limitation: Checks concern reported text and arithmetic, not experimental truth or scientific validity.

Limitation: Operands come from this statement; agreement does not independently corroborate them.

## C008 — INSUFFICIENT_EVIDENCE

Claim: Our findings prove that the approach generalizes to all hospitals.

Explanation: Related passages are candidates only. The supported grammar or explicit contextual evidence is insufficient for a verdict.

Method: Deterministic verification

Human review flag: True

- [15b6f9ed53-p2-b6-s0] numerical-audit.pdf, page 2, Discussion: Our findings prove that the approach generalizes to all hospitals.

- [15b6f9ed53-p1-b16-s0] numerical-audit.pdf, page 1, Results: LitWeaver AI \| Synthetic verification fixture - no real scientific findings 1

- [15b6f9ed53-p2-b12-s0] numerical-audit.pdf, page 2, Limitations: LitWeaver AI \| Synthetic verification fixture - no real scientific findings 2

Limitation: Checks concern reported text and arithmetic, not experimental truth or scientific validity.

## C009 — INSUFFICIENT_EVIDENCE

Claim: The broad hospital claim has no supporting experiment.

Explanation: Related passages are candidates only. The supported grammar or explicit contextual evidence is insufficient for a verdict.

Method: Deterministic verification

Human review flag: True

- [15b6f9ed53-p2-b9-s1] numerical-audit.pdf, page 2, Limitations: The broad hospital claim has no supporting experiment.

- [15b6f9ed53-p2-b11-s0] numerical-audit.pdf, page 2, Limitations: Flag the claim that Model B has higher accuracy.

- [15b6f9ed53-p2-b11-s2] numerical-audit.pdf, page 2, Limitations: Abstain on the broad generalization.

- [15b6f9ed53-p1-b7-s1] numerical-audit.pdf, page 1, Methods: The table below is machine-readable and has explicit context

- [15b6f9ed53-p1-b15-s1] numerical-audit.pdf, page 1, Results: These values are not the model-comparison experiment above.

Limitation: Checks concern reported text and arithmetic, not experimental truth or scientific validity.

## C010 — INSUFFICIENT_EVIDENCE

Claim: Abstain on the broad generalization.

Explanation: Related passages are candidates only. The supported grammar or explicit contextual evidence is insufficient for a verdict.

Method: Deterministic verification

Human review flag: True

- [15b6f9ed53-p2-b11-s2] numerical-audit.pdf, page 2, Limitations: Abstain on the broad generalization.

- [15b6f9ed53-p2-b9-s1] numerical-audit.pdf, page 2, Limitations: The broad hospital claim has no supporting experiment.

Limitation: Checks concern reported text and arithmetic, not experimental truth or scientific validity.

## Model-suggested concerns

Potential concerns requiring human review; these do not change the evidence verdicts.

No model-suggested concerns were generated or accepted.