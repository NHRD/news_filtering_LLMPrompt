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
| UT-003-6 | last_run を使った障害復旧 | Medium | max(last_run, now-12h) を cutoff に使用 |

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
| UT-005-5 | Ollama タイムアウト時のフォールバック (send_anyway) | Critical | 全記事返却 |
| UT-005-6 | 空リストの処理 | Low | 空リストを返す |
| UT-005-7 | on_dedup_failure=fail 時の Ollama 障害 | High | SystemExit(1) が raise される |
| UT-005-8 | Model not found (HTTP 404) 時の処理 | Critical | CRITICAL ログ + SystemExit(1) |

### UT-006: HTML Builder (`src/html_builder.py`)

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| UT-006-1 | 有効な HTML を生成 | Critical | DOCTYPE, html タグを含む |
| UT-006-2 | カテゴリ別にグループ化 | High | カテゴリ名で分類 |
| UT-006-3 | 日付順にソート | High | 新しい記事が先 |
| UT-006-4 | HTML エスケープ | High | XSS 攻撃を防止 |
| UT-006-5 | 空リスト時のメッセージ | Medium | "No articles" メッセージ表示 |
| UT-006-6 | max_articles 制限 | Medium | 指定件数で切り捨て |

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
| UT-008-5 | on_dedup_failure のデフォルト値 | Medium | "send_anyway" がデフォルト |

---

## Integration Tests

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| IT-001-1 | Fetch → Time Filter の連携 | Critical | 取得→フィルタが正しく動作 |
| IT-001-2 | State ファイルの永続化 | High | 書き込み→読み込みで値が一致 |
| IT-002-1 | Filter → Deduplicator の連携 | High | フィルタ済みリストが重複排除される |
| IT-002-2 | Dedup + Ollama 呼び出し回数の確認 | Medium | 記事数分の embedding 呼び出し |
| IT-003-1 | Dedup → HTML Builder の連携 | High | 重複排除後の記事で HTML 生成 |
| IT-004-1 | HTML Builder → Email Sender の連携 | High | HTML をモック SMTP で送信 |

---

## E2E Tests

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| E2E-001-1 | Dry-run パイプライン | Critical | メール未送信 + HTML ファイル保存 |
| E2E-001-2 | フルパイプライン（メールモック） | Critical | 全コンポーネント連携 + メール送信 |
| E2E-001-3 | Ollama ダウン時のフォールバック | High | 重複排除スキップでパイプライン完了 |
| E2E-002-1 | --dry-run フラグ | High | メール送信しない |
| E2E-002-2 | --fetch-only フラグ | High | フェッチ+フィルタのみ |
| E2E-002-3 | --force フラグ | Medium | last_run を無視 |

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
| 12時間以内の記事をフィルタ | UT-003-1, UT-003-2, IT-001-1 |
| Feedly プロキシ URL のスキップ | UT-001-2 |
| URL 完全一致の重複排除 | UT-004-1, UT-004-2 |
| タイトル類似度によるクラスタリング | UT-005-1, UT-005-2 |
| preferred_sources の優先選択 | UT-005-3, UT-005-4 |
| Ollama 障害時のフォールバック | UT-005-5, UT-005-7, E2E-001-3 |
| Model not found 時の即時停止 | UT-005-8 |
| on_dedup_failure 設定 | UT-005-5, UT-005-7, UT-008-5 |
| カテゴリ別グループ化 | UT-006-2 |
| Gmail SMTP 送信 | UT-007-1, IT-004-1 |
| リトライ機構（指数バックオフ） | UT-007-3 |
| 状態永続化（障害復旧） | UT-003-6, IT-001-2 |
| ログローテーション | RotatingFileHandler の設定確認 |
| 空リスト時のメッセージ | UT-006-5 |
| max_articles 制限 | UT-006-6, BC-002 |

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
| Critical | 16 | Core functionality, must pass |
| High | 23 | Important features, should pass |
| Medium | 12 | Edge cases |
| Low | 1 | Minor scenarios |
