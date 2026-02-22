# Test Results - 2026-02-22

## Summary

| Metric | Value |
|---|---|
| Total Tests | 54 |
| Passed | 54 |
| Failed | 0 |
| Pass Rate | 100% |
| Coverage | 90% |
| Python Version | 3.12.12 |
| Test Framework | pytest 9.0.2 |

---

## Test Results by Module

### test_config.py (5 tests)

| Test ID | Test Name | Status |
|---|---|---|
| UT-008-1 | test_ut_008_1_load_config_yaml | PASS |
| UT-008-2 | test_ut_008_2_expand_env_vars | PASS |
| UT-008-3 | test_ut_008_3_handle_missing_file | PASS |
| UT-008-4 | test_ut_008_4_handle_missing_env_var | PASS |
| UT-008-5 | test_ut_008_5_on_dedup_failure_default | PASS |

### test_deduplicator.py (11 tests)

| Test ID | Test Name | Status |
|---|---|---|
| UT-004-1 | test_ut_004_1_remove_duplicate_urls | PASS |
| UT-004-2 | test_ut_004_2_keep_most_recent | PASS |
| UT-004-3 | test_ut_004_3_handle_all_unique | PASS |
| UT-005-1 | test_ut_005_1_cluster_similar_titles | PASS |
| UT-005-2 | test_ut_005_2_keep_different_titles | PASS |
| UT-005-3 | test_ut_005_3_prefer_preferred_source | PASS |
| UT-005-4 | test_ut_005_4_prefer_recent_if_no_preferred | PASS |
| UT-005-5 | test_ut_005_5_handle_ollama_timeout | PASS |
| UT-005-6 | test_ut_005_6_handle_empty_list | PASS |
| UT-005-7 | test_ut_005_7_on_dedup_failure_fail | PASS |
| UT-005-8 | test_ut_005_8_model_not_found | PASS |

### test_email_sender.py (4 tests)

| Test ID | Test Name | Status |
|---|---|---|
| UT-007-1 | test_ut_007_1_send_email_mocked | PASS |
| UT-007-2 | test_ut_007_2_handle_auth_failure | PASS |
| UT-007-3 | test_ut_007_3_handle_network_error_with_retries | PASS |
| UT-007-4 | test_ut_007_4_multiple_recipients | PASS |

### test_html_builder.py (6 tests)

| Test ID | Test Name | Status |
|---|---|---|
| UT-006-1 | test_ut_006_1_generate_valid_html | PASS |
| UT-006-2 | test_ut_006_2_group_by_category | PASS |
| UT-006-3 | test_ut_006_3_sort_by_date | PASS |
| UT-006-4 | test_ut_006_4_escape_html_in_title | PASS |
| UT-006-5 | test_ut_006_5_handle_empty_list | PASS |
| UT-006-6 | test_ut_006_6_respect_max_articles | PASS |

### test_integration.py (12 tests)

| Test ID | Test Name | Status |
|---|---|---|
| IT-001-1 | test_it_001_1_fetch_real_like_and_filter_by_time | PASS |
| IT-001-2 | test_it_001_2_state_persistence_across_runs | PASS |
| IT-002-1 | test_it_002_1_filter_then_deduplicate | PASS |
| IT-002-2 | test_it_002_2_dedup_with_ollama_running | PASS |
| IT-003-1 | test_it_003_1_build_html_from_deduped_articles | PASS |
| IT-004-1 | test_it_004_1_build_and_send_mocked_smtp | PASS |
| E2E-001-1 | test_e2e_001_1_run_pipeline_dry_run | PASS |
| E2E-001-2 | test_e2e_001_2_run_pipeline_full_with_mocked_email | PASS |
| E2E-001-3 | test_e2e_001_3_run_with_ollama_down_fallback | PASS |
| E2E-002-1 | test_e2e_002_1_dry_run_flag | PASS |
| E2E-002-2 | test_e2e_002_2_fetch_only_flag | PASS |
| E2E-002-3 | test_e2e_002_3_force_flag | PASS |

### test_rss_fetcher.py (10 tests)

| Test ID | Test Name | Status |
|---|---|---|
| UT-001-1 | test_ut_001_1_parse_valid_opml | PASS |
| UT-001-2 | test_ut_001_2_skip_feedly_proxy_urls | PASS |
| UT-001-3 | test_ut_001_3_handle_duplicate_feed_urls | PASS |
| UT-001-4 | test_ut_001_4_handle_empty_opml | PASS |
| UT-001-5 | test_ut_001_5_handle_malformed_opml | PASS |
| UT-002-1 | test_ut_002_1_fetch_valid_rss_feed | PASS |
| UT-002-2 | test_ut_002_2_handle_feed_timeout | PASS |
| UT-002-3 | test_ut_002_3_handle_malformed_feed | PASS |
| UT-002-4 | test_ut_002_4_extract_article_metadata | PASS |
| UT-002-5 | test_ut_002_5_handle_missing_date | PASS |

### test_time_filter.py (6 tests)

| Test ID | Test Name | Status |
|---|---|---|
| UT-003-1 | test_ut_003_1_filter_recent_articles | PASS |
| UT-003-2 | test_ut_003_2_filter_old_articles | PASS |
| UT-003-3 | test_ut_003_3_handle_timezone_aware_dates | PASS |
| UT-003-4 | test_ut_003_4_handle_timezone_naive_dates | PASS |
| UT-003-5 | test_ut_003_5_handle_none_date | PASS |
| UT-003-6 | test_ut_003_6_use_last_run_for_recovery | PASS |

---

## Coverage Report

| Module | Stmts | Miss | Cover | Missing Lines |
|---|---|---|---|---|
| src/__init__.py | 8 | 0 | 100% | - |
| src/config.py | 68 | 0 | 100% | - |
| src/deduplicator.py | 70 | 9 | 87% | 31-38, 103 |
| src/email_sender.py | 33 | 1 | 97% | 49 |
| src/html_builder.py | 31 | 0 | 100% | - |
| src/main.py | 73 | 18 | 75% | 36-38, 51-56, 61, 79-80, 101, 131-134, 138 |
| src/rss_fetcher.py | 83 | 6 | 93% | 61, 74-75, 84-85, 114 |
| src/time_filter.py | 52 | 6 | 88% | 28, 31-32, 34-36 |
| **TOTAL** | **418** | **40** | **90%** | |

### Coverage Notes

- **src/config.py (100%)** and **src/html_builder.py (100%)**: Fully covered
- **src/main.py (75%)**: CLI argument parsing, `main()` entry point, logging setup are not covered (tested indirectly via `run_pipeline`)
- **src/deduplicator.py (87%)**: Real Ollama API call path (`_get_embedding` HTTP logic) not covered by unit tests
- **src/rss_fetcher.py (93%)**: Category inheritance edge case, some date parsing branches
- **src/time_filter.py (88%)**: State file loading edge cases

---

## Changes from Previous Session (2026-02-17)

### Issues Fixed

| Issue | Previous | Current | Status |
|---|---|---|---|
| Python version | 3.6.15 | 3.12.12 | Fixed |
| Timezone naive/aware comparison | TypeError | Handled (assume UTC + log) | Fixed |
| None date article handling | Test/impl mismatch | Aligned (exclude + log) | Fixed |
| Empty article list HTML | No message | "No articles found" message | Fixed |
| Mock patch in test_it_004_1 | Patching wrong reference | Patching module attribute | Fixed |
| scikit-learn API | Incompatible (Python 3.6) | Compatible (Python 3.12) | Fixed |
| datetime.fromisoformat | Not available (Python 3.6) | Available (Python 3.12) | Fixed |

### New Features Added (from architecture_review.md)

| Feature | Description |
|---|---|
| on_dedup_failure config | "send_anyway" (default) or "fail" mode for Ollama failure |
| Model not found handling | CRITICAL log + SystemExit(1) on HTTP 404 |
| RotatingFileHandler | 10MB max, 5 backups for log rotation |
| max_articles in HTML builder | Truncation parameter at builder level |

### Test Growth

| Metric | Previous | Current | Change |
|---|---|---|---|
| Total Tests | 51 | 54 | +3 |
| Passed | 41 | 54 | +13 |
| Failed | 10 | 0 | -10 |
| Pass Rate | 80.4% | 100% | +19.6% |
| Coverage | N/A | 90% | New |
