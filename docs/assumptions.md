# Assumptions Register — PROVEN / INFERRED / DECISION_REQUIRED
## Architecture package — required by §78

> Master document: [`architecture.md`](architecture.md). Classification:
> - **PROVEN** — stated in the source PDFs or the master build prompt.
> - **INFERRED** — a low-risk, reversible default I chose to keep the build moving (§78: continue
>   with clearly marked `INFERRED` decisions where they are low-risk and reversible).
> - **DECISION_REQUIRED** — genuinely missing and material to financial correctness, legal effect,
>   security, data integrity, or architectural direction (§70, §78). Isolated so the build continues;
>   the system is designed to configure the answer later.

---

## 1. PROVEN

| # | Assumption | Source |
| --- | --- | --- |
| P-01 | 14 key farm/property areas + daily/weekly routines + control cycle | Workplan PDF |
| P-02 | Tenant placement, lease admin, rent, maintenance, records, legal compliance, customer service | Job Description PDF |
| P-03 | 25 domains, 9 roles, permission action vocabulary, task/lease/maintenance/incident/stock/application status enums | Master prompt §3, §5, §6, §14–§30 |
| P-04 | Control cycle `PLAN → ASSIGN → EXECUTE → MONITOR → VERIFY → RECORD → REPORT → FOLLOW UP` | Workplan + §1 |
| P-05 | No auto-approvals for applications, leases, payments/refunds, procurement, legal action, termination, stock adjustments | §53 |
| P-06 | Timezone **Africa/Maseru**; append-only payments; no silent stock alterations | §8, §18, §26 |
| P-07 | Escalation ladders: task D−1/D0/D+1/D+2/D+5; arrears 30/60/90; lease −90/−60/−30 | §11, §17, §19 |

## 2. INFERRED (reversible defaults)

| # | Assumption | Why it's safe | Change point |
| --- | --- | --- | --- |
| I-01 | Start stack = Google Workspace (Sheets/Forms/Apps Script), migrate to PostgreSQL+n8n when triggered | low cost, reversible; ADR-001 | Architecture review |
| I-02 | Interface & notices in English + Sesotho | user-requested locale unknown; i18n from Phase 1 makes it configurable | Q-01 |
| I-03 | Officer is the primary operator; HoSS approves tenancy & refunds | matches reporting line in the JD | Role config |
| I-04 | Reports delivered as PDF + archived as DOCUMENT | standard; snapshot reference retained | Report settings |
| I-05 | Tenant-facing channel is WhatsApp (provider TBD) | ubiquity + low bandwidth | Integration config |
| I-06 | Field app is a PWA (installable, offline capture) | fits low-connectivity sites; no app-store dependency | Device strategy |
| I-07 | Attendance exports to payroll as CSV only (no live HR link) | explicit §25 ("not the payroll system") | Integration |
| I-08 | Seed data = baseline configuration only (no fabricated operational data) | explicit §56 | — |

## 3. DECISION_REQUIRED

| # | Decision | Material impact | Blocking phase | Owner |
| --- | --- | --- | --- | --- |
| D-01 | **Procurement approval thresholds** (who approves what value) | financial correctness | Phase 7 | HoSS |
| D-02 | **Statutory retention periods** (tenant/financial/legal records) | legal effect | Phase 1 config | Legal |
| D-03 | **Payment integrations**: bank / M-Pesa / EcoCash / other | financial correctness | Phase 4/10 | HoSS |
| D-04 | **Official WhatsApp provider & Business number** | communications | Phase 10 (capture pilot) | Officer |
| D-05 | **E-signature provider & legal validity confirmation** | legal effect | Phase 3 | Legal |
| D-06 | **Exact compliance obligations** (regulators, licences, deadlines) | legal effect | Phase 8 | Officer/HoSS |
| D-07 | **Interface/notice language** (en / st / both) | usability | Phase 1 (i18n scaffold exists regardless) | Officer |
| D-08 | **Budget envelope & approval process for recurring tool costs** | cost model | Phase 10 | Management |

> Each `DECISION_REQUIRED` item is **isolated**: the system exposes it as configuration
> (`SYSTEM_SETTING`), an adapter placeholder, or a seeded value marked "PENDING CONFIGURATION" — the
> rest of the build proceeds without silently guessing (§70).

## 4. Handling rules (§78)

- Continue past `INFERRED` items without asking; they are recorded here and reversible.
- Stop and request clarification **only** for `DECISION_REQUIRED` items that would materially affect
  financial correctness, legal effect, security, data integrity, architectural direction, or
  irreversible implementation — and only when that item's phase is reached.

---

*End of the architecture package. Master document: [`architecture.md`](architecture.md).*
