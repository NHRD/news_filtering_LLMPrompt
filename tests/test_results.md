# Test Results - 2026-03-12 (v2.0)

---

## v2.0 Test Report (Raw Data) - Rev.3

**実施日:** 2026-03-12
**実行コマンド:** `venv/bin/python -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing`
**実行環境:** Python 3.12.12, pytest-9.0.2, Linux 6.8.0

---

### 実行結果: 93 passed, 0 failed, 実行時間 57.64s

#### 全テスト実行ログ（省略なし）

```
tests/test_boundary.py::test_bc_001_empty_feed_pipeline_completes PASSED
tests/test_boundary.py::test_bc_005_mixed_timezone_articles_normalized_to_utc PASSED
tests/test_config.py::test_ut_008_1_load_config_yaml PASSED
tests/test_config.py::test_ut_008_2_expand_env_vars PASSED
tests/test_config.py::test_ut_008_3_handle_missing_file PASSED
tests/test_config.py::test_ut_008_4_handle_missing_env_var PASSED
tests/test_config.py::test_ut_008_5_preferred_sources_loading PASSED
tests/test_deduplicator.py::test_ut_004_1_remove_duplicate_urls PASSED
tests/test_deduplicator.py::test_ut_004_2_keep_most_recent PASSED
tests/test_deduplicator.py::test_ut_004_3_handle_all_unique PASSED
tests/test_deduplicator.py::test_ut_005_1_cluster_similar_titles PASSED
tests/test_deduplicator.py::test_ut_005_2_keep_different_titles PASSED
tests/test_deduplicator.py::test_ut_005_3_prefer_preferred_source PASSED
tests/test_deduplicator.py::test_ut_005_4_prefer_recent_if_no_preferred PASSED
tests/test_deduplicator.py::test_ut_005_5_handle_gemini_timeout PASSED
tests/test_deduplicator.py::test_ut_005_6_handle_empty_list PASSED
tests/test_deduplicator.py::test_ut_005_7_on_dedup_failure_fail PASSED
tests/test_deduplicator.py::test_ut_005_8_on_dedup_failure_send_anyway PASSED
tests/test_email_sender.py::test_ut_007_1_send_email_mocked PASSED
tests/test_email_sender.py::test_ut_007_2_handle_auth_failure PASSED
tests/test_email_sender.py::test_ut_007_3_handle_network_error_with_retries PASSED
tests/test_email_sender.py::test_ut_007_4_multiple_recipients PASSED
tests/test_html_builder.py::test_ut_006_1_generate_valid_html PASSED
tests/test_html_builder.py::test_ut_006_2_group_by_category PASSED
tests/test_html_builder.py::test_ut_006_3_sort_by_date PASSED
tests/test_html_builder.py::test_ut_006_4_escape_html_in_title PASSED
tests/test_html_builder.py::test_ut_006_5_handle_empty_list PASSED
tests/test_html_builder.py::test_ut_006_6_truncation_message_display PASSED
tests/test_html_builder.py::test_ut_006_7_no_column_rendered PASSED
tests/test_html_builder.py::test_ut_006_8_title_ja_displayed PASSED
tests/test_html_builder.py::test_ut_006_9_title_ja_fallback_to_title PASSED
tests/test_html_builder.py::test_ut_006_10_group_articles_no_resorting PASSED
tests/test_html_builder.py::test_ut_006_11_numbered_articles_nos_in_html PASSED
tests/test_index_writer.py::test_ut_011_1_write_am_session PASSED
tests/test_index_writer.py::test_ut_011_2_write_pm_session PASSED
tests/test_index_writer.py::test_ut_011_3_json_schema_all_fields PASSED
tests/test_index_writer.py::test_ut_011_4_fifo_max_files PASSED
tests/test_index_writer.py::test_ut_011_5_fifo_am_before_pm PASSED
tests/test_index_writer.py::test_ut_011_6_auto_create_directory PASSED
tests/test_index_writer.py::test_ut_011_7_save_index_false_skips_write PASSED
tests/test_index_writer.py::test_ut_011_8_io_error_does_not_raise PASSED
tests/test_index_writer.py::test_ut_011_9_article_count_correct PASSED
tests/test_integration.py::test_it_001_1_fetch_real_like_and_filter_by_time PASSED
tests/test_integration.py::test_it_001_2_state_persistence_across_runs PASSED
tests/test_integration.py::test_it_002_1_filter_then_deduplicate PASSED
tests/test_integration.py::test_it_002_2_dedup_with_gemini_running PASSED
tests/test_integration.py::test_it_003_1_build_html_from_deduped_articles PASSED
tests/test_integration.py::test_it_004_1_build_and_send_mocked_smtp PASSED
tests/test_integration.py::test_e2e_001_1_run_pipeline_dry_run PASSED
tests/test_integration.py::test_e2e_001_2_run_pipeline_full_with_mocked_email PASSED
tests/test_integration.py::test_e2e_001_3_run_with_gemini_down_fails PASSED
tests/test_integration.py::test_e2e_002_1_dry_run_flag PASSED
tests/test_integration.py::test_e2e_002_2_fetch_only_flag PASSED
tests/test_integration.py::test_e2e_002_3_force_flag PASSED
tests/test_integration.py::test_it_005_1_translator_numbering_html_builder PASSED
tests/test_integration.py::test_it_005_2_translator_numbering_index_writer PASSED
tests/test_integration.py::test_it_005_3_numbering_order_consistent_html_and_json PASSED
tests/test_integration.py::test_e2e_003_1_translation_enabled_full_pipeline PASSED
tests/test_integration.py::test_e2e_003_2_translation_disabled_full_pipeline PASSED
tests/test_integration.py::test_e2e_003_3_save_index_true_full_pipeline PASSED
tests/test_numbering.py::test_ut_010_1_single_category_sequential_from_1 PASSED
tests/test_numbering.py::test_ut_010_2_multiple_categories_alphabetical_order PASSED
tests/test_numbering.py::test_ut_010_3_within_category_published_desc PASSED
tests/test_numbering.py::test_ut_010_4_empty_list PASSED
tests/test_numbering.py::test_ut_010_5_sequential_numbers_no_gap PASSED
tests/test_numbering.py::test_ut_010_6_cross_category_sequential PASSED
tests/test_rss_fetcher.py::test_ut_001_1_parse_valid_opml PASSED
tests/test_rss_fetcher.py::test_ut_001_2_skip_feedly_proxy_urls PASSED
tests/test_rss_fetcher.py::test_ut_001_3_handle_duplicate_feed_urls PASSED
tests/test_rss_fetcher.py::test_ut_001_4_handle_empty_opml PASSED
tests/test_rss_fetcher.py::test_ut_001_5_handle_malformed_opml PASSED
tests/test_rss_fetcher.py::test_ut_002_1_fetch_valid_rss_feed PASSED
tests/test_rss_fetcher.py::test_ut_002_2_handle_feed_timeout PASSED
tests/test_rss_fetcher.py::test_ut_002_3_handle_malformed_feed PASSED
tests/test_rss_fetcher.py::test_ut_002_4_extract_article_metadata PASSED
tests/test_rss_fetcher.py::test_ut_002_5_handle_missing_date PASSED
tests/test_time_filter.py::test_ut_003_1_filter_recent_articles PASSED
tests/test_time_filter.py::test_ut_003_2_filter_old_articles PASSED
tests/test_time_filter.py::test_ut_003_3_handle_timezone_aware_dates PASSED
tests/test_time_filter.py::test_ut_003_4_handle_timezone_naive_dates PASSED
tests/test_time_filter.py::test_ut_003_5_handle_none_date PASSED
tests/test_time_filter.py::test_ut_003_6_use_last_run_for_recovery PASSED
tests/test_translator.py::test_ut_009_1_translate_all_success PASSED
tests/test_translator.py::test_ut_009_2_batch_split PASSED
tests/test_translator.py::test_ut_009_3_individual_line_parse_failure_fallback PASSED
tests/test_translator.py::test_ut_009_4_out_of_range_number_fallback PASSED
tests/test_translator.py::test_ut_009_5_duplicate_number_last_wins PASSED
tests/test_translator.py::test_ut_009_6_all_parse_fail_skip PASSED
tests/test_translator.py::test_ut_009_7_all_parse_fail_fail_mode PASSED
tests/test_translator.py::test_ut_009_8_gemini_cli_error_skip PASSED
tests/test_translator.py::test_ut_009_9_gemini_cli_exception_skip PASSED
tests/test_translator.py::test_ut_009_10_translation_disabled_in_pipeline PASSED
tests/test_translator.py::test_ut_009_11_empty_list PASSED
```

---

### カバレッジレポート（`--cov-report=term-missing` 出力そのまま）

```
Name                  Stmts   Miss  Cover   Missing
---------------------------------------------------
src/__init__.py           9      0   100%
src/config.py            85      0   100%
src/deduplicator.py      74      5    93%   51, 58, 60, 63, 70
src/email_sender.py      33      1    97%   49
src/html_builder.py      50      0   100%
src/index_writer.py      48      7    85%   35-37, 83-86
src/main.py             127     37    71%   44-46, 59-64, 69, 81-93, 128-129, 143-144, 155-157, 194-196, 206, 211-214, 218
src/numbering.py         17      0   100%
src/rss_fetcher.py       83      6    93%   61, 75-76, 85-86, 115
src/time_filter.py       65      8    88%   23, 36, 48, 51-52, 54-56
src/translator.py        61      1    98%   55
---------------------------------------------------
TOTAL                   652     65    90%
```

---

### test_plan.md との対応（計画ID vs 実装済みテスト関数）

#### test_integration.py に存在する全関数（grep結果そのまま）
```
test_it_001_1_fetch_real_like_and_filter_by_time
test_it_001_2_state_persistence_across_runs
test_it_002_1_filter_then_deduplicate
test_it_002_2_dedup_with_gemini_running
test_it_003_1_build_html_from_deduped_articles
test_it_004_1_build_and_send_mocked_smtp
test_e2e_001_1_run_pipeline_dry_run
test_e2e_001_2_run_pipeline_full_with_mocked_email
test_e2e_001_3_run_with_gemini_down_fails
test_e2e_002_1_dry_run_flag
test_e2e_002_2_fetch_only_flag
test_e2e_002_3_force_flag
test_it_005_1_translator_numbering_html_builder
test_it_005_2_translator_numbering_index_writer
test_it_005_3_numbering_order_consistent_html_and_json
test_e2e_003_1_translation_enabled_full_pipeline
test_e2e_003_2_translation_disabled_full_pipeline
test_e2e_003_3_save_index_true_full_pipeline
```

#### test_boundary.py に存在する全関数（grep結果そのまま）
```
test_bc_001_empty_feed_pipeline_completes
test_bc_005_mixed_timezone_articles_normalized_to_utc
```

#### test_plan.md に定義されているが実装されていない関数
```
BC-002: max_articles_per_email 超過（未実装）
BC-003: 全記事が同一 URL（未実装）
BC-004: 全記事が同一タイトル（未実装）
```

---

**実施日:** 2026-03-12
**実施者:** Claude (Sonnet 4.6)
**対象バージョン:** v2.0
**実行環境:** Python 3.12.12, pytest 9.0.2, Linux 6.8.0

### 実行結果サマリー

| 項目 | 結果 |
|---|---|
| **総テスト数** | 93 |
| **PASSED** | **93 (100%)** |
| **FAILED** | 0 |
| **ERROR** | 0 |
| **実行時間** | 57.64s |

### コンポーネント別結果

| コンポーネント | テスト数 | PASS | FAIL |
|---|---|---|---|
| Boundary Conditions (test_boundary.py) | 2 | 2 | 0 |
| Config Loader (test_config.py) | 5 | 5 | 0 |
| Deduplicator (test_deduplicator.py) | 11 | 11 | 0 |
| Email Sender (test_email_sender.py) | 4 | 4 | 0 |
| HTML Builder (test_html_builder.py) | 11 | 11 | 0 |
| Index Writer (test_index_writer.py) | 9 | 9 | 0 |
| Integration / E2E (test_integration.py) | 18 | 18 | 0 |
| Article Numbering (test_numbering.py) | 6 | 6 | 0 |
| RSS Fetcher (test_rss_fetcher.py) | 10 | 10 | 0 |
| Time Filter (test_time_filter.py) | 6 | 6 | 0 |
| Translator (test_translator.py) | 11 | 11 | 0 |
| **合計** | **93** | **93** | **0** |

### アーキテクチャ要件カバレッジ

| アーキテクチャ要件 | カバレッジ |
|---|---|
| 境界条件: 空フィード時パイプライン完走 | ✅ BC-001 |
| 境界条件: タイムゾーン混在記事のUTC正規化 | ✅ BC-005 |
| Translator: 正常翻訳 | ✅ UT-009-1 |
| Translator: バッチ処理 | ✅ UT-009-2 |
| Translator: 全エラーハンドリング | ✅ UT-009-3〜9 |
| Translator: enabled=False スキップ | ✅ UT-009-10 |
| Article Numbering: カテゴリ順・通し番号 | ✅ UT-010-1〜6 |
| Index Writer: AM/PMセッション判定 | ✅ UT-011-1,2 |
| Index Writer: JSONフォーマット | ✅ UT-011-3,9 |
| Index Writer: FIFO管理 | ✅ UT-011-4,5 |
| Index Writer: エラー時継続 | ✅ UT-011-8 |
| HTML Builder: No.列・title_ja | ✅ UT-006-7,8,9 |
| HTML Builder: 再ソート禁止 | ✅ UT-006-10 |
| HTML/JSON番号一致 | ✅ IT-005-3 |
| E2E: translation on/off | ✅ E2E-003-1,2 |
| E2E: save_index=True | ✅ E2E-003-3 |

### 未カバー項目（次バージョン推奨）

| 項目 | 優先度 |
|---|---|
| メール件名のAM/PM含有検証・JST日付フォーマット検証 | Medium（E2E-004-1〜3 として v2.1 に追加済み） |
| TranslationConfig/IndexConfigのデフォルト値テスト | Medium |
| truncationがnumbering前に行われる順序検証 | Medium |

### テスト増加サマリー (v1.0→v2.0)

| 指標 | v1.0 (2026-02-22) | v2.0 (2026-03-12) | 増分 |
|---|---|---|---|
| 総テスト数 | 54 | 93 | +39 |
| PASS数 | 54 | 93 | +39 |
| FAIL数 | 0 | 0 | 0 |

---

# Appendix: 過去のテスト結果履歴

---

## Test Results - 2026-02-22 (v1.0)

### Summary

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
