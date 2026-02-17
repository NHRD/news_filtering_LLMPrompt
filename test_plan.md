# Test Plan: RSS News Filtering System

## Overview

This document defines the test plan for the RSS News Filtering System based on `architecture.md`.

---

## Test Categories

| Category | Purpose | Tools |
|----------|---------|-------|
| Unit Tests | Test individual components in isolation | pytest, unittest.mock |
| Integration Tests | Test component interactions | pytest |
| E2E Tests | Test full pipeline execution | pytest, subprocess |

---

## Unit Tests

### UT-001: RSS Fetcher - OPML Parsing

**Component:** `src/rss_fetcher.py`

| Test ID | Description | Input | Expected Output | Priority |
|---------|-------------|-------|-----------------|----------|
| UT-001-1 | Parse valid OPML file | `feedly_rss.opml` | List of feed URLs | Critical |
| UT-001-2 | Skip Feedly proxy URLs | OPML with `feedly.com/web/...` | URL not in result | Critical |
| UT-001-3 | Handle duplicate feed URLs | OPML with same URL twice | Deduplicated list | High |
| UT-001-4 | Handle empty OPML | Empty OPML file | Empty list, no error | Medium |
| UT-001-5 | Handle malformed OPML | Invalid XML | Raise exception with message | Medium |

### UT-002: RSS Fetcher - Feed Fetching

| Test ID | Description | Input | Expected Output | Priority |
|---------|-------------|-------|-----------------|----------|
| UT-002-1 | Fetch valid RSS feed | Working RSS URL | List of articles | Critical |
| UT-002-2 | Handle feed timeout | Slow/unavailable URL | Empty list, log warning | High |
| UT-002-3 | Handle malformed feed | Invalid RSS XML | Empty list, log warning | High |
| UT-002-4 | Extract article metadata | Valid RSS entry | Article with title, link, date, source | Critical |
| UT-002-5 | Handle missing date | Entry without published | Article with None date | Medium |

### UT-003: Time Filter

**Component:** `src/time_filter.py`

| Test ID | Description | Input | Expected Output | Priority |
|---------|-------------|-------|-----------------|----------|
| UT-003-1 | Filter recent articles | Articles from last 6h | All included | Critical |
| UT-003-2 | Filter old articles | Articles from 24h ago | All excluded | Critical |
| UT-003-3 | Handle timezone-aware dates | UTC dates | Correct filtering | High |
| UT-003-4 | Handle timezone-naive dates | Naive datetime | Assume UTC, log warning | High |
| UT-003-5 | Handle None date | Article with None date | Exclude, log warning | Medium |
| UT-003-6 | Use last_run for recovery | last_run.json exists | Use max(last_run, now-12h) | High |

### UT-004: Deduplicator - Stage 1 (URL)

**Component:** `src/deduplicator.py`

| Test ID | Description | Input | Expected Output | Priority |
|---------|-------------|-------|-----------------|----------|
| UT-004-1 | Remove duplicate URLs | 3 articles, 2 same URL | 2 unique articles | Critical |
| UT-004-2 | Keep most recent | Same URL, different dates | Article with later date | Critical |
| UT-004-3 | Handle all unique | All different URLs | All articles kept | High |

### UT-005: Deduplicator - Stage 2 (Similarity)

| Test ID | Description | Input | Expected Output | Priority |
|---------|-------------|-------|-----------------|----------|
| UT-005-1 | Cluster similar titles | "Apple releases iOS 18" x2 | 1 article | Critical |
| UT-005-2 | Keep different titles | Unrelated titles | All kept | Critical |
| UT-005-3 | Prefer preferred source | Cluster with Reuters | Reuters article selected | High |
| UT-005-4 | Prefer recent if no pref | Cluster, no pref source | Most recent selected | High |
| UT-005-5 | Handle Ollama timeout | Ollama unavailable | Skip dedup, return all | High |
| UT-005-6 | Handle empty list | No articles | Empty list | Medium |

### UT-006: HTML Builder

**Component:** `src/html_builder.py`

| Test ID | Description | Input | Expected Output | Priority |
|---------|-------------|-------|-----------------|----------|
| UT-006-1 | Generate valid HTML | List of articles | Valid HTML string | Critical |
| UT-006-2 | Group by category | Articles with categories | HTML with category sections | High |
| UT-006-3 | Sort by date | Articles with dates | Newest first in each category | High |
| UT-006-4 | Escape HTML in title | Title with `<script>` | Escaped output | Critical |
| UT-006-5 | Handle empty list | No articles | HTML with "No articles" message | Medium |
| UT-006-6 | Respect max_articles | 300 articles, max=200 | 200 articles in HTML | High |

### UT-007: Email Sender

**Component:** `src/email_sender.py`

| Test ID | Description | Input | Expected Output | Priority |
|---------|-------------|-------|-----------------|----------|
| UT-007-1 | Send email (mocked) | Valid config, HTML | SMTP called correctly | Critical |
| UT-007-2 | Handle auth failure | Invalid credentials | Raise exception | High |
| UT-007-3 | Handle network error | SMTP timeout | Retry 3 times, then fail | High |
| UT-007-4 | Multiple recipients | 2 email addresses | Both in To header | High |

### UT-008: Config Loader

**Component:** `src/config.py`

| Test ID | Description | Input | Expected Output | Priority |
|---------|-------------|-------|-----------------|----------|
| UT-008-1 | Load config.yaml | Valid YAML | Config object | Critical |
| UT-008-2 | Expand env vars | `${GMAIL_ADDRESS}` | Actual value | Critical |
| UT-008-3 | Handle missing file | No config.yaml | Raise exception | High |
| UT-008-4 | Handle missing env var | `${UNDEFINED}` | Raise exception or default | Medium |

---

## Integration Tests

### IT-001: RSS Fetch + Time Filter

| Test ID | Description | Expected Result | Priority |
|---------|-------------|-----------------|----------|
| IT-001-1 | Fetch real feeds, filter by time | Recent articles only | High |
| IT-001-2 | State persistence across runs | last_run.json updated | High |

### IT-002: Time Filter + Deduplicator

| Test ID | Description | Expected Result | Priority |
|---------|-------------|-----------------|----------|
| IT-002-1 | Filter then deduplicate | Reduced article count | High |
| IT-002-2 | Dedup with Ollama running | Embeddings generated | High |

### IT-003: Deduplicator + HTML Builder

| Test ID | Description | Expected Result | Priority |
|---------|-------------|-----------------|----------|
| IT-003-1 | Build HTML from deduped articles | Valid HTML output | High |

### IT-004: HTML Builder + Email Sender

| Test ID | Description | Expected Result | Priority |
|---------|-------------|-----------------|----------|
| IT-004-1 | Build and send (mocked SMTP) | Email sent successfully | High |

---

## E2E Tests

### E2E-001: Full Pipeline

| Test ID | Description | Expected Result | Priority |
|---------|-------------|-----------------|----------|
| E2E-001-1 | Run main.py --dry-run | HTML generated, no email | Critical |
| E2E-001-2 | Run main.py (mocked email) | Full pipeline completes | Critical |
| E2E-001-3 | Run with Ollama down | Fallback, no dedup | High |

### E2E-002: CLI Options

| Test ID | Description | Expected Result | Priority |
|---------|-------------|-----------------|----------|
| E2E-002-1 | --dry-run flag | No email sent | High |
| E2E-002-2 | --fetch-only flag | Only fetch, no dedup/email | Medium |
| E2E-002-3 | --force flag | Ignore schedule, run immediately | Medium |

---

## Boundary Conditions

| Condition | Test | Expected Behavior |
|-----------|------|-------------------|
| 0 articles after filter | Full pipeline | Email with "No new articles" |
| 1000+ articles | Deduplication | Performance acceptable (<60s) |
| 300 articles, max=200 | HTML Builder | Truncate to 200 |
| All feeds timeout | RSS Fetcher | Empty list, log errors |
| Ollama model not found | Deduplicator | Fallback to no dedup |
| Invalid Gmail password | Email Sender | Clear error message |

---

## Test Data

### Mock Articles
```python
MOCK_ARTICLES = [
    Article(title="Apple announces new iPhone", link="https://example.com/1",
            published=datetime.now(UTC), source="TechCrunch", category="Tech news"),
    Article(title="Apple unveils latest iPhone model", link="https://example.com/2",
            published=datetime.now(UTC) - timedelta(hours=1), source="The Verge", category="Tech news"),
    Article(title="Fed raises interest rates", link="https://example.com/3",
            published=datetime.now(UTC) - timedelta(hours=2), source="Reuters", category="Finance"),
]
```

### Mock OPML
```xml
<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.0">
    <body>
        <outline text="Test" title="Test">
            <outline type="rss" text="Test Feed" xmlUrl="https://example.com/feed.xml"/>
        </outline>
    </body>
</opml>
```

---

## Acceptance Criteria Traceability

| Requirement | Test IDs |
|-------------|----------|
| Fetch RSS from OPML | UT-001-*, UT-002-* |
| Filter last 12 hours | UT-003-* |
| Deduplicate with LLM | UT-004-*, UT-005-* |
| Generate HTML email | UT-006-* |
| Send via Gmail | UT-007-* |
| Handle errors gracefully | UT-002-2, UT-003-5, UT-005-5, UT-007-3 |
| Failure recovery | UT-003-6, IT-001-2 |

---

## Test Execution

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific category
pytest tests/test_rss_fetcher.py -v
pytest tests/ -k "integration" -v
pytest tests/ -k "e2e" -v
```

---

## Priority Summary

| Priority | Count | Description |
|----------|-------|-------------|
| Critical | 15 | Core functionality, must pass |
| High | 22 | Important features, should pass |
| Medium | 8 | Edge cases, nice to have |
