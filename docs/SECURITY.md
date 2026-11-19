# Security and privacy

Mira is a loopback-bound fictional booking product. It never asks for payment or contact information. The browser stores a high-entropy HttpOnly SameSite=Lax session cookie. Remembering the browser adds 30-day persistence. Forgetting removes its ownership and trip context. Internal business records and sanitized stage traces are retained independently.

Staff use independent environment-configured bearer capabilities. The UI keeps these in memory and the API compares the supplied token in constant time. An Editor can create and inspect drafts. Only an Approver can publish a draft. Ledger updates and draft release actions append audit rows. Protected finance and follow-up endpoints enforce permissions on each call. Generated content is held to publication status even if the model claims approval.

Mutations validate browser origin and never trust client-provided visitor IDs, tool state, money or roles. Cross-visitor quotes and booking references are checked in SQLite. Draft content is plain text. Public retrieval excludes unapproved content, and visible cards and sources pass a fixed catalogue. Credentials and Docker state should remain private.

The local trace captures stage names, source IDs, safe outcomes, validation, workbook hash and persistence. Raw chat, visitor tokens and staff notes are excluded from stored trace metadata. The AG-UI message stream is delivered to its originating browser and the CopilotKit runner has ephemeral in-process event state. Do not type real personal information into this demo.

The local token model, guest traffic controls, retention and rate controls are suitable for an isolated demonstration. A production launch requires named staff identities, secret rotation, distributed rate limiting, TLS and a formal retention policy.
