# Test Results - 2026-03-01

## Summary

| Metric | Value |
|---|---|
| Total Tests | 73 |
| Passed | 73 |
| Failed | 0 |
| Pass Rate | 100% |
| Coverage | 86% |
| Python Version | 3.12.12 |
| Test Framework | pytest 9.0.2 |

---

## Test Results by Module

### test_config.py (7 tests)

| Test ID | Test Name | Status |
|---|---|---|
| UT-008-1 | test_ut_008_1_load_config_yaml | PASS |
| UT-008-2 | test_ut_008_2_expand_env_vars | PASS |
| UT-008-3 | test_ut_008_3_handle_missing_file | PASS |
| UT-008-4 | test_ut_008_4_handle_missing_env_var | PASS |
| UT-008-5 | test_ut_008_5_preferred_sources_loading | PASS |
| UT-008-6 | test_ut_008_6_parse_mailing_lists | PASS |
| UT-008-7 | test_ut_008_7_copy_imap_credentials_from_email | PASS |

### test_deduplicator.py (12 tests)

| Test ID | Test Name | Status |
|---|---|---|
| UT-004-1 | test_ut_004_1_remove_duplicate_urls | PASS |
| UT-004-2 | test_ut_004_2_keep_most_recent | PASS |
| UT-004-3 | test_ut_004_3_keep_empty_links | PASS |
| UT-004-4 | test_ut_004_4_handle_all_unique | PASS |
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
| UT-006-6 | test_ut_006_6_truncation_message_display | PASS |

### test_integration.py (18 tests)

| Test ID | Test Name | Status |
|---|---|---|
| IT-001-1 | test_it_001_1_fetch_real_like_and_filter_by_time | PASS |
| IT-001-2 | test_it_001_2_state_persistence_across_runs | PASS |
| IT-002-1 | test_it_002_1_filter_then_deduplicate | PASS |
| IT-002-2 | test_it_002_2_dedup_with_ollama_running | PASS |
| IT-003-1 | test_it_003_1_build_html_from_deduped_articles | PASS |
| IT-004-1 | test_it_004_1_build_and_send_mocked_smtp | PASS |
| IT-005-1 | test_it_005_1_merge_rss_and_mail_in_pipeline | PASS |
| IT-005-2 | test_it_005_2_time_filter_applies_to_rss_and_mail | PASS |
| IT-005-3 | test_it_005_3_dedup_exact_url_between_rss_and_mail | PASS |
| IT-005-4 | test_it_005_4_dedup_title_similarity_between_rss_and_mail | PASS |
| E2E-001-1 | test_e2e_001_1_run_pipeline_dry_run | PASS |
| E2E-001-2 | test_e2e_001_2_run_pipeline_full_with_mocked_email | PASS |
| E2E-001-3 | test_e2e_001_3_run_with_ollama_down_fails | PASS |
| E2E-001-4 | test_e2e_001_4_run_pipeline_with_rss_and_mail | PASS |
| E2E-001-5 | test_e2e_001_5_imap_failure_graceful_degradation | PASS |
| E2E-002-1 | test_e2e_002_1_dry_run_flag | PASS |
| E2E-002-2 | test_e2e_002_2_fetch_only_flag | PASS |
| E2E-002-3 | test_e2e_002_3_force_flag | PASS |

### test_mail_fetcher.py (10 tests)

| Test ID | Test Name | Status |
|---|---|---|
| UT-009-1 | test_ut_009_1_imap_connect_and_login | PASS |
| UT-009-2 | test_ut_009_2_search_by_from_uses_since_and_from | PASS |
| UT-009-3 | test_ut_009_3_search_by_label_uses_select_label | PASS |
| UT-009-4 | test_ut_009_4_decode_rfc2047_subject | PASS |
| UT-009-5 | test_ut_009_5_date_header_to_utc | PASS |
| UT-009-6 | test_ut_009_6_extract_url_from_text_plain | PASS |
| UT-009-7 | test_ut_009_7_extract_url_from_text_html | PASS |
| UT-009-8 | test_ut_009_8_no_url_results_in_empty_link | PASS |
| UT-009-9 | test_ut_009_9_connection_failure_returns_empty | PASS |
| UT-009-10 | test_ut_009_10_disabled_returns_empty_without_imap | PASS |

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
| src/config.py | 92 | 0 | 100% | - |
| src/html_builder.py | 34 | 0 | 100% | - |
| src/email_sender.py | 33 | 1 | 97% | 49 |
| src/rss_fetcher.py | 83 | 6 | 93% | 61, 75-76, 85-86, 115 |
| src/time_filter.py | 65 | 8 | 88% | 23, 36, 48, 51-52, 54-56 |
| src/deduplicator.py | 76 | 13 | 83% | 41-48, 82-83, 132-134 |
| src/mail_fetcher.py | 148 | 30 | 80% | 57, 65-66, 88, 92-93, 120, 124-125, 142-143, 156, 163, 166, 173-174, 186-190, 206, 217-223, 236-237 |
| src/main.py | 116 | 36 | 69% | 42-44, 57-62, 67, 79-91, 124-125, 145-146, 157-158, 189-191, 201, 206-209, 213 |
| **TOTAL** | **655** | **94** | **86%** | |

### Coverage Notes

- **src/config.py (100%)**, **src/__init__.py (100%)**, **src/html_builder.py (100%)**: 完全カバー
- **src/mail_fetcher.py (80%)**: 実 IMAP 接続後の低頻度エラーパス（認証後のネットワーク切断、個別メールのデコード例外等）が未カバー。モックテストで主要フローは検証済み
- **src/main.py (69%)**: ロギングセットアップ、CLI 引数パース、`main()` エントリーポイント、シャットダウン処理が未カバー。`run_pipeline` は統合テストで検証済み
- **src/deduplicator.py (83%)**: 実 Ollama API 呼び出しの HTTP エラーパス
- **src/rss_fetcher.py (93%)**: カテゴリ継承エッジケース、一部の日付パース分岐

---

## Changes from Previous Session (2026-02-22)

### New Features Added (Gmail Mailing List Integration)

| Component | Change |
|---|---|
| `src/mail_fetcher.py` | 新規作成: Gmail IMAP 経由のメーリングリスト取得 (stdlib のみ使用) |
| `src/config.py` | `MailingListEntry`, `MailFetchConfig` 追加; `AppConfig` に `mail_fetch` フィールド追加 |
| `src/main.py` | `compute_cutoff` 先行計算 + `fetch_mail_articles` 呼び出し + RSS と結合 |
| `src/deduplicator.py` | `_dedup_by_exact_url`: `link=""` を重複排除対象外に変更 |
| `config.yaml` | `mailing_lists` セクション追加 (デフォルト `enabled: false`) |

### Requirement Coverage

| Architecture Requirement (architecture_add_mail.md) | Test IDs |
|---|---|
| Gmail IMAP 経由のメール取得 | UT-009-1 〜 UT-009-3, E2E-001-4 |
| `match_by: from` / `label` 対応 | UT-009-2, UT-009-3 |
| RFC 2047 Subject デコード | UT-009-4 |
| 本文からの URL 抽出 (plain/html) | UT-009-6, UT-009-7 |
| `link=""` 時の重複排除回避 | UT-004-3 |
| `mailing_lists` 設定パース | UT-008-6, UT-008-7 |
| RSS と Mail 記事の統合 | IT-005-1, IT-005-2 |
| RSS と Mail の重複排除 | IT-005-3, IT-005-4 |
| IMAP 失敗時のグレースフルデグレード | UT-009-9, E2E-001-5 |

### Test Growth

| Metric | Previous (2026-02-22) | Current (2026-03-01) | Change |
|---|---|---|---|
| Total Tests | 54 | 73 | +19 |
| Passed | 54 | 73 | +19 |
| Failed | 0 | 0 | 0 |
| Pass Rate | 100% | 100% | - |
| Coverage | 90% | 86% | -4% (新規 mail_fetcher.py の未カバーパスによる) |
