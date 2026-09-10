# Integrations

## Authority
ADMIN is the system of record. External systems are adapters and never the authoritative store for ADMIN business state.

## Configuration rule
External APIs/providers MUST NOT be hard-coded. Provider selection, endpoints, identifiers and credentials are supplied through authorised ADMIN administration/configuration. Secrets must be stored securely and must never be committed to source control or returned by ordinary settings APIs.

An integration with missing configuration is `INACTIVE` / `NOT_CONFIGURED`; the application must not simulate success.

## Adapter architecture
Domain service → port/interface → provider adapter → external API.

Core business modules must not import provider SDKs directly. Provider adapters translate between ADMIN's stable contracts and external APIs.

## Planned integration categories
- WhatsApp Business API — provider decision required.
- Email/SMTP — provider configuration required.
- SMS — provider decision required.
- Mobile money/bank — provider decision required; statement import may be supported.
- E-signature — provider and legal-validity decision required.
- Object storage — provider configuration required.
- Accounting — export/API configuration required.
- HR/payroll — attendance export/API configuration required.
- Government and utility portals — provider/process decision required.

## Reliability
Webhook consumers must validate signatures when the provider supports them, use idempotency keys, persist inbound events, retry safely, and expose failures. Outbound messages must have delivery state and retry/dead-letter handling where appropriate.

## No fake integrations
Never return a successful provider result when the provider is not configured or the external request was not actually accepted.