# Test Plan - RSS News Filtering System

## Overview

本テスト計画は `architecture.md` および `architecture_review.md` のフィードバックに基づき、RSSニュースフィルタリングシステムの品質保証のために設計された。

---

## Test Categories

| Category | Purpose | Tools |
|---|---|---|
| Unit Tests (UT) | 各コンポーネントを単独でテスト | pytest, unittest.mock |
| Integration Tests (IT) | コンポーネント間の連携をテスト | pytest |
| E2E Tests | パイプライン全体の実行をテスト | pytest |
| Boundary Condition Tests (BC) | 境界条件・異常系をテスト | pytest |

---

## Unit Tests

### UT-001: OPML Parser (`src/rss_fetcher.py::parse_opml`)

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| UT-001-1 | 正常な OPML をパースしフィードリストを返す | Critical | FeedSource のリストが返る |
| UT-001-2 | Feedly プロキシ URL をスキップ | High | feedly.com/web/ で始まる URL が除外 |
| UT-001-3 | 重複フィード URL を排除 | High | 同一 URL は1件のみ |
| UT-001-4 | 空の OPML を処理 | Medium | 空リストを返す |
| UT-001-5 | 不正な OPML でエラー発生 | Medium | Exception が raise される |

### UT-002: RSS Fetcher (`src/rss_fetcher.py::fetch_articles`)

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| UT-002-1 | 正常な RSS フィードを取得 | Critical | Article リストが返る |
| UT-002-2 | フィードタイムアウト時の処理 | High | 空リスト + WARNING ログ |
| UT-002-3 | 不正な日付形式の処理 | High | 該当記事をスキップ + WARNING ログ |
| UT-002-4 | 記事メタデータの正確な抽出 | High | title, link, source, category, published が正しい |
| UT-002-5 | published_date なし記事の処理 | High | 記事を除外 + WARNING ログ |

### UT-003: Time Filter (`src/time_filter.py`)

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| UT-003-1 | 時間ウィンドウ内の記事をフィルタ | Critical | cutoff 以降の記事のみ返る |
| UT-003-2 | 古い記事を除外 | Critical | cutoff より前の記事は含まれない |
| UT-003-3 | タイムゾーン aware な日付の処理 | High | 正しく UTC に変換して比較 |
| UT-003-4 | タイムゾーン naive な日付の処理 | High | UTC として扱い WARNING ログ |
| UT-003-5 | published=None の記事の処理 | High | スキップ + WARNING ログ |
| UT-003-6 | last_run を使った障害復旧 | Medium | max(last_run, now-24h) を cutoff に使用 |

### UT-004: URL Deduplication (`src/deduplicator.py::_dedup_by_exact_url`)

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| UT-004-1 | 重複 URL を削除 | Critical | 同一 URL は1件のみ残る |
| UT-004-2 | 最新の記事を保持 | High | 同一 URL のうち published が最新のものを保持 |
| UT-004-3 | 全てユニークな場合 | Medium | 全記事がそのまま返る |

### UT-005: Title Similarity Clustering (`src/deduplicator.py`)

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| UT-005-1 | 類似タイトルをクラスタリング | Critical | 類似記事が1件に統合 |
| UT-005-2 | 異なるタイトルを別クラスタに | High | 異なる記事は両方保持 |
| UT-005-3 | preferred_sources を優先 | High | preferred source の記事を選択 |
| UT-005-4 | preferred_sources がない場合は最新を選択 | Medium | 最新記事が代表に |
| UT-005-5 | Gemini CLI タイムアウト + on_dedup_failure=fail | Critical | DeduplicationError が raise される |
| UT-005-6 | 空リストの処理 | Low | 空リストを返す |
| UT-005-7 | CalledProcessError + on_dedup_failure=fail | High | DeduplicationError が raise される |
| UT-005-8 | CalledProcessError + on_dedup_failure=send_anyway | High | 全記事返却（パイプライン継続） |

### UT-006: HTML Builder (`src/html_builder.py`)

**更新:** NumberedArticle 対応 (新アーキテクチャ準拠)

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| UT-006-1 | 有効な HTML を生成 | Critical | DOCTYPE, html タグを含む |
| UT-006-2 | カテゴリ別にグループ化 | High | カテゴリ名で分類 |
| UT-006-3 | 日付順にソート | High | 新しい記事が先（numbering.py が確定した順序を維持） |
| UT-006-4 | HTML エスケープ | High | XSS 攻撃を防止 |
| UT-006-5 | 空リスト時のメッセージ | Medium | "No articles" メッセージ表示 |
| UT-006-6 | max_articles 制限 | Medium | 指定件数で切り捨て |
| UT-006-7 | No.列のレンダリング | High | NumberedArticle の no が HTML に出力される |
| UT-006-8 | title_ja の表示 | High | title_ja が HTML に出力される |
| UT-006-9 | title_ja="" 時のフォールバック | High | title_ja が空の場合は title を表示 |
| UT-006-10 | _group_articles() が再ソートしない | Critical | numbering.py 確定順序をカテゴリ内で維持（no の昇順を保持） |
| UT-006-11 | 複数カテゴリをまたぐ通し番号の出力 | High | 全カテゴリにわたり連番が HTML に出力される |

### UT-007: Email Sender (`src/email_sender.py`)

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| UT-007-1 | SMTP 経由でメール送信 | Critical | 正常送信 + True 返却 |
| UT-007-2 | 認証失敗時のエラー | Critical | SMTPAuthenticationError を raise |
| UT-007-3 | ネットワークエラー時のリトライ | High | 3回リトライ + 指数バックオフ |
| UT-007-4 | 複数宛先への送信 | Medium | 全宛先に送信 |

### UT-008: Config Loader (`src/config.py`)

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| UT-008-1 | YAML 設定の読み込み | Critical | AppConfig が返る |
| UT-008-2 | 環境変数の展開 | High | ${VAR} が環境変数値に置換 |
| UT-008-3 | 設定ファイル未存在時のエラー | Medium | FileNotFoundError |
| UT-008-4 | 必須環境変数の欠落 | Medium | ValueError |
| UT-008-5 | preferred_sources の読み込みと on_dedup_failure デフォルト値 | Medium | preferred_sources に設定値が読み込まれ、on_dedup_failure が "send_anyway" |
| UT-008-6 | TranslationConfig の全フィールド読み込み | High | enabled, batch_size, batch_interval_seconds, on_translate_failure が設定値またはデフォルト値で AppConfig に反映される |

### UT-009: Translator (`src/translator.py`) **[NEW]**

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| UT-009-1 | 正常翻訳（全件） | Critical | 全記事の title_ja が翻訳結果で埋まる |
| UT-009-2 | バッチ分割（batch_size 超過時） | High | バッチごとにローカル番号で処理、全件翻訳 |
| UT-009-3 | 個別行パース失敗 → フォールバック | High | 該当記事のみ original title を使用、WARNING ログ |
| UT-009-4 | 範囲外番号 → フォールバック | High | 範囲外行を無視、対応記事は original title |
| UT-009-5 | 重複番号 → 後出し優先 | Medium | 最後に出現した翻訳を採用、WARNING ログ |
| UT-009-6 | 全行パース失敗 + on_translate_failure=skip | Critical | 全記事を original title で継続 |
| UT-009-7 | 全行パース失敗 + on_translate_failure=fail | Critical | TranslationError を raise |
| UT-009-8 | Gemini CLI エラー + on_translate_failure=skip | High | original title にフォールバック、WARNING ログ |
| UT-009-9 | Gemini CLI 未起動/例外 + skip | High | original title にフォールバック |
| UT-009-10 | translation.enabled=False → 翻訳スキップ | High | subprocess 未呼び出し、title_ja="" のまま |
| UT-009-11 | 空リスト → 空リスト | Low | [] が返る、subprocess 未呼び出し |

### UT-010: Article Numbering (`src/numbering.py`) **[NEW]**

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| UT-010-1 | 単一カテゴリ: 1から連番 | Critical | no が 1 始まりで連続する |
| UT-010-2 | 複数カテゴリ: アルファベット順に並び通し番号 | Critical | カテゴリはアルファベット順、番号はカテゴリをまたいで連続 |
| UT-010-3 | カテゴリ内: published 降順ソート | High | 新しい記事が先になる |
| UT-010-4 | 空リスト → 空リスト | Medium | [] が返る |
| UT-010-5 | 連番に途切れがない | High | no が 1〜N まで飛びなし |
| UT-010-6 | 複数カテゴリをまたいで番号が連続する | High | Alpha: 1,2 → Beta: 3 のように通し番号 |

### UT-011: Index Writer (`src/index_writer.py`) **[NEW]**

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| UT-011-1 | 正常書き込み（AMセッション） | Critical | session='AM' かつファイル名が `news_index_YYYYMMDD_HHMM.json` 形式で出力される |
| UT-011-2 | 正常書き込み（PMセッション） | Critical | session='PM' かつファイル名が `news_index_YYYYMMDD_HHMM.json` 形式で出力される |
| UT-011-3 | JSONフォーマット検証（全フィールド存在確認） | Critical | session, run_time, article_count, articles が存在。articles 内に no, title_ja, title_en, link, source, category, published が存在 |
| UT-011-4 | FIFO: max_files=3 で4件目書き込み時に最古が削除 | High | ファイル数が max_files 以内に収まる、最古が削除 |
| UT-011-5 | FIFO: ファイル名ソートが HHMM の辞書順で時系列と一致 | Medium | `YYYYMMDD_HHMM` フォーマットのファイルが辞書順で時系列順と一致する |
| UT-011-6 | ディレクトリ不在時は自動作成（実装依存） | Low | index_dir が存在しない場合に自動作成される（実装がそうなっている場合のみ） |
| UT-011-7 | save_index=False → 書き込みスキップ | High | ファイルが生成されない |
| UT-011-8 | I/O エラー → パイプライン継続（例外を吐かない） | Critical | write_index が例外を外に伝播しない |
| UT-011-9 | 複数記事の article_count が正しい | High | article_count と articles の len が一致 |

---

## Integration Tests

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| IT-001-1 | Fetch → Time Filter の連携 | Critical | 取得→フィルタが正しく動作 |
| IT-001-2 | State ファイルの永続化 | High | 書き込み→読み込みで値が一致 |
| IT-002-1 | Filter → Deduplicator の連携 | High | フィルタ済みリストが重複排除される |
| IT-002-2 | Dedup + Gemini 呼び出し回数の確認 | Medium | バッチ数分の Gemini CLI 呼び出し |
| IT-003-1 | Dedup → HTML Builder の連携 | High | 重複排除後の記事で HTML 生成 |
| IT-004-1 | HTML Builder → Email Sender の連携 | High | HTML をモック SMTP で送信 |
| IT-005-1 | Translator → Numbering → HTML Builder の連携 | High | 翻訳済み title_ja を持つ NumberedArticle で HTML が生成される |
| IT-005-2 | Translator → Numbering → Index Writer の連携 | High | 翻訳済み記事が JSON に書き出され no が一致する |
| IT-005-3 | Numbering 後の no 順序が HTML/JSON で一致するか | Critical | HTML と JSON インデックスで同一 no が同一記事を指す |

---

## E2E Tests

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| E2E-001-1 | Dry-run パイプライン | Critical | メール未送信 + HTML ファイル保存 |
| E2E-001-2 | フルパイプライン（メールモック） | Critical | 全コンポーネント連携 + メール送信 |
| E2E-001-3 | Gemini ダウン時のフォールバック（dedup） | High | 重複排除スキップでパイプライン完了 |
| E2E-002-1 | --dry-run フラグ | High | メール送信しない |
| E2E-002-2 | --fetch-only フラグ | High | フェッチ+フィルタのみ |
| E2E-002-3 | --force フラグ | Medium | last_run を無視 |
| E2E-003-1 | translation.enabled=True の full pipeline | High | Translator が呼ばれ title_ja が HTML/JSON に反映される |
| E2E-003-2 | translation.enabled=False の full pipeline | High | Translator がスキップされ title_ja="" のままで HTML/JSON が生成される |
| E2E-003-3 | index.save_index=True の full pipeline | High | output/ に news_index_YYYYMMDD_HHMM.json が生成される |
| E2E-004-1 | メール件名の JST 日付フォーマット検証（AM セッション） | High | 件名が `News Digest \| AM \| N articles \| YYYY-MM-DD HH:MM JST - YYYY-MM-DD HH:MM JST` 形式で、UTC ではなく JST 時刻が含まれる |
| E2E-004-2 | メール件名の JST 日付フォーマット検証（PM セッション） | High | 件名が `News Digest \| PM \| N articles \| YYYY-MM-DD HH:MM JST - YYYY-MM-DD HH:MM JST` 形式で、UTC ではなく JST 時刻が含まれる |
| E2E-004-3 | 件名に UTC 文字列が含まれないこと | High | 件名中に "UTC" が含まれず "JST" が含まれる |

---

## Boundary Condition Tests

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| BC-001 | 0件の記事（全フィード空） | High | 正常終了 |
| BC-002 | max_articles_per_email 超過 | Medium | 指定件数で切り捨て |
| BC-003 | 全記事が同一 URL | Medium | 1件のみ残る |
| BC-004 | 全記事が同一タイトル | Medium | 1クラスタ → 1件 |
| BC-005 | タイムゾーン混在（UTC, JST, EST） | High | 全て UTC に正規化して比較 |

---

## Acceptance Criteria Traceability

| Architecture Requirement | Test Coverage |
|---|---|
| 時間ウィンドウ内の記事をフィルタ | UT-003-1, UT-003-2, IT-001-1 |
| Feedly プロキシ URL のスキップ | UT-001-2 |
| URL 完全一致の重複排除 | UT-004-1, UT-004-2 |
| タイトル類似度によるクラスタリング | UT-005-1, UT-005-2 |
| preferred_sources の優先選択 | UT-005-3, UT-005-4 |
| Gemini 障害時のフォールバック（dedup） | UT-005-5, UT-005-7, UT-005-8, E2E-001-3 |
| on_dedup_failure 設定（fail/send_anyway） | UT-005-7, UT-005-8, UT-008-5 |
| 英→日タイトル翻訳（Translator） | UT-009-1〜11, IT-005-1, E2E-003-1, E2E-003-2 |
| translation.enabled=False スキップ | UT-009-10, E2E-003-2 |
| 翻訳失敗時のフォールバック (skip/fail) | UT-009-6, UT-009-7, UT-009-8 |
| batch_interval_seconds によるバッチ間インターバル | UT-009-2, UT-008-6 |
| グローバル通し番号付与（Numbering） | UT-010-1〜6, IT-005-3 |
| カテゴリ別グループ化（HTML Builder） | UT-006-2, UT-006-10 |
| No.列と title_ja の HTML 出力 | UT-006-7, UT-006-8, UT-006-9 |
| HTML Builder が再ソートしない | UT-006-10 |
| JSON インデックス書き込み (Index Writer) | UT-011-1〜9, IT-005-2, E2E-003-3 |
| FIFO による古いインデックス削除 | UT-011-4, UT-011-5 |
| Index Writer I/O エラー時のパイプライン継続 | UT-011-8 |
| save_index=False スキップ | UT-011-7 |
| Gmail SMTP 送信 | UT-007-1, IT-004-1 |
| リトライ機構（指数バックオフ） | UT-007-3 |
| 状態永続化（障害復旧） | UT-003-6, IT-001-2 |
| ログローテーション | RotatingFileHandler の設定確認 |
| Auto Shutdown | 自動テスト対象外（手動確認のみ）: systemd/cron の設定は本テストスコープ外 |
| Truncation は Numbering の前に行う（順序制約） | 未実装（v2.0スコープ外、次バージョン推奨）: IT-005-1〜3 で間接的に動作確認のみ |
| メール件名フォーマット（[AM/PM], 日付, 件数, JST） | E2E-004-1〜3（v2.1で追加） |
| 空リスト時のメッセージ | UT-006-5 |
| max_articles 制限 | UT-006-6, BC-002 |
| HTML/JSON インデックスの番号一致 | IT-005-3, E2E-003-1 |

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
|---|---|---|
| Critical | 26 | Core functionality, must pass |
| High | 48 | Important features, should pass |
| Medium | 19 | Edge cases |
| Low | 3 | Minor scenarios |
| **合計** | **96** | 実装済み93件 + 未実装BC 3件 |

**内訳（新規追加分）:**

| Section | New Cases | Notes |
|---|---|---|
| UT-006 | +5 (007〜011) | NumberedArticle 対応 |
| UT-009 | +11 | Translator 全ユニットテスト |
| UT-010 | +6 | Article Numbering 全ユニットテスト |
| UT-011 | +9 | Index Writer 全ユニットテスト |
| IT | +3 (005-1〜3) | 新コンポーネント間連携テスト |
| E2E | +3 (003-1〜3) | translation/index 有効化のパイプラインテスト |
| BC | +2 (001, 005) | 境界条件テスト実装済み（BC-002〜004 は未実装） |
