# MIRA semantic discovery verification

The existing isolated branch is `fix/semantic-recommendation-root-cause`. Its starting worktree contained an uncommitted workflow refactor and existing evaluation results. The before measurement used that worktree. The submitted branch and development branch still point at `75d40b8`. No commit, push, workbook edit, or dataset migration was part of this upgrade.

## Failure analysis and changes

| Observed failure | Cause in the former path | Change and measured result |
| --- | --- | --- |
| Family wildlife request yielded a greeting | The classifier treated children as quote-party input. With no named tour the discovery node retrieved no record. | A party mention can accompany an experience request. “My children love elephants and wild animals” selected T13 in both final runs. |
| Mountain requests included incidental stops | Matching the beginning of a description, wide synonym expansion and counting any location hit gave a mixed circuit credit for a single stop. | Title, primary description and itinerary passages have different weights. Relevance and score cutoffs allow shorter lists. “Railway windows and views of plantations” went from T06, T01 and T09 to T06 alone in both final runs. |
| Unrelated messages produced travel cards | Unrecognized input fell through to general discovery. The ranker sorted every candidate, even at zero relevance. Some paths seeded three fixed IDs. | Empty results are supported. A software backlog request following a safari search cleared the old results. Off-topic turns receive a travel-scope response. |
| Valid Gemini JSON selected irrelevant tours | Membership in a filtered ID list was the only substantive validation. The model had to choose at least one ID, saw a short prefix and supplied no citation. | The discovery schema permits zero to three IDs with passage references. Server code checks membership, uniqueness, evidence bounds, topical support, primary-match confidence, exclusions and supported hard constraints. The live holdout included a schema-valid output rejected by the relevance validator. |

The existing interpret and retrieve nodes dispatch discovery separately from quote, policy, enquiry, booking, publication and notebook operations. The provider sees bounded traveller text with common identifiers redacted, structured discovery context and compact published evidence. A separate structured schema can map unfamiliar wording to a catalogue concept when lexical retrieval has no match. The server checks the phrase against the message and the concept against a cited passage. A phrase-to-concept judgement remains a model inference.

The local scorer uses a shared experience vocabulary, per-passage overlap, coverage and primary-experience weighting. It reads eligible catalogue rows at request time. Discovery context stores interests, exclusions and supported constraints for refinements. Evidence indices, validated passages, candidates, scores, selected IDs and fallback decisions are available in trace stages. The code uses the existing database and Gemini adapter.

## Relevance results

The check sends real AG-UI turns, including follow-ups, then grades the first card, every additional card, the three-card limit, source IDs and absence of booking or price components. Empty-result cases require a clarification, scope response or refusal. Expectations were written from catalogue content before the corresponding first run. The rubrics were preserved through subsequent repairs.

| Set | Initial offline | Final offline | Live configuration | Accepted Gemini decisions alone |
| --- | ---: | ---: | ---: | ---: |
| Development rubric, 24 cases | 5/24 before implementation | 24/24 | 24/24 | 14/14 |
| Second rubric, 20 additional cases | 16/20 on first exposure to the enhanced system | 20/20 | 19/20 | 14/15 |
| Final combined | | 44/44 | 43/44 | 28/29 |

The first live pass on the additional 20 cases scored 16/20. The final rerun measures repairs on those cases. It is not an estimate from another untouched holdout. The final live runs used the configured Gemini service. Of 44 final decisions, 29 were accepted Gemini responses, nine used local fallback after a provider or evidence failure, one used local results after a returned list failed the final relevance check, and five used deterministic or unsupported-constraint handling. Live calls encountered intermittent service and quota errors during verification.

The sole final live miss was “My kids want to visit a gem museum”. The expected city tour T02 ranked first. T07 also includes a gem museum on its itinerary, but the independently specified allowlist included only T02. Its extra card counts as a failure. No assertion was changed. Full prompts, expected IDs, actual IDs, replies and selection provenance are in [the machine-readable results](../evals/report/semantic_discovery.json).

## Requirement compatibility

| Assignment area | Verification and outcome |
| --- | --- |
| Trip discovery and three-question limit | Direct and broad exploration, party mentions, scope changes and grounded alternatives covered. Semantic no-match replies stop asking after the third attempt and offer a custom enquiry. The existing three-question flow passes. |
| Returning visitor memory and private enquiries | Existing session, consent, quote history, enquiry ownership, lifecycle, recovery and authorization tests pass in the backend. A pre-existing registration-only browser failure is recorded below. |
| Five-node typed LangGraph, A2UI and AG-UI | The graph and its public state and transport contracts were retained. All 63 planned turns in the original evaluator validated. The backend graph and schema characterization tests pass. |
| Grounding and publication | Discovery reads published tours and destinations and the existing publication overlay. Existing historical exclusions remain in effect. Draft rejection, fabricated IDs, invalid passage indices, irrelevant citations and destination ranking have regression coverage. Original grounding results were 10/10. |
| Pricing, margin, deposit and confidentiality | All price arithmetic remains in deterministic code. The original evaluator observed zero invented prices and 23/24 exact sample comparisons. Q-1043 still computes USD 2,965 with USD 742 deposit. The source email expects USD 2,680 and USD 670. The difference includes LKR 64,000 in child extra-bed costs. |
| Missing, expired or ambiguous rates | All 11/11 no-price and specialist-handoff cases passed. Existing rate validation, enquiry creation and rate preview suites ran. |
| Approval, roles and booking | Original authorization checks passed 2/2 and booking checks 3/3. Backend approval-only publication, visitor isolation and mocked booking failure recovery run through their existing endpoints. |
| Data, configuration and infrastructure | Original supplied files and configurable assessment clock retained. The conversational evaluator ran at 2026-11-19. No new service or vector index. |
| Tracing and model authority | A model decision contains only bounded selections, evidence references and, where requested, mapped concepts. Discovery cannot dispatch quote, payment or publishing operations. Debug logging suppresses discovery model prompts and remote trace input uses an operation label. |

## Regression suites and remaining limitations

- The complete backend suite passed 241/241, including the loopback observability check. The frontend component suite passed 73/73 in nine files. Both frontend TypeScript checks passed.
- Original conversational evaluation passed 53/54 across 17 supplied and 37 authored cases, including seven multi-turn conversations. The sole failure was the documented Q-1043 sample disagreement.
- Next.js Playwright passed 16/17 on the warmed isolated service. The failed flow registers directly, then requests the traveller overview without first establishing a visitor cookie. The overview returned HTTP 401. A separate run against an archive of the frozen backend reproduced registration 200, signed-in profile 200 and overview 401.
- The dedicated production workspace Playwright suite passed 9/10. The family scenario generated the six-day proposal. Its strict locator for JourneyPlan matched both the chat component and the workspace panel. The frozen frontend contains both markers.
- The separate legacy notebook smoke test timed out waiting for the retired homepage hero. The submitted server redirects the homepage to the workspace before that selector can appear.
- Gemini availability and exact ranking vary between runs. Local fallback is English-language lexical scoring with a travel vocabulary. Novel paraphrases, nested negation, implicit location constraints and nuanced changes of preference remain difficult. A published itinerary mention does not prove personal suitability or accessibility. Unverified budgets and accessibility requirements trigger abstention.
- Redaction covers common contact and credential formats. No general-purpose person-name recognizer or independent privacy audit was added. The use of a live service was verified on synthetic traveller messages.

## Reproduce

Run from the repository root with the existing virtual environment. Each discovery command writes one JSON record per case to stdout and a summary to stderr. A rubric failure produces a nonzero exit code, as does a live run with no accepted model decisions.

```sh
PYTHONPATH=apps/api .venv/bin/python evals/discovery.py
PYTHONPATH=apps/api .venv/bin/python evals/discovery.py --holdout
PYTHONPATH=apps/api .venv/bin/python evals/discovery.py --live
PYTHONPATH=apps/api .venv/bin/python evals/discovery.py --live --holdout
make test
make eval
make browser
make workspace-browser
make notebook-browser
```

The live evaluator reads only the provider configuration from the environment or local .env. The discovery and original conversational evaluators use temporary databases. Browser suites need their respective services and fixture accounts. The original evaluation was run with its report directory redirected to a temporary location to preserve the prior working-tree reports.
