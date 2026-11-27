# Mira evaluation

Assessment clock 2026-11-19. Local deterministic mode. Generated 2026-11-27T17:44:53.893177+00:00.

**53/54 cases passed (98.1%).**
Includes 17 supplied cases, 37 authored cases and 7 multi-turn conversations.
Validated 63 of 63 planned turns.
Exact quotes matched in 23/24 pricing cases.
No-price and specialist-handoff cases passed 11/11.
Observed 0 unexpected quote components.

| Requirement | Passed | Cases | Rate |
|---|---:|---:|---:|
| authorization | 2 | 2 | 100.0% |
| booking | 3 | 3 | 100.0% |
| discovery | 4 | 4 | 100.0% |
| grounding | 10 | 10 | 100.0% |
| multi_turn | 6 | 6 | 100.0% |
| off_topic | 2 | 2 | 100.0% |
| pricing | 14 | 15 | 93.3% |
| rates | 8 | 8 | 100.0% |
| safety | 4 | 4 | 100.0% |

## Failures

### P03

Expected [{'tour': 'T09', 'price_usd': 2680, 'deposit_usd': 670}], observed [{'tour': 'T09', 'price_usd': 2965, 'deposit_usd': 742}]

[Trace 3b093a37-f335-4b72-8111-3f05a1c5f5a6](#trace-3b093a37-f335-4b72-8111-3f05a1c5f5a6)


## Failed-case trace snapshots

### Trace 3b093a37-f335-4b72-8111-3f05a1c5f5a6

```json
[
  {
    "stage": "interpret",
    "provider": "local rules",
    "action": "discover",
    "ms": 0
  },
  {
    "stage": "retrieval",
    "sources": [
      "T09"
    ],
    "ms": 0
  },
  {
    "stage": "pricing",
    "outcome": "verified",
    "snapshot": "a16dd63ffb7ed2324e9d709f4b35e1bb3f0d5c2123b765903bce039f5fefdfe2",
    "rate_digest": "a16dd63ffb7ed2324e9d709f4b35e1bb3f0d5c2123b765903bce039f5fefdfe2",
    "ms": 2
  },
  {
    "stage": "validated_ui",
    "components": [
      "PriceBreakdown",
      "TourCard",
      "ItineraryDay",
      "BookingForm"
    ],
    "ms": 0
  },
  {
    "stage": "persistence",
    "enquiry": true,
    "request_id": "d7c4690a-60bc-4722-8b1c-1e265b474894",
    "ms": 1
  }
]
```


## Judge calibration

Live judge scored 10/10 review cases. Human calibration pending.
