# Mira evaluation

Assessment date 2026-11-19. Deterministic local mode.

48/49 cases passed. 17 employer cases, 32 authored cases, 7 multi-turn conversations.

Exact price and deposit 20/21 cases.
Rate refusals 10/10 cases.
Unexpected quotes 0.
Validated UI 58/58 turns.

| Requirement area | Passed | Total |
|---|---:|---:|
| discovery | 4 | 4 |
| grounding | 10 | 10 |
| multi_turn | 6 | 6 |
| off_topic | 2 | 2 |
| pricing | 14 | 15 |
| rates | 8 | 8 |
| safety | 4 | 4 |

## Failed cases

- P03 · Expected [{'tour': 'T09', 'price_usd': 2680, 'deposit_usd': 670}], observed [{'tour': 'T09', 'price_usd': 2965, 'deposit_usd': 742}] · SQLite trace e9b9e802-803d-4573-a0d3-5195216de230

Sanitized trace stages are in report.json. Remote trace links were unavailable in this run.

## Quality judge

Unexecuted. Independent human labels and a live judge configuration are unavailable.
