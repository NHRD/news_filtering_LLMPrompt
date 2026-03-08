# RSS News Filtering Architecture

## Overview

This document defines the system architecture for the RSS News Filtering System. The system runs every 24 hours, fetches RSS articles published within the last 24 hours, deduplicates them using a local LLM (Ollama with embedding model), and sends an HTML email summary.

**Note:** For workflow details (agent coordination, step-by-step execution), see `workflow.md`.

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
|  default_rss.opml| -> |  RSS Fetcher      | -> |  Article List    |
|  (feed sources)  |    |  (feedparser)     |    |  (raw articles)  |
+------------------+    +-------------------+    +--------+---------+
                                                         |
                                                         | filter: last 24h
                                                         v
                                               +-------------------+
                                               | Time Filter       |
                                               | (published_date   |
                                               |  >= now - 24h)    |
                                               +---------+---------+
                                                         |
                                                         v
                                               +-------------------+
                                               | Gemini Deduplicator|
                                               |  (Gemini CLI)     |
                                               +---------+---------+
                                                         |
                                                         v
                                               +-------------------+
                                               |  HTML Builder     |
                                               |  (title + URL)    |
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

## Components

### 1. Scheduler

**Responsibility:** Trigger the pipeline every 24 hours

**Options:**
- **cron** (recommended for simplicity)
- **systemd timer**
- **Python scheduler** (APScheduler)

**cron example:**
```cron
0 6 * * * /path/to/venv/bin/python /path/to/main.py >> /path/to/logs/news_filter.log 2>&1
```

**Execution times:** 06:00 daily

---

### 2. RSS Fetcher

**Input:** `default_rss.opml` (Configurable via `feeds.opml_file`)

**Output:** List of articles with metadata

**Process:**
1. Parse OPML to extract feed URLs
2. Skip Feedly proxy URLs (`https://feedly.com/web/...`)
3. Deduplicate feed URLs
4. Fetch each feed with `feedparser`
5. Extract: `title`, `link`, `published_date`, `source_name`
6. Handle timeouts and errors gracefully

**Data Structure:**
```python
from typing import NamedTuple

class Article(NamedTuple):
    title: str
    link: str
    published: datetime
    source: str
    category: str  # from OPML folder
```

---

### 3. Time Filter

**Input:** All fetched articles

**Output:** Articles published within the last 24 hours

**Logic:**
```python
cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
recent_articles = [a for a in articles if a.published >= cutoff]
```

**Edge cases:**
- Articles without `published_date`: **exclude** and log WARNING
- Timezone handling: normalize all dates to UTC
- **Timezone-naive dates:** If `published_parsed` lacks timezone info, assume UTC and log WARNING

**State Persistence (Failure Recovery):**
- Save timestamp of last successful run to `state/last_run.json`.
- **Update Timing:** The `state/last_run.json` file is updated with the current timestamp **only after** the entire pipeline has completed successfully. A successful completion means either:
  - The news summary email has been sent without errors.
  - The `--dry-run` option was used and the HTML file was saved successfully.
- If any step in the pipeline fails (including network errors, LLM failures, etc.), the state file **will not** be updated.
- On the next run, the system will use the older timestamp from the state file, ensuring that any articles from the failed run's time window are re-processed and not missed.
- The cutoff for new articles is calculated as `max(last_run_timestamp, now - 24h)`.

---

### 4. Gemini Deduplicator

**Input:** List of recent articles

**Output:** Deduplicated list of unique articles

**Purpose:** Remove duplicate/similar articles that cover the same news story using Gemini CLI's natural language understanding

**Failure Behavior:**
- **Gemini CLI unavailable / non-zero exit:** Controlled by `on_dedup_failure` config setting:
  - `send_anyway` (default): Skip deduplication and proceed with all articles. Log WARNING.
  - `fail`: Abort pipeline with exit code 1. Log ERROR. The `state/last_run.json` file **is not** updated to ensure re-processing on the next run.
- **Output parse failure:** Treat as Gemini unavailable and apply `on_dedup_failure` behavior.

**Two-Stage Deduplication Process:**

#### Stage 1: Exact URL Deduplication
- Remove articles with identical `link` values
- Keep the most recent one (by `published` date)

#### Stage 2: Title Deduplication via Gemini CLI
1. Build a numbered list of `"N. [title] (source)"` from Stage 1 output
2. If article count exceeds `dedup_batch_size` (default: 80), split into batches and process each batch independently
3. Pass the list to Gemini CLI with the following prompt:
   ```
   以下はニュース記事のタイトル一覧です（番号. タイトル (ソース) の形式）。
   同じニュースを報じている記事をグループ化し、各グループから1記事だけ残してください。
   残す記事の選択基準（優先順）:
     1. preferred_sources（Reuters, Bloomberg, TechCrunch, The Verge）に含まれるソースがあればその中で最新のもの
     2. なければグループ内で最新のもの
   出力は残す記事の番号のみをカンマ区切りで返してください。説明文は不要です。
   例: 1,3,5,8,12
   ```
4. Parse the comma-separated index list from Gemini's output
5. Return the articles at the specified indices

**Gemini CLI Integration:**
```python
import subprocess

def deduplicate_by_gemini(articles, preferred_sources, batch_size=80):
    # Build numbered list: "1. Title (Source)"
    lines = [f"{i+1}. {a.title} ({a.source})" for i, a in enumerate(articles)]

    # Batch processing if needed
    if len(lines) > batch_size:
        return _deduplicate_in_batches(articles, preferred_sources, batch_size)

    prompt = _build_prompt(lines, preferred_sources)
    result = subprocess.run(
        ["gemini", "-p", prompt],
        capture_output=True, text=True, timeout=60
    )
    result.check_returncode()

    indices = _parse_indices(result.stdout.strip(), len(articles))
    return [articles[i] for i in indices]
```

**Why Gemini over Embedding-based Clustering:**
- Embedding models measure vector distance and struggle with paraphrasing (e.g., "Fed hikes 25bp" vs "Federal Reserve raises rates by a quarter point")
- Gemini understands natural language semantics and correctly identifies such cases as the same story
- No local model infrastructure (Ollama) required

**Deduplication Criteria:**
- Same URL (exact match) → Stage 1
- Same news story regardless of wording → Stage 2 (Gemini)

---

### 5. HTML Builder

**Input:** Deduplicated articles

**Output:** HTML email body

**Template Structure:**
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; }
        .header { background: #1a73e8; color: white; padding: 20px; }
        .category { margin: 20px 0; }
        .category-title { color: #1a73e8; border-bottom: 2px solid #1a73e8; }
        .article { margin: 10px 0; padding: 10px; background: #f8f9fa; }
        .article-title { font-weight: bold; }
        .article-link { color: #1a73e8; text-decoration: none; }
        .article-meta { font-size: 0.8em; color: #666; }
        .footer { font-size: 0.8em; color: #666; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>News Digest</h1>
        <p>{{date_range}}</p>
        <p>{{article_count}} articles from {{source_count}} sources</p>
    </div>

    {{#each categories}}
    <div class="category">
        <h2 class="category-title">{{name}}</h2>
        {{#each articles}}
        <div class="article">
            <div class="article-title">
                <a href="{{link}}" class="article-link">{{title}}</a>
            </div>
            <div class="article-meta">{{source}} | {{published}}</div>
        </div>
        {{/each}}
    </div>
    {{/each}}

    <div class="footer">
        <p>Generated by RSS News Filter | {{generation_time}}</p>
    </div>
</body>
</html>
```

**Max Articles Handling:**
- To prevent overly large emails, the number of articles is limited by the `max_articles_per_email` setting in `config.yaml`.
- If the total number of unique articles exceeds this limit, the list is truncated to include only the **most recent** N articles, where N is `max_articles_per_email`.
- When truncation occurs, a notification will be added to the email's footer. For example: "Showing the 200 most recent articles out of 250 found."

**Date Formatting:**
- All dates displayed in the email are formatted as `YYYY-MM-DD HH:MM UTC` by the HTML Builder using `strftime('%Y-%m-%d %H:%M UTC')`.

**Empty Article List:**
- When no articles remain after filtering/dedup, render a "No articles found" message instead of empty content.

**Grouping:**
- Group articles by OPML category (Tech news, sub, Finance)
- Within each category, sort by publication date (newest first)

---

### 6. Email Sender

**Input:** HTML email body

**Output:** Email sent to recipients

**Configuration:**
```python
@dataclass
class EmailConfig:
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str  # Your Gmail address
    sender_password: str  # App password (not regular password)
    recipients: list[str]  # [personal_gmail, company_email]
```

**Gmail Setup Requirements:**
1. Enable 2-Factor Authentication on Gmail account
2. Generate App Password: Google Account > Security > App passwords
3. Store App Password securely (environment variable or .env file)

**Implementation:**
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(
    config: EmailConfig,
    subject: str,
    html_body: str
) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.sender_email
    msg["To"] = ", ".join(config.recipients)

    html_part = MIMEText(html_body, "html")
    msg.attach(html_part)

    with smtplib.SMTP(config.smtp_server, config.smtp_port) as server:
        server.starttls()
        server.login(config.sender_email, config.sender_password)
        server.sendmail(
            config.sender_email,
            config.recipients,
            msg.as_string()
        )
    return True
```

---

### 7. Auto Shutdown

**Responsibility:** Shut down the system after successful completion

**Logic:**
1. Wait for 3 minutes (180 seconds) to allow logs to be flushed and give user a chance to cancel.
2. Execute `sudo -n /usr/sbin/poweroff` command.

**Configuration:**
- `system.poweroff_after_run: bool` (default: false)

---

## Configuration File

**File:** `config.yaml`

**Configuration Loading Priority:**
1. Load `.env` file into environment variables
2. Read `config.yaml`
3. Environment variables override YAML values (where `${VAR}` syntax is used)

```yaml
# RSS Feed Configuration
feeds:
  opml_file: "default_rss.opml"
  timeout_seconds: 10
  skip_feedly_proxy: true

# Schedule Configuration
schedule:
  interval_hours: 24
  time_window_hours: 24  # Fetch articles from last N hours

# Gemini CLI Configuration
gemini:
  model: "gemini-2.0-flash"  # Model passed to gemini CLI (default: uses CLI default)
  dedup_batch_size: 80  # Max articles per Gemini request; splits into batches if exceeded

# Deduplication Settings
deduplication:
  preferred_sources:  # Articles from these sources are preferred when selecting cluster representatives
    - "Reuters"
    - "Bloomberg"
    - "TechCrunch"
    - "The Verge"

# Email Configuration
email:
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  sender_email: "${GMAIL_ADDRESS}"
  sender_password: "${GMAIL_APP_PASSWORD}"
  recipients:
    - "${PERSONAL_EMAIL}"  # Personal Gmail
    - "${COMPANY_EMAIL}"   # Company address
  max_articles_per_email: 200  # Prevent oversized emails

# Output Configuration
output:
  save_html: true
  html_dir: "./output"
  log_file: "./logs/news_filter.log"
  state_file: "./state/last_run.json"  # For failure recovery

# System Configuration
system:
  poweroff_after_run: false  # Set to true to shut down PC after completion
```

**Environment Variables (`.env`):**
```env
GMAIL_ADDRESS=your.email@gmail.com
GMAIL_APP_PASSWORD=your-app-password-here
PERSONAL_EMAIL=your.email@gmail.com
COMPANY_EMAIL=your.email@company.com
```

---

## Error Handling Strategy

| Component | Error Type | Action |
|-----------|-----------|--------|
| RSS Fetcher | Feed timeout | Log warning, continue with other feeds |
| RSS Fetcher | Feed parse error | Log warning, continue |
| RSS Fetcher | No articles found | Log info, continue |
| Time Filter | Invalid date | Skip article, log warning |
| Gemini Deduplicator | Gemini CLI unavailable / error | Configurable: skip dedup (`send_anyway`) or abort (`fail`) |
| Gemini Deduplicator | Output parse failure | Same as CLI unavailable; apply `on_dedup_failure` behavior |
| HTML Builder | Template error | Exit with error |
| Email Sender | Auth failure | Exit with error, send alert if possible |
| Email Sender | Network error | Retry 3 times with exponential backoff |

---

## Logging

**Log Levels:**
- `INFO`: Normal operation (fetching feeds, article counts)
- `WARNING`: Recoverable errors (feed timeout, skipped articles)
- `ERROR`: Critical failures (email auth, Ollama down)
- `CRITICAL`: Configuration errors requiring human intervention (model not found)

**Log Rotation:**
- Use Python's `RotatingFileHandler` with `maxBytes=10MB` and `backupCount=5`
- This prevents unlimited log growth while retaining recent history

**Log Format:**
```
2026-02-17 06:00:01 INFO  [RSS Fetcher] Starting fetch cycle
2026-02-17 06:00:01 INFO  [RSS Fetcher] Found 110 unique feeds in OPML
2026-02-17 06:00:05 WARN  [RSS Fetcher] Timeout: nitter.net/FirstSquawk/rss
2026-02-17 06:01:30 INFO  [RSS Fetcher] Fetched 450 articles from 95 feeds
2026-02-17 06:01:30 INFO  [Time Filter] 127 articles within last 24 hours
2026-02-17 06:01:35 INFO  [Deduplicator] Reduced to 89 unique articles
2026-02-17 06:01:36 INFO  [HTML Builder] Generated email (15KB)
2026-02-17 06:01:38 INFO  [Email Sender] Sent to 2 recipients
2026-02-17 06:01:38 INFO  [Main] Cycle completed successfully
```

---

## File Structure

```
news_filtering/
├── design/
│   ├── architecture.md       # システムアーキテクチャ設計 (This file)
│   ├── architecture_review.md # 設計レビュー結果
│   └── review_artifact/      # 実行後の評価資料
│       ├── final_review.md   # 最終評価レポート
│       ├── refactor_24h.md   # リファクタリング計画
│       └── issue_list.md     # 修正事項リスト
├── session_summaries/
│   └── session_summary_*.md  # 毎セッションの作業記録
├── src/
│   ├── __init__.py           # Article データクラス
│   ├── main.py               # エントリーポイント (CLI)
│   ├── config.py             # 設定読み込み
│   ├── rss_fetcher.py        # OPML 解析 + RSS 取得
│   ├── time_filter.py        # 時間フィルタリング
│   ├── deduplicator.py       # 2段階重複排除 (URL + Ollama embedding)
│   ├── html_builder.py       # HTML メール生成
│   └── email_sender.py       # Gmail SMTP 送信
├── templates/
│   ├── email.html            # HTML メールテンプレート (Jinja2)
│   └── error.html            # エラー通知テンプレート (Jinja2)
├── tests/
│   ├── test_*.py             # ユニットテスト・統合テスト
│   ├── test_data_template.py # 精度検証用テンプレート
│   ├── test_plan.md           # テスト計画書
│   └── test_results.md        # テスト結果レポート
├── config.yaml               # 設定ファイル
├── .env                      # 認証情報 (git 管理外)
├── .env.example              # .env のテンプレート
├── default_rss.opml          # RSS フィード一覧
├── workflow.md               # ワークフロー定義
├── workflow_state.json       # ワークフロー状態管理
├── agent_roles.md            # エージェント役割分担
└── requirements.txt          # Python 依存関係
```

---

## Execution Modes

### 1. Full Pipeline (Default)
```bash
python src/main.py
```

### 2. Dry Run (No Email)
```bash
python src/main.py --dry-run
```

### 3. Fetch Only (Debug)
```bash
python src/main.py --fetch-only
```

### 4. Force Run (Ignore Schedule)
```bash
python src/main.py --force
```

---

## Dependencies

**requirements.txt:**
```
feedparser>=6.0.0
pyyaml>=6.0
python-dotenv>=1.0.0
jinja2>=3.1.0
```

**External CLI dependency:**
- `gemini` CLI must be installed and authenticated (`gemini auth login`)

---

## Setup Instructions

1. **Clone and setup environment:**
   ```bash
   cd news_filtering
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Gmail credentials
   ```

3. **Verify Gemini CLI is installed and authenticated:**
   ```bash
   gemini --version
   gemini auth login  # if not yet authenticated
   ```

4. **Test the pipeline:**
   ```bash
   python src/main.py --dry-run
   ```

5. **Setup cron job:**
   ```bash
   crontab -e
   # Add: 0 6 * * * /path/to/venv/bin/python /path/to/src/main.py
   ```
