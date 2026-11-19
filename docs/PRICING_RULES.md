# Pricing rules

1. Require an actively published tour, date, invited party composition, unique workbook tour, and unique season coverage for every tour day. Unpublished, historic and conflicting products fail closed.
2. Count adults and travellers aged 12 or older for adult rates. Count ages 2–11 for seats and child rates. Infants under 2 cost nothing. Require at least one accompanying adult.
3. Select the vehicle from a unique applicable row. Multiply its daily buy cost and the guide cost by tour days. Add entrance costs and meal costs, with children paying half the adult meal buy cost.
4. Match one rate per booked hotel night, including the first night. Use double rooms for adult pairs, a single room for an odd adult, and one extra bed per eligible child every night.
5. Divide total LKR buy cost by fixed LKR/USD FX times one minus the configured sales margin. Round up in USD 5 steps with Decimal. Compute realized gross profit from the rounded sale for staff.
6. Day trips and departures within 30 calendar days pay in full. Other multi-day trips use the configured deposit, rounded up to a whole USD. Keep cost, realized profit, row references and hash in staff storage.
7. If any applicable component is absent, past, malformed, ambiguous, inconsistent with published tour scope or outside FX validity, save a flag and withhold price. Saved quotes and bookings are rechecked against the active snapshot and current assessment clock.

## Sample outcomes

| Sample | Workbook buy cost (LKR) | Sale (USD) | Deposit (USD) | Comparison |
|---|---:|---:|---:|---|
| Q-1041 | 66,000 | 315 | 315 | Matches |
| Q-1042 | 477,500 | 2,125 | 532 | Matches |
| Q-1043 | 667,000 | 2,965 | 742 | Email differs; starter S03 agrees |
| Q-1044 | 563,000 | 2,505 | 2,505 | Matches |

Q-1043 uses six nights across hotel IDs H12, H02 and H03. Extra-bed buy cost is `2 children × 2 nights × (4,500 + 6,000 + 5,500) = LKR 64,000`. Adding it to the email's cost produces LKR 667,000. The source email remains unchanged and the test suite shows its disagreement explicitly.

Run `make test` for direct rules and `make eval` for end-to-end checks through AG-UI.
