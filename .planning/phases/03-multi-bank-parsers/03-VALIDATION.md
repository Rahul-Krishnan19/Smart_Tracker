---
phase: 3
slug: multi-bank-parsers
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.4 + pytest-asyncio 0.24.0 |
| **Config file** | none — Wave 0 creates `backend/pytest.ini` |
| **Quick run command** | `cd backend && source venv/Scripts/activate && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && source venv/Scripts/activate && python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && source venv/Scripts/activate && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && source venv/Scripts/activate && python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 0 | INFRA | infra | `python -m pytest tests/ -x -q` | ❌ W0 | ⬜ pending |
| 3-01-02 | 01 | 1 | INFRA-01/02 | unit | `python -m pytest tests/test_migrations.py -v` | ❌ W0 | ⬜ pending |
| 3-02-01 | 02 | 1 | PARSE-09 | unit | `python -m pytest tests/test_hdfc_parser.py -v` | ❌ W0 | ⬜ pending |
| 3-02-02 | 02 | 1 | PARSE-03 | unit | `python -m pytest tests/test_icici_parser.py -v` | ❌ W0 | ⬜ pending |
| 3-02-03 | 02 | 1 | PARSE-04 | unit | `python -m pytest tests/test_sbi_parser.py -v` | ❌ W0 | ⬜ pending |
| 3-02-04 | 02 | 2 | INFRA-05 | unit | `python -m pytest tests/test_email_sync_service.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/pytest.ini` — pytest config with testpaths = tests, asyncio_mode = auto
- [ ] `backend/tests/__init__.py` — empty init to make tests a package
- [ ] `backend/tests/conftest.py` — shared fixtures (in-memory SQLite DB, sample email dicts for HDFC/ICICI/SBI)
- [ ] `backend/tests/test_hdfc_parser.py` — stubs for HDFC date fallback (PARSE-09 partial)
- [ ] `backend/tests/test_icici_parser.py` — stubs for ICICI parsing (PARSE-03)
- [ ] `backend/tests/test_sbi_parser.py` — stubs for SBI parsing (PARSE-04)
- [ ] `backend/tests/test_email_sync_service.py` — stubs for parse_failed/unmatched split (INFRA-05)
- [ ] `backend/tests/test_migrations.py` — stubs for Alembic migration (INFRA-01/02)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real ICICI email parses end-to-end via /api/gmail/sync | PARSE-03 | Requires live Gmail OAuth session | Trigger sync, verify ICICI transaction appears in DB with payment_source="ICICI CC ••XXXX" |
| Real SBI email parses end-to-end via /api/gmail/sync | PARSE-04 | Requires live Gmail OAuth session | Trigger sync, verify SBI debit appears in DB; verify FD/TDS emails are skipped |
| Alembic upgrade head on fresh DB works at startup | INFRA-01 | Requires running the server | Delete DB, start server, verify alembic_version table created and at head |
| Alembic stamp + upgrade on existing DB works | INFRA-01 | Requires existing DB state | Backup existing DB, run stamp + upgrade, verify data intact |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
