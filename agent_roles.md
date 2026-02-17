# Agent Role Assignment: RSS News Filtering System

## Project Overview

Build a system that:
1. Runs every 12 hours
2. Fetches all RSS feed articles published within the last 12 hours
3. Deduplicates articles using a local LLM (Ollama)
4. Generates an HTML email with article titles and links
5. Sends the email via Gmail to personal and company addresses

## Agent Assignments

| Phase | Agent | Responsibilities |
|---|---|---|
| **Design** | **Gemini 2.5 Pro** | Requirements, architecture, data flow, API design, component interfaces, scheduling strategy, non-functional requirements |
| **Design Review** | **Claude Code** | Identify contradictions, undefined behaviors, edge cases, dependency issues, implementation feasibility, produce question list |
| **Implementation** | **Codex** | Implement all components: RSS fetcher, LLM dedup, HTML email builder, Gmail sender, scheduler |
| **Test Design** | **Claude Code** | Test plan, test cases, boundary conditions, acceptance criteria traceability, risk-based prioritization |
| **Test Implementation + Execution** | **Codex** | Write test code, run tests, collect results |
| **Test Result Review** | **Gemini 2.5 Pro** | Evaluate pass/fail validity, coverage analysis, identify gaps, additional test recommendations |
| **Refactoring (optional)** | **Codex** | Lint, type annotations, code cleanup, formatting |

## Independence Chain

```
Design (Gemini)
    ↓
Design Review (Claude)
    ↓
Implementation (Codex)
    ↓
Test Design (Claude)
    ↓
Test Implementation + Execution (Codex)
    ↓
Test Result Review (Gemini)
```

### Independence Guarantees

- **No agent handles two consecutive phases alone** (except Codex for Implementation → Test Design is handed off to Claude)
- **Codex** focuses on writing code (implementation + test code) but never designs or reviews
- **Claude Code** focuses on review and design (design review + test design) but never implements
- **Gemini 2.5 Pro** bookends the process (design + final review) with full context, separated by 4 phases from each other

### Bias Prevention

| Risk | Mitigation |
|---|---|
| Implementer writes tests that pass trivially | Test design (Claude) is independent from implementer (Codex) |
| Test designer overlooks own blind spots | Test implementation (Codex) and review (Gemini) are separate agents |
| Design flaws propagate unchecked | Design review (Claude) catches issues before implementation begins |
| Test results rubber-stamped | Reviewer (Gemini) has full design context but was not involved in test design or implementation |

## Workflow per Phase

### Phase 1: Design (Gemini 2.5 Pro)

**Input:**
- `instruction.md` (current RSS fetcher spec)
- `fetch_news.py` (existing implementation)
- `feedly-*.opml` (feed list)
- This document (`agent_roles.md`)

**Output:** `design.md` containing:
- System architecture diagram (text-based)
- Component breakdown and interfaces
- Data flow: OPML → RSS fetch → dedup → HTML → Gmail
- Local LLM integration spec (Ollama model, prompt design for dedup)
- Gmail API or SMTP configuration
- Scheduling mechanism (cron vs systemd timer vs Python scheduler)
- Configuration management (.env or config file)
- Error handling and retry strategy
- Logging strategy

### Phase 2: Design Review (Claude Code)

**Input:** `design.md` from Phase 1

**Output:** `design_review.md` containing:
- List of contradictions or ambiguities
- Missing edge cases and failure modes
- Dependency risks (external services, LLM availability)
- Implementation feasibility concerns
- Questions requiring human decision
- Approved / Needs Revision verdict

### Phase 3: Implementation (Codex)

**Input:**
- Approved `design.md`
- `design_review.md` (addressed concerns)
- `fetch_news.py` (base to extend)

**Output:**
- Source code for all components
- `requirements.txt`
- Configuration template (`.env.example`)
- Brief implementation notes

### Phase 4: Test Design (Claude Code)

**Input:**
- `design.md`
- Implemented source code from Phase 3

**Output:** `test_plan.md` containing:
- Test categories (unit, integration, E2E)
- Test cases with IDs, descriptions, expected results
- Boundary conditions (empty feeds, LLM timeout, Gmail auth failure, etc.)
- Acceptance criteria traceability matrix
- Priority ranking (critical / high / medium / low)

### Phase 5: Test Implementation + Execution (Codex)

**Input:**
- `test_plan.md` from Phase 4
- Source code from Phase 3

**Output:**
- Test code files
- `test_results.md` with execution output (pass/fail per test case)
- Coverage report if applicable

### Phase 6: Test Result Review (Gemini 2.5 Pro)

**Input:**
- `test_plan.md`
- `test_results.md`
- `design.md`
- Source code

**Output:** `test_review.md` containing:
- Pass/Fail validity assessment
- Coverage gap analysis
- Recommendations for additional tests
- Final verdict: Release-ready / Needs fixes

## Existing Assets

| File | Description |
|---|---|
| `fetch_news.py` | Working RSS fetcher (OPML parse + feedparser + sort + output) |
| `instruction.md` | Original spec for RSS fetcher |
| `feedly-ca53bc95-9ca8-4579-a877-542cfb958671-2026-02-17.opml` | 114 RSS feeds across 3 categories |
| `news_list.txt` | Sample output from current fetcher (100 articles) |

## Environment

- Python 3.6.15 (current; upgrade to 3.9+ recommended)
- OS: Linux (Ubuntu)
- Local LLM: Ollama (model TBD in design phase)
- Email: Gmail (API or SMTP, TBD in design phase)
