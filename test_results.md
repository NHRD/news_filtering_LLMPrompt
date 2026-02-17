# Test Results

## Environment
- Date: 2026-02-17
- Python: 3.6.15
- pytest: 7.0.1
- Command: `pytest tests/ -v --tb=short 2>&1 | tee test_output.txt`

## Dependency Installation Notes
- Executed: `pip install -r requirements.txt`
- Result: Failed due to Python 3.6 incompatibility with `requests>=2.28.0` (and other modern constraints).
- Executed: `pip install pytest pytest-cov` (succeeded).
- Added Python 3.6-compatible runtime packages to run tests: `requests==2.27.1`, `jinja2==3.0.3`, `pyyaml==6.0`, `python-dotenv==0.20.0`, `scikit-learn==0.24.2`, `numpy==1.19.5`.

## Test Case Status (by Test Plan ID)

| ID | Status | Test |
|---|---|---|
| UT-001-1 | Pass | `test_ut_001_1_parse_valid_opml` |
| UT-001-2 | Pass | `test_ut_001_2_skip_feedly_proxy_urls` |
| UT-001-3 | Pass | `test_ut_001_3_handle_duplicate_feed_urls` |
| UT-001-4 | Pass | `test_ut_001_4_handle_empty_opml` |
| UT-001-5 | Pass | `test_ut_001_5_handle_malformed_opml` |
| UT-002-1 | Pass | `test_ut_002_1_fetch_valid_rss_feed` |
| UT-002-2 | Pass | `test_ut_002_2_handle_feed_timeout` |
| UT-002-3 | Pass | `test_ut_002_3_handle_malformed_feed` |
| UT-002-4 | Pass | `test_ut_002_4_extract_article_metadata` |
| UT-002-5 | Fail | `test_ut_002_5_handle_missing_date` |
| UT-003-1 | Pass | `test_ut_003_1_filter_recent_articles` |
| UT-003-2 | Pass | `test_ut_003_2_filter_old_articles` |
| UT-003-3 | Pass | `test_ut_003_3_handle_timezone_aware_dates` |
| UT-003-4 | Fail | `test_ut_003_4_handle_timezone_naive_dates` |
| UT-003-5 | Fail | `test_ut_003_5_handle_none_date` |
| UT-003-6 | Pass | `test_ut_003_6_use_last_run_for_recovery` |
| UT-004-1 | Pass | `test_ut_004_1_remove_duplicate_urls` |
| UT-004-2 | Pass | `test_ut_004_2_keep_most_recent` |
| UT-004-3 | Pass | `test_ut_004_3_handle_all_unique` |
| UT-005-1 | Fail | `test_ut_005_1_cluster_similar_titles` |
| UT-005-2 | Pass | `test_ut_005_2_keep_different_titles` |
| UT-005-3 | Fail | `test_ut_005_3_prefer_preferred_source` |
| UT-005-4 | Fail | `test_ut_005_4_prefer_recent_if_no_preferred` |
| UT-005-5 | Pass | `test_ut_005_5_handle_ollama_timeout` |
| UT-005-6 | Pass | `test_ut_005_6_handle_empty_list` |
| UT-006-1 | Pass | `test_ut_006_1_generate_valid_html` |
| UT-006-2 | Pass | `test_ut_006_2_group_by_category` |
| UT-006-3 | Pass | `test_ut_006_3_sort_by_date` |
| UT-006-4 | Pass | `test_ut_006_4_escape_html_in_title` |
| UT-006-5 | Fail | `test_ut_006_5_handle_empty_list` |
| UT-006-6 | Fail | `test_ut_006_6_respect_max_articles` |
| UT-007-1 | Pass | `test_ut_007_1_send_email_mocked` |
| UT-007-2 | Pass | `test_ut_007_2_handle_auth_failure` |
| UT-007-3 | Pass | `test_ut_007_3_handle_network_error_with_retries` |
| UT-007-4 | Pass | `test_ut_007_4_multiple_recipients` |
| UT-008-1 | Pass | `test_ut_008_1_load_config_yaml` |
| UT-008-2 | Pass | `test_ut_008_2_expand_env_vars` |
| UT-008-3 | Pass | `test_ut_008_3_handle_missing_file` |
| UT-008-4 | Pass | `test_ut_008_4_handle_missing_env_var` |
| IT-001-1 | Pass | `test_it_001_1_fetch_real_like_and_filter_by_time` |
| IT-001-2 | Fail | `test_it_001_2_state_persistence_across_runs` |
| IT-002-1 | Pass | `test_it_002_1_filter_then_deduplicate` |
| IT-002-2 | Pass | `test_it_002_2_dedup_with_ollama_running` |
| IT-003-1 | Pass | `test_it_003_1_build_html_from_deduped_articles` |
| IT-004-1 | Fail | `test_it_004_1_build_and_send_mocked_smtp` |
| E2E-001-1 | Pass | `test_e2e_001_1_run_pipeline_dry_run` |
| E2E-001-2 | Pass | `test_e2e_001_2_run_pipeline_full_with_mocked_email` |
| E2E-001-3 | Pass | `test_e2e_001_3_run_with_ollama_down_fallback` |
| E2E-002-1 | Pass | `test_e2e_002_1_dry_run_flag` |
| E2E-002-2 | Pass | `test_e2e_002_2_fetch_only_flag` |
| E2E-002-3 | Pass | `test_e2e_002_3_force_flag` |

## Failed Test Details

1. `UT-005-1` / `UT-005-3` / `UT-005-4`
- Error: Stage2 clustering falls back with warning: `__init__() got an unexpected keyword argument 'metric'`
- Observed in: `src/deduplicator.py` AgglomerativeClustering init on sklearn 0.24.2.
- Impact: Similarity dedup stage disabled; URL-stage fallback only.

2. `UT-006-5`
- Expected: empty input renders "No articles" message.
- Actual: HTML has header/footer only, no explicit no-articles message.

3. `UT-006-6`
- Expected: HTML builder limits to 200 articles.
- Actual: 300 articles rendered. Limiting currently handled in `src/main.py`, not `src/html_builder.py`.

4. `IT-001-2`
- Error: `datetime.fromisoformat` unavailable in Python 3.6, so state load fails and returns `None`.
- Log: `[Time Filter] Failed to load state file: type object 'datetime.datetime' has no attribute 'fromisoformat'`

5. `IT-004-1`
- Error: Integration test attempted real SMTP auth.
- Cause: test monkeypatched `src.email_sender.send_email` but called imported local `send_email` symbol, so patch was ineffective.

6. `UT-002-5`
- Expected (plan): missing date -> keep article with `published=None`.
- Actual: implementation drops entries without valid date.

7. `UT-003-4`
- Error: naive datetime comparison causes `TypeError` between naive and aware datetimes.

8. `UT-003-5`
- Error: `None` published date comparison causes `TypeError`.

## Overall Summary
- Total tests: 51
- Passed: 41
- Failed: 10
- Pass rate: 80.4%
- Artifacts:
  - Test output: `test_output.txt`
  - Test report: `test_results.md`
  - Tests: `tests/`
