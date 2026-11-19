# Before and after

## M02, changing a child’s age

The first complete run of the conversational evaluation produced USD 365 twice. The first turn correctly priced an 11-year-old. The second turn said “Actually the child’s age is 12.” The age extractor only accepted a number immediately after “age,” so Mira reissued the original amount.

The failing run produced local traces a17963a0-99e0-4471-8849-2ebb2274febd and 709d9cbc-bcc7-4229-b06b-1051bb79d28a. These identifiers were captured by the evaluator. The temporary database from that run has been removed.

The parser now accepts “age is” and “ages are” and recognizes singular child counts. M02 stays in the suite with the independent expected sequence USD 365 → USD 410. See the current report for the rerun and trace evidence.

## Q-1042, text-valued room rate

The first direct workbook run rejected “LKR 28,000” with missing_amount. The importer stripped the explicit currency and comma but left a string that its numeric type check rejected. Converting the recognized value directly to Decimal produced LKR 477,500 total, USD 2,125 price and USD 532 deposit. The pricing suite covers the fix.
