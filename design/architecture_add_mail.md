# RSS + Mailing List News Filtering Architecture (with Gmail Integration)

## Overview

本ドキュメントは、既存の RSS ニュースフィルタリングシステム (`design/architecture.md`) に、
**Gmail に届くメーリングリストのメール内容をスクリーニング対象として追加**した改訂版アーキテクチャを定義する。

RSS フィードからの記事取得に加え、指定した Gmail ラベルのメールを IMAP 経由で取得し、
同じパイプライン（時間フィルタ → 重複排除 → HTML 生成 → メール送信）に統合する。

**メール本文はダイジスト HTML にインライン埋め込み**する方針とする。
これにより、会社メールアドレスで受信したダイジェストからリンクをクリックした際に
個人 Gmail が開いてしまう問題を回避する。

**Note:** For workflow details (agent coordination, step-by-step execution), see `workflow.md`.

---

## 変更点サマリー

| 区分 | 変更内容 |
|------|---------|
| 新規コンポーネント | `src/mail_fetcher.py` (Gmail IMAP メーリングリスト取得) |
| 変更コンポーネント | `src/__init__.py` (`Article` に `body: str = ""` フィールド追加) |
| 変更コンポーネント | `src/config.py` (`MailingListEntry`, `MailFetchConfig` 追加, `AppConfig` 拡張) |
| 変更コンポーネント | `src/main.py` (mail_fetcher を呼び出し、`cutoff` を渡して RSS 記事と結合) |
| 変更コンポーネント | `src/deduplicator.py` (`link=""` を URL 完全一致重複排除の対象外に変更) |
| 変更コンポーネント | `src/html_builder.py` (`body` フィールドが非空の場合に本文テキストをインライン表示) |
| 変更ファイル | `config.yaml` (`mailing_lists` セクション追加) |
| 変更なし | `src/time_filter.py`, `src/rss_fetcher.py`, `src/email_sender.py` |
| 変更なし | `.env.example` (既存の `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` を流用) |

---

## System Flow Diagram

```
                    +----------------+
                    |   Scheduler    |
                    | (cron/systemd) |
                    +-------+--------+
                            |
                            | triggers every 24h
                            v
+------------------+    +-------------------+    +------------------+
|  default_rss.opml| -> |  RSS Fetcher      | -> |  RSS Articles    |
|  (feed sources)  |    |  (feedparser)     |    |  (body="")       |
+------------------+    +-------------------+    +--------+---------+
                                                          |
                                                          | merge (list concat)
+------------------+    +-------------------+            |
|  Gmail IMAP      | -> |  Mail Fetcher     | -> +-------v----------+
|  mailing lists   |    |  (imaplib/email)  |    |  Combined Article |
|  (configured)    |    |  RFC822 + plain   |    |  List (raw)       |
+------------------+    +-------------------+    +--------+---------+
                                                          |
                                                          | filter: last 24h (or since last_run)
                                                          v
                                                +-------------------+
                                                | Time Filter       |
                                                | (published >= cut)|
                                                +---------+---------+
                                                          |
                                                          v
                                                +-------------------+
                                                |  LLM Deduplicator |
                                                |  (Ollama/nomic)   |
                                                +---------+---------+
                                                          |
                                                          v
                                                +-------------------+
                                                |  HTML Builder     |
                                                |  title + body     |
                                                |  (body inline)    |
                                                +---------+---------+
                                                          |
                                                          v
                                                +-------------------+
                                                |  Email Sender     |
                                                |  (Gmail SMTP)     |
                                                +---------+---------+
                                                          |
                                                          v
                                                +-------------------+
                                                |  Auto Shutdown    |
                                                |  (Optional)       |
                                                +---------+---------+
                                                          |
                                                          v
                                                +-------------------+
                                                | Recipients:       |
                                                | - Personal Gmail  |
                                                | - Company Email   |
                                                +-------------------+
```

---

## Components

### 1. Scheduler / 2. RSS Fetcher / 3. Time Filter / 4. LLM Deduplicator / 6. Email Sender / 7. Auto Shutdown

これらは既存の `design/architecture.md` の仕様と同一。変更なし。

---

### 新規: Mail Fetcher (`src/mail_fetcher.py`)

#### 責務

Gmail IMAP 経由で、設定ファイルに登録された Gmail ラベル宛のメールを取得し、
既存の `Article` NamedTuple に変換して返す。
メール件名を `title`、テキスト本文を `body` に格納する。外部リンクは使用しない (`link=""`)。

#### 接続方式

| 項目 | 仕様 |
|------|------|
| プロトコル | IMAP over SSL (`imaplib.IMAP4_SSL`) |
| サーバー | `imap.gmail.com` (デフォルト) |
| ポート | `993` |
| 認証 | Gmail アドレス + App Password (既存の `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` を流用) |
| OAuth | 不要（SMTP と同一の App Password で接続可能） |

**新規 OAuth 設定不要** — 既存の `.env` 認証情報をそのまま利用する。

#### メーリングリストの識別方法

**Gmail ラベル方式のみ**をサポートする。
対象メールには事前に Gmail フィルターでラベルを設定しておく。

`SELECT` で指定したラベルのフォルダに接続し、`SEARCH SINCE` で時間絞り込みを行う。
ラベル名に空白を含む場合は `"Tech news"` のようにダブルクォートで囲む。

#### Article 変換ルール

| Article フィールド | マッピング元 |
|-------------------|------------|
| `title` | メール件名 (`Subject` ヘッダ、RFC 2047 デコード済み) |
| `link` | 常に空文字列 `""` (外部リンクなし) |
| `published` | `Date` ヘッダを offset-aware UTC `datetime` に変換 (`parsedate_to_datetime` + `astimezone(timezone.utc)`) |
| `source` | 設定ファイルの `name` フィールド (例: "Tech mailing list") |
| `category` | 設定ファイルの `category` フィールド (例: "Tech news") |
| `body` | RFC 2047 デコードしたメール `text/plain` 本文 |

#### 処理フロー

```python
def fetch_mail_articles(config: MailFetchConfig, cutoff: datetime) -> list[Article]:
    """
    1. mailing_lists.enabled が False なら空リストを返す
    2. IMAP4_SSL で接続・ログイン (失敗時は WARNING + 空リストを返す)
    3. 各 mailing_list 設定に対してループ:
       a. SELECT で Gmail ラベルフォルダを開く
       b. SEARCH SINCE で cutoff 以降のメッセージIDを取得
       c. 各メッセージを RFC822 (ヘッダ + 本文) で FETCH
       d. Subject → title, Date → published, text/plain → body として Article 生成
    4. 全 mailing_list の Article を結合して返す
    """
```

#### ヘッダ/本文デコード方針

- Subject: `email.header.decode_header` で RFC 2047 をデコードする。
- Date: `email.utils.parsedate_to_datetime` で `datetime` に変換し、`timezone.utc` に正規化する。
- Body: `Message.walk()` で multipart を走査し、`text/plain` パートを使用する。
  `text/plain` がなければ `body=""` とする。
- 文字コード: 各パートの charset 指定を優先し、未指定時は UTF-8 フォールバックで decode する。

#### エラーハンドリング

メーリングリスト取得はニュースソースの一つに過ぎないため、**グレースフルデグレード**とする。
IMAP 接続・個別リスト取得が失敗しても、RSS 記事のみで処理を継続する。

| エラー種別 | 動作 |
|-----------|------|
| IMAP 接続失敗 (ネットワーク) | WARNING ログ → メーリングリスト取得をスキップ、RSS のみで続行 |
| IMAP 認証失敗 | WARNING ログ → スキップ（認証情報の確認を促す） |
| 個別リストのフェッチ失敗 | WARNING ログ → その列のみスキップ、他のリストと RSS は続行 |
| メール解析エラー (1件) | WARNING ログ → その1件をスキップ、処理続行 |
| `mailing_lists.enabled: false` | 取得処理を行わず空リストを返す (既存動作と同一) |

**IMAP 失敗はパイプライン全体を止めない**。この点が Ollama 失敗時の動作（パイプライン停止）と異なる。

---

### 更新: `src/__init__.py` の Article NamedTuple

```python
class Article(NamedTuple):
    title: str
    link: str
    published: datetime
    source: str
    category: str
    body: str = ""   # NEW: メーリングリストメール本文 (text/plain)。RSS 記事は空文字列
```

`body` フィールドはデフォルト値 `""` を持つため、既存コードへの影響はない。

---

### 更新: HTML Builder (`src/html_builder.py`)

`Article.body` が非空の場合、タイトル・メタデータの下に本文テキストをインライン表示する。
これにより受信者はダイジェストメール内でメーリングリストの内容を完結して読めるため、
**外部リンクへのアクセスが不要**になる。

```
[カテゴリ: Tech news]
  ■ <件名>
    [source: Tech mailing list | 2026-03-01 06:00 UTC]
    <メール本文テキスト (折り返し表示)>
```

RSS 記事 (`body=""`) は従来通り、タイトル + リンクのみを表示する。

---

### 更新: `main.py` の Pipeline 統合

`run_pipeline` 関数に以下の変更を加える:

```python
# 既存: RSS 記事取得
feeds = parse_opml(...)
rss_articles = fetch_articles(feeds, ...)

# cutoff は last_run_timestamp から算出した UTC datetime (既存ロジック)
cutoff = ...

# 新規: メーリングリスト記事取得（失敗しても続行）
mail_articles = fetch_mail_articles(config.mail_fetch, cutoff=cutoff)

# 結合
articles = rss_articles + mail_articles
logging.info("[Main] Combined: %d RSS + %d mail articles", len(rss_articles), len(mail_articles))

# 以降は変更なし (time_filter → dedup → html_builder → email_sender)
```

`cutoff` は `load_last_run_timestamp` の結果から既存ロジックで算出した値を流用する。
IMAP 側で `SEARCH SINCE` により候補を先に絞り、`time_filter` は最終的な安全弁として維持する。

---

## Configuration

### `config.yaml` 変更点

既存の全セクションは変更なし。以下の `mailing_lists` セクションを追加する。

```yaml
# (既存セクション: feeds, schedule, llm, deduplication, email, output, system は変更なし)

# --- NEW: Mailing List Configuration ---
mailing_lists:
  enabled: true          # false にするとメーリングリスト取得をスキップ
  imap_server: "imap.gmail.com"
  imap_port: 993
  # 認証情報は既存の .env 変数を流用
  # GMAIL_ADDRESS / GMAIL_APP_PASSWORD
  timeout_seconds: 30    # IMAP 接続タイムアウト

  lists:
    - name: "Tech mailing list"   # Article.source に使用
      category: "Tech news"       # Article.category に使用 (HTML グルーピング用)
      label: "Tech news"          # Gmail ラベル名 (スペースありはそのまま記載)
```

### `.env` / `.env.example` 変更点

**変更なし**。既存の `GMAIL_ADDRESS` と `GMAIL_APP_PASSWORD` を IMAP 接続でも流用するため、
新規環境変数の追加は不要。

```env
# 既存のまま使用 (変更なし)
GMAIL_ADDRESS=your.email@gmail.com
GMAIL_APP_PASSWORD=your-app-password-here
PERSONAL_EMAIL=your.email@gmail.com
COMPANY_EMAIL=your.email@company.com
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Config Data Model (`src/config.py`)

既存の各 `NamedTuple` は変更しない。以下を追加する。

```python
class MailingListEntry(NamedTuple):
    name: str        # Article.source に使用
    category: str    # Article.category に使用 (HTML グルーピング用)
    label: str       # Gmail ラベル名 (スペースあり可)


class MailFetchConfig(NamedTuple):
    enabled: bool
    imap_server: str
    imap_port: int
    imap_user: str          # GMAIL_ADDRESS から取得
    imap_password: str      # GMAIL_APP_PASSWORD から取得
    timeout_seconds: int
    lists: List[MailingListEntry]


class AppConfig(NamedTuple):
    feeds: FeedConfig
    schedule: ScheduleConfig
    llm: LLMConfig
    deduplication: DeduplicationConfig
    email: EmailConfig
    output: OutputConfig
    system: SystemConfig
    mail_fetch: MailFetchConfig  # NEW
```

---

## HTML Builder への影響

`Article.body` が非空の場合、テンプレート (`templates/email.html`) で本文テキストを
タイトル・メタデータの下にインライン表示する。

`Article.category` が `"Tech news"` などになるため、
HTML メールの既存カテゴリーグルーピングロジックにより、
メーリングリスト由来の記事は自動的に専用カテゴリーセクションに分類される。

---

## Deduplication への影響

メーリングリスト記事も RSS 記事と同一のパイプラインで重複排除される。

- **Stage 1 (URL一致)**: メーリングリスト記事は `link=""` のため URL 重複排除の対象外となり、常に保持される。
- **Stage 2 (タイトル類似度)**: メール件名が他の記事タイトルと類似していれば重複排除される。

### 更新: `src/deduplicator.py` の仕様

`_dedup_by_exact_url` は `link=""` を重複判定キーとして扱わない。
URL が空の `Article` は Stage 1 で常に保持し、URL が存在する記事のみ exact URL 重複排除の対象とする。

```python
def _dedup_by_exact_url(articles):
    by_url = {}
    unique_articles = []
    for article in articles:
        if not article.link:
            unique_articles.append(article)
            continue
        existing = by_url.get(article.link)
        if existing is None or article.published > existing.published:
            by_url[article.link] = article
    return unique_articles + list(by_url.values())
```

---

## Error Handling 全体表

既存テーブルに行を追加する。

| Component | Error Type | Action |
|-----------|-----------|--------|
| RSS Fetcher | Feed timeout | Log warning, continue with other feeds |
| RSS Fetcher | Feed parse error | Log warning, continue |
| RSS Fetcher | No articles found | Log info, continue |
| **Mail Fetcher** | **IMAP connection failure** | **Log WARNING, skip mail fetch entirely, continue with RSS only** |
| **Mail Fetcher** | **IMAP auth failure** | **Log WARNING, skip mail fetch entirely, continue with RSS only** |
| **Mail Fetcher** | **Individual list fetch failure** | **Log WARNING, skip that list, continue with other lists** |
| **Mail Fetcher** | **Email parse error (per message)** | **Log WARNING, skip that message, continue** |
| Time Filter | Invalid date | Skip article, log warning |
| LLM Deduplicator | Ollama unavailable | Send error email, log ERROR, abort. Do not update state. |
| LLM Deduplicator | Model not found | Send error email, log CRITICAL, abort. Do not update state. |
| HTML Builder | Template error | Exit with error |
| Email Sender | Auth failure | Exit with error, send alert if possible |
| Email Sender | Network error | Retry 3 times with exponential backoff |

---

## File Structure 変更点

```diff
  news_filtering/
  ├── design/
  │   ├── architecture.md          # 既存アーキテクチャ (RSS のみ)
+ │   ├── architecture_add_mail.md # 本ドキュメント (RSS + メーリングリスト統合版)
  │   ├── architecture_review.md
  │   └── review_artifact/
  ├── src/
+ │   ├── __init__.py              # 変更: Article に body フィールド追加
  │   ├── main.py                  # 変更: mail_fetcher を呼び出し、結果を結合
  │   ├── config.py                # 変更: MailingListEntry, MailFetchConfig 追加
+ │   ├── mail_fetcher.py          # 新規: Gmail IMAP メーリングリスト取得
  │   ├── rss_fetcher.py           # 変更なし
  │   ├── time_filter.py           # 変更なし
  │   ├── deduplicator.py          # 変更: link="" は Stage 1 URL 重複排除の対象外
+ │   ├── html_builder.py          # 変更: body フィールドがある場合に本文インライン表示
  │   └── email_sender.py          # 変更なし
  ├── config.yaml                  # 変更: mailing_lists セクション追加
  ├── .env                         # 変更なし (既存の GMAIL_* を流用)
  └── .env.example                 # 変更なし
```

---

## Dependencies 変更点

**新規外部ライブラリ追加なし**。

| ライブラリ | 用途 | 区分 |
|-----------|------|------|
| `imaplib` | IMAP 接続 | Python stdlib |
| `email` | メール解析 (ヘッダ・本文デコード) | Python stdlib |

```diff
  # requirements.txt (変更なし)
  feedparser>=6.0.0
  requests>=2.28.0
  pyyaml>=6.0
  python-dotenv>=1.0.0
  jinja2>=3.1.0
  scikit-learn>=1.3.0
  numpy>=1.24.0
```

---

## Gmail IMAP セットアップ要件

既存の Gmail App Password 設定で IMAP も利用可能。追加設定が必要な場合のみ対応する。

1. **Gmail IMAP 有効化確認**: Gmail 設定 > 転送とPOP/IMAP > IMAP アクセス: **有効**
2. **App Password**: 既存のものをそのまま使用（SMTP と共有）
3. **Gmail ラベル設定**: 対象のメーリングリストメールに Gmail フィルターでラベルを事前に設定しておく

---

## Execution Modes

既存モード (`--dry-run`, `--fetch-only`, `--force`) はすべて同様に動作する。
`--fetch-only` モード時はメーリングリスト取得も行うが、重複排除以降は実行しない（既存動作と同一）。

---

## 変更後のログ出力例

```
2026-03-01 06:00:01 INFO  [RSS Fetcher] Found 110 unique feeds in OPML
2026-03-01 06:00:05 WARN  [RSS Fetcher] Timeout: nitter.net/...
2026-03-01 06:01:30 INFO  [RSS Fetcher] Fetched 450 articles from 95 feeds
2026-03-01 06:01:31 INFO  [Mail Fetcher] Connecting to imap.gmail.com:993
2026-03-01 06:01:32 INFO  [Mail Fetcher] Fetching list: Tech mailing list (label:Tech news)
2026-03-01 06:01:33 INFO  [Mail Fetcher] Fetched 12 articles from "Tech mailing list"
2026-03-01 06:01:33 INFO  [Main] Combined: 450 RSS + 12 mail articles (total: 462)
2026-03-01 06:01:33 INFO  [Time Filter] 134 articles within last 24 hours
2026-03-01 06:01:38 INFO  [Deduplicator] Reduced to 91 unique articles
2026-03-01 06:01:39 INFO  [HTML Builder] Generated email (24KB)
2026-03-01 06:01:41 INFO  [Email Sender] Sent to 2 recipients
2026-03-01 06:01:41 INFO  [Main] Cycle completed successfully
```

---

## 設計上の判断事項・トレードオフ

| 判断事項 | 採用した方針 | 理由 |
|---------|------------|------|
| Gmail アクセス方式 | IMAP (App Password) | OAuth2 不要で既存 `.env` を流用でき、セットアップコストが最小 |
| IMAP 失敗時の動作 | グレースフルデグレード (RSS のみで続行) | メーリングリストはニュースの補助ソース。失敗でパイプライン全停止は過剰 |
| `link` フィールド | 常に `""` (外部リンクなし) | 会社メールで受信したダイジェストから個人 Gmail に誘導されるのを防ぐ |
| メール内容の表示方式 | `Article.body` に本文を格納しダイジストにインライン埋め込み | 受信者はダイジェストメールのみで内容を完結して読める |
| body フィールドのデフォルト | `body: str = ""` | 既存の RSS 記事には影響しない後方互換設計 |
| メーリングリスト識別方式 | Gmail ラベルのみ | FROM アドレス検索は不要な複雑さを生む。ラベル方式が実用的かつシンプル |
| 外部ライブラリ追加 | なし (stdlib のみ) | `requirements.txt` の変更を最小化し、依存リスクを抑制 |
| `on_dedup_failure` の適用 | 既存設定をそのまま適用 | メーリングリスト記事も RSS 記事も同一の重複排除ロジックを通過する |
