# Source audit

The original delivery lives under the top-level assignment folder. The README, brand JSON, rated workbook, sample quote emails, both versions of the brief, Markdown and JSONL remain unchanged. Run `shasum -a 256 -c docs/source-sha256.txt` from the workspace root.

| Input | Observed |
|---|---:|
| Tour documents | 16 |
| Destination documents | 10 |
| Policy, FAQ, about and testimonial documents | 6 |
| Seed JSONL records | 17 |
| Workbook tabs | 6 |
| Supplied licensed photographs or dataset ZIP | 0 |

The dataset README says 15 cases. The brief says 17. Counting the input JSONL confirms 17 unique IDs. All required input paths are present. The UI uses original SVG and CSS artwork.

| Source location | Irregularity | Handling |
|---|---|---|
| Hotels rows 8 and 10 | Double-room amounts use text such as LKR 28,000 | Accept an explicit well-formed LKR amount and parse with Decimal |
| Hotels rows 16–19, H04 | Single rates absent | Quote only compositions that do not require the missing rate |
| Hotels rows 29–31, H07 | Date intervals ended in October 2026 | Refuse modern rates for the Mirissa beach stay |
| Hotels row 33, H08 | Peak interval begins with a day/month/year string | Parse the explicit date format |
| Hotels rows 40–43, H10 | Row notes specify USD; header specifies LKR | Apply the fixed workbook FX to these specifically labeled contract costs |
| Hotels rows 13 and 56, H03 | Peak and unconfirmed revised intervals overlap | Refuse the affected night because neither overlapping row has priority |
| Tours row 7, T06 | One-day workbook scope conflicts with 1-night/2-day front matter | Refer to specialists until scope is reconciled |
| Tours row 13, T-13 | Content uses T13 and both titles match | Map content T13 to its explicitly documented workbook alias |
| Tours rows 14–15, T14 and T15 | Historical promotion and unpublished north tour | Exclude from active public catalogue and pricing |
| Tours tab | T10 and T16 have published content without a rate row | Browse with citations; send pricing requests to staff |
| Sample quote Q-1043 | Email omits LKR 64,000 in applicable child extra beds | Show workbook result and preserve email disagreement in P03 |
| Tour Markdown front matter | Historical teaser prices | Ignore for public quotes and exclude rate-like prose from excerpts |

The current rate workbook is hashed, read and validated in code. SQLite stores each imported workbook snapshot with its original SHA-256. Interpretations and pricing row numbers live in code and protected records. Loss or corruption of the source blocks new quotes rather than reviving an old snapshot. The supplied brief and files should only be transferred to the authorized reviewer through the private submission channel.
