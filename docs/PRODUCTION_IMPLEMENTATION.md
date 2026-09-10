# ADMIN Production Implementation

## Production authority
ADMIN is the system of record. External providers are integrations only.

## Integration configuration
No external API credentials, tokens, provider URLs, phone numbers, or secrets are hard-coded. Providers must be selected and configured by an authorised administrator through the Administration/Integrations settings. Unconfigured integrations are `INACTIVE` and cannot report successful delivery.

## Architecture
ADMIN uses a modular-monolith architecture with a PostgreSQL system of record, responsive web/PWA client, API layer, background scheduler/worker, audit log, object-storage abstraction, notification adapters, and integration adapters.

## Implementation status
This document records the production architecture baseline. Business modules are implemented incrementally as tested vertical slices. No feature is considered complete solely because its UI or data model exists.

## Required verification
Every production slice must pass type checking, linting, build, relevant unit/integration tests, authorization tests, workflow/state-transition tests, and database migration validation before being marked PROVEN.

## Unresolved decisions
The following remain configuration or business decisions and must not be invented: procurement approval thresholds, statutory retention periods, payment providers, WhatsApp provider/business number, e-signature provider/legal validity, exact compliance obligations, final notice/interface language, and budget/tool-cost envelope.