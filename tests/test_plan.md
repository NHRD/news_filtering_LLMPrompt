# Test Plan - RSS + Mailing List News Filtering System

## Overview

本テスト計画は `architecture_add_mail.md` の改訂版に基づき、RSS ニュースフィルタリングシステムへの **Gmail メーリングリスト統合機能（本文インライン埋め込み版）** の品質保証のために設計された。既存のテスト計画を更新し、新規コンポーネントおよび変更箇所の検証項目を追加・修正する。

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

### UT-004: URL Deduplication [更新]

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| UT-004-3 | **link="" の記事を保持** | Critical | **メーリングリスト記事（link=""）は重複排除されず全て保持される** |

### UT-006: HTML Builder (`src/html_builder.py`) [更新]

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| UT-006-7 | **body フィールドのインライン表示** | Critical | **Article.body がある場合、HTML 内にテキストが埋め込まれる** |
| UT-006-8 | RSS 記事のリンク表示 | High | body="" の記事は従来通りリンクが表示される |

### UT-008: Config Loader (`src/config.py`) [更新]

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| UT-008-6 | mailing_lists セクションのパース | Critical | lists 内の label が正確に読み込まれる（match_by は廃止） |
| UT-008-7 | imap_user/password の自動設定 | High | email セクションの認証情報が mail_fetch にコピーされる |

### UT-009: Mail Fetcher (`src/mail_fetcher.py`) [更新]

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| UT-009-1 | IMAP 接続・ログイン | Critical | imaplib を正しく呼び出し認証 |
| UT-009-3 | ラベル検索 | Critical | `SELECT "label"`, `SEARCH SINCE ...` を発行 |
| UT-009-4 | RFC 2047 Subject デコード | High | 日本語等の非 ASCII 件名が正しく復元される |
| UT-009-5 | Date ヘッダの UTC 変換 | High | タイムゾーンに関わらず正しい UTC datetime になる |
| UT-009-14 | **本文抽出 (text/plain)** | Critical | **メール本文（text/plain）が Article.body に格納される** |
| UT-009-15 | **リンクなし設定** | High | **メーリングリスト記事の Article.link は常に "" となる** |
| UT-009-9 | IMAP 接続失敗時の例外処理 | High | 例外をキャッチし WARNING ログを出力して続行 |
| UT-009-10 | enabled: false 時の動作 | Medium | IMAP 接続を行わず空リストを返す |

---

## Integration Tests

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| IT-005-1 | RSS + Mail の記事結合 | Critical | 両ソースの記事が1つのリストに統合される |
| IT-005-5 | **本文を含む HTML 生成の連携** | Critical | **Mail Fetcher で取得した本文が HTML Builder で正しく出力される** |

---

## E2E Tests

| ID | Description | Priority | Expected Result |
|---|---|---|---|
| E2E-001-4 | フルパイプライン (RSS + Mail Mock) | Critical | RSS と本文付きメールが統合されたダイジェストが送信される |

---

## Acceptance Criteria Traceability

| Architecture Requirement | Test Coverage |
|---|---|
| Gmail IMAP 経由の本文取得 | UT-009-14, E2E-001-4 |
| 本文のインライン表示 | UT-006-7, IT-005-5 |
| メーリングリストの `link=""` 固定 | UT-009-15 |
| 外部リンクなしでの重複排除回避 | UT-004-3 |
| Gmail ラベル方式への限定 | UT-008-6, UT-009-3 |

---

## Test Execution

```bash
# Run all tests
pytest tests/ -v
```
