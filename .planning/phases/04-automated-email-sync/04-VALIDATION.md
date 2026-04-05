---
phase: 4
slug: automated-email-sync
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.4 + pytest-asyncio 0.24.0 |
| **Config file** | `backend/pytest.ini` (exists — `testpaths = tests, asyncio_mode = auto`) |
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
| 4-01-01 | 01 | 0 | INFRA | infra | `python -m pytest tests/ --collect-only -q` | ✅ | ⬜ pending |
| 4-01-02 | 01 | 1 | GMAIL-05 | unit | `python -m pytest tests/test_gmail_service.py -v` | ❌ W0 | ⬜ pending |
| 4-01-03 | 01 | 1 | INFRA-03/04 | unit | `python -m pytest tests/test_scheduler.py -v` | ❌ W0 | ⬜ pending |
| 4-02-01 | 02 | 2 | GMAIL-06/07 | unit | `python -m pytest tests/test_scheduler.py -v` | ❌ W0 | ⬜ pending |
| 4-02-02 | 02 | 2 | GMAIL-08/10 | unit | `python -m pytest tests/test_gmail_settings.py -v` | ❌ W0 | ⬜ pending |
| 4-03-01 | 03 | 3 | GMAIL-07 | unit | `python -m pytest tests/ -v` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_gmail_service.py` — stubs for token refresh persistence (GMAIL-05)
- [ ] `backend/tests/test_scheduler.py` — stubs for scheduler job registration, interval logic, cleanup job (GMAIL-06, INFRA-03, INFRA-04)
- [ ] `backend/tests/test_gmail_settings.py` — stubs for settings API (GMAIL-08, GMAIL-10)
- [ ] `APScheduler==3.11.2` added to `backend/requirements.txt` and installed

*Existing infra (`pytest.ini`, `conftest.py`, 27 passing tests) covers everything else.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Auto-sync fires at scheduled time | GMAIL-06 | Requires waiting for scheduler trigger | Enable hourly sync, wait ~1min with shortened interval in dev, verify new transactions appear |
| "Last updated at" timestamp shows in IST | GMAIL-07 | Requires browser + live sync | Trigger sync, verify timestamp format matches "HH:MM DD MMM YYYY IST" in UI |
| Settings toggle persists across page reload | GMAIL-10 | Requires browser session | Toggle auto-sync on, reload page, verify toggle is still on |
| Gmail token refresh re-persisted | GMAIL-05 | Requires expired token scenario | Hard to simulate in unit tests — verify DB value changes after forced refresh |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
