# Security, Privacy & Audit Architecture
## Architecture package — items 16 & 17

> Master document: [`architecture.md`](architecture.md). Authorisation is server-side; audit is
> immutable; financial/legal records are never silently overwritten.

---

## 1. Security architecture (§44)

### 1.1 Identity & authentication

- Username/email + password with **strong password hashing** (Argon2id/bcrypt, never plaintext).
- **Secure sessions** (HttpOnly, SameSite cookies; CSRF protection on state-changing routes).
- **MFA-ready from day one:** TOTP field + enforced-at-login flag; enforcement is a config toggle.
- Password reset via one-time, expiring, single-use tokens over email.
- Session management: expiry, revocation, device/IP metadata, forced logout.

### 1.2 Authorisation (see [`role-permission-matrix.md`](role-permission-matrix.md))

- RBAC + **4-level permission tuple** (module → action → record → field).
- Enforced in the **application layer**, not the UI; denial events are audited.
- Record-scope filtering (assigned/team/own/all) applied at the query layer.
- Field-level redaction for sensitive columns.

### 1.3 Transport & storage

- **TLS everywhere** (HTTPS, SMTP-TLS, webhook TLS).
- **Encryption at rest** for the database and object storage where supported.
- **Secrets management:** API keys/tokens in a secret store (env/vault); never hard-coded or committed.
- **File security:** uploaded files validated (type, size, content sniffing); stored outside the DB as
  metadata + object storage (§46); served through permission-checked endpoints, never public URLs.
- **Rate limiting** on auth and webhook endpoints; lockout after repeated failures.
- **Webhook verification:** signature/secret verification before any inbound event is accepted.

### 1.4 Threat model (top risks → mitigations)

| Threat | Mitigation |
| --- | --- |
| Credential stuffing | rate limit + lockout + MFA |
| Privilege escalation | server-side permission checks + audit of denials |
| Data exfiltration (tenant PII) | RBAC, field redaction, export permission, audit |
| Malicious uploads | content-type/size validation, non-executable storage, scan-ready design |
| Webhook spoofing | signature verification + idempotency keys |
| Insider misuse | immutable audit log, append-only financial records |
| Ransomware/loss | encrypted off-site backups, RPO ≤ 24 h / RTO ≤ 1 working day |

---

## 2. Privacy architecture (§45)

- **Minimisation:** collect only fields in the data dictionary (§11); sensitive ID fields are
  role-restricted and redacted by default.
- **Data-subject rights:** access / correction / deletion workflows supported by the records domain;
  deletion is soft unless legally mandated (and always audited).
- **Retention & deletion:** schedule per classification (tenant/financial/legal/operational);
  `DECISION_REQUIRED: statutory retention periods` ([`assumptions.md`](assumptions.md)).
- **Compliance posture:** designed toward POPIA-style obligations, but **no legal-compliance claim is
  made automatically** — legal requirements needing professional confirmation are flagged
  `DECISION_REQUIRED` (§45, §70).

---

## 3. Audit architecture (§38, §69)

### 3.1 What is audited

Every **important mutation**: creates, edits, state transitions, approvals, rejections, verification,
payments, reversals, document uploads, permission changes, exports of sensitive data, login/logout,
and **every automated action** (task generation, reminders, escalations, invoice generation, status
changes, reports, notifications).

### 3.2 Audit record

```text
actor (user|system|scheduler) · action · entity · entity_id · timestamp
previous_value · new_value · ip/device (where applicable) · source · correlation_id
```

### 3.3 Rules

| Rule | Implementation |
| --- | --- |
| Immutable | append-only `AUDIT_LOG`; no update/delete paths |
| Complete | before/after JSON for every audited mutation |
| Financial/legal correctness | original record + reversal/adjustment + audit event — never overwrite (§38) |
| Automation traceable | "why did this happen?" = trigger → rule → input → action → result → job id (§66, §69) |
| Access-controlled | audit views restricted (SysAdmin/Admin Officer/HoSS read-only) |
| Retained | audit log retention follows the legal record schedule |

### 3.4 Automation audit example

```text
task.created  ← TASK_TEMPLATE("Weekly review & report", id=9)
             ← SCHEDULER_RUN(#481, 2026-09-11 14:00 Africa/Maseru)
             ← OCCURRENCE(template_id=9, occurrence_date=2026-09-11)
```

The officer can always answer: *why was this task created, by what rule, from what run?*

---

## 4. Global activity timeline (§48)

Derived from `SYSTEM_EVENT` + `AUDIT_LOG` (never manually maintained), rendered per entity:

```text
Application submitted → Vetting completed → Approved → Lease signed →
Invoice generated → Payment received → Maintenance request → Inspection → Renewal notice
```

Available on any entity that participates in events (tenant, lease, unit, task, incident, asset,
stock item, purchase order).

---

*Next in package: [`offline-sync.md`](offline-sync.md).*
