# RSS News Filtering Architecture

## Overview

This document defines the system architecture for the RSS News Filtering System. The system runs every 12 hours, fetches RSS articles published within the last 12 hours, deduplicates them using a local LLM (Ollama with embedding model), and sends an HTML email summary.

**Note:** For workflow details (agent coordination, step-by-step execution), see `workflow.md`.

## System Flow Diagram

```
                    +----------------+
                    |   Scheduler    |
                    | (cron/systemd) |
                    +-------+--------+
                            |
                            | triggers every 12h
                            v
+------------------+    +-------------------+    +------------------+
|  feedly_rss.opml | -> |  RSS Fetcher      | -> |  Article List    |
|  (feed sources)  |    |  (feedparser)     |    |  (raw articles)  |
+------------------+    +-------------------+    +--------+---------+
                                                         |
                                                         | filter: last 12h
                                                         v
                                               +-------------------+
                                               | Time Filter       |
                                               | (published_date   |
                                               |  >= now - 12h)    |
                                               +---------+---------+
                                                         |
                                                         v
                                               +-------------------+
                                               |  LLM Deduplicator |
                                               |  (Ollama/Llama)   |
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
                                               | Recipients:       |
                                               | - Personal Gmail  |
                                               | - Company Email   |
                                               +-------------------+
```

## Components

### 1. Scheduler

**Responsibility:** Trigger the pipeline every 12 hours

**Options:**
- **cron** (recommended for simplicity)
- **systemd timer**
- **Python scheduler** (APScheduler)

**cron example:**
```cron
0 6,18 * * * /path/to/venv/bin/python /path/to/main.py >> /path/to/logs/news_filter.log 2>&1
```

**Execution times:** 06:00 and 18:00 daily

---

### 2. RSS Fetcher

**Input:** `feedly_rss.opml`

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
@dataclass
class Article:
    title: str
    link: str
    published: datetime
    source: str
    category: str  # from OPML folder
```

---

### 3. Time Filter

**Input:** All fetched articles

**Output:** Articles published within the last 12 hours

**Logic:**
```python
cutoff = datetime.now(timezone.utc) - timedelta(hours=12)
recent_articles = [a for a in articles if a.published >= cutoff]
```

**Edge cases:**
- Articles without `published_date`: **exclude** and log WARNING
- Timezone handling: normalize all dates to UTC
- **Timezone-naive dates:** If `published_parsed` lacks timezone info, assume UTC and log WARNING

**State Persistence (Failure Recovery):**
- Save timestamp of last successful run to `state/last_run.json`
- On next run, use `max(last_run_timestamp, now - 12h)` as cutoff
- This ensures no articles are missed if a run fails

---

### 4. LLM Deduplicator (Ollama)

**Input:** List of recent articles

**Output:** Deduplicated list of unique articles

**Purpose:** Remove duplicate/similar articles that cover the same news story

**Recommended Model:** `nomic-embed-text` (dedicated embedding model, faster and more efficient than general-purpose LLMs like `llama3.2`)

**Two-Stage Deduplication Process:**

#### Stage 1: Exact URL Deduplication
- Remove articles with identical `link` values
- Keep the most recent one (by `published` date)

#### Stage 2: Title Similarity Clustering
1. Generate embeddings for each article title using Ollama
2. Use **Agglomerative Clustering** with cosine distance
3. Distance threshold: configurable (default: 0.15, equivalent to 0.85 similarity)
4. Select one representative from each cluster:
   - Prefer articles from `preferred_sources` (if configured)
   - Otherwise, select the most recent article

**Ollama Integration:**
```python
import requests
from sklearn.cluster import AgglomerativeClustering

def get_embedding(text: str, model: str = "nomic-embed-text") -> list[float]:
    response = requests.post(
        "http://localhost:11434/api/embeddings",
        json={"model": model, "prompt": text}
    )
    return response.json()["embedding"]

def deduplicate_articles(articles: list[Article], config: dict) -> list[Article]:
    # Stage 1: Remove exact URL duplicates
    url_seen = {}
    for a in articles:
        if a.link not in url_seen or a.published > url_seen[a.link].published:
            url_seen[a.link] = a
    unique_by_url = list(url_seen.values())

    # Stage 2: Cluster by title similarity
    embeddings = [get_embedding(a.title, config["embedding_model"]) for a in unique_by_url]
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=1 - config["dedup_threshold"],
        metric="cosine",
        linkage="average"
    )
    labels = clustering.fit_predict(embeddings)

    # Select representative from each cluster
    return select_representatives(unique_by_url, labels, config.get("preferred_sources", []))
```

**Deduplication Criteria:**
- Same URL (exact match) → Stage 1
- Similar title (>85% cosine similarity) → Stage 2

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

## Configuration File

**File:** `config.yaml`

**Configuration Loading Priority:**
1. Load `.env` file into environment variables
2. Read `config.yaml`
3. Environment variables override YAML values (where `${VAR}` syntax is used)

```yaml
# RSS Feed Configuration
feeds:
  opml_file: "feedly_rss.opml"
  timeout_seconds: 10
  skip_feedly_proxy: true

# Schedule Configuration
schedule:
  interval_hours: 12
  time_window_hours: 12  # Fetch articles from last N hours

# LLM Configuration (Ollama)
llm:
  base_url: "${OLLAMA_BASE_URL}"
  embedding_model: "nomic-embed-text"  # Recommended: dedicated embedding model
  dedup_threshold: 0.85  # Cosine similarity threshold for deduplication

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
```

**Environment Variables (`.env`):**
```env
GMAIL_ADDRESS=your.email@gmail.com
GMAIL_APP_PASSWORD=your-app-password-here
PERSONAL_EMAIL=your.email@gmail.com
COMPANY_EMAIL=your.email@company.com
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Error Handling Strategy

| Component | Error Type | Action |
|-----------|-----------|--------|
| RSS Fetcher | Feed timeout | Log warning, continue with other feeds |
| RSS Fetcher | Feed parse error | Log warning, continue |
| RSS Fetcher | No articles found | Log info, continue |
| Time Filter | Invalid date | Skip article, log warning |
| LLM Deduplicator | Ollama unavailable | Fallback: skip dedup, use all articles |
| LLM Deduplicator | Model not found | Fallback or exit with error |
| HTML Builder | Template error | Exit with error |
| Email Sender | Auth failure | Exit with error, send alert if possible |
| Email Sender | Network error | Retry 3 times with exponential backoff |

---

## Logging

**Log Levels:**
- `INFO`: Normal operation (fetching feeds, article counts)
- `WARNING`: Recoverable errors (feed timeout, skipped articles)
- `ERROR`: Critical failures (email auth, Ollama down)

**Log Format:**
```
2026-02-17 06:00:01 INFO  [RSS Fetcher] Starting fetch cycle
2026-02-17 06:00:01 INFO  [RSS Fetcher] Found 110 unique feeds in OPML
2026-02-17 06:00:05 WARN  [RSS Fetcher] Timeout: nitter.net/FirstSquawk/rss
2026-02-17 06:01:30 INFO  [RSS Fetcher] Fetched 450 articles from 95 feeds
2026-02-17 06:01:30 INFO  [Time Filter] 127 articles within last 12 hours
2026-02-17 06:01:35 INFO  [Deduplicator] Reduced to 89 unique articles
2026-02-17 06:01:36 INFO  [HTML Builder] Generated email (15KB)
2026-02-17 06:01:38 INFO  [Email Sender] Sent to 2 recipients
2026-02-17 06:01:38 INFO  [Main] Cycle completed successfully
```

---

## File Structure

```
news_filtering/
├── config.yaml              # Configuration
├── .env                     # Secrets (git-ignored)
├── .env.example             # Template for .env
├── feedly_rss.opml          # RSS feed sources
├── requirements.txt         # Python dependencies
│
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── rss_fetcher.py       # OPML parsing + RSS fetching
│   ├── time_filter.py       # Filter by publication date
│   ├── deduplicator.py      # LLM-based deduplication
│   ├── html_builder.py      # HTML email generation
│   ├── email_sender.py      # Gmail SMTP sending
│   └── config.py            # Configuration loading
│
├── templates/
│   └── email.html           # HTML email template (Jinja2)
│
├── state/                   # Runtime state (git-ignored)
│   └── last_run.json        # Timestamp of last successful run
│
├── output/                  # Generated HTML files (git-ignored)
├── logs/                    # Log files (git-ignored)
│
├── tests/
│   ├── test_rss_fetcher.py
│   ├── test_time_filter.py
│   ├── test_deduplicator.py
│   ├── test_html_builder.py
│   ├── test_email_sender.py
│   └── test_integration.py
│
├── agent_roles.md           # Agent role assignments
├── architecture.md          # This file (system architecture)
├── workflow.md              # Agent workflow definition
├── architecture_review.md   # Architecture review results
└── test_plan.md             # Test plan
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
requests>=2.28.0
pyyaml>=6.0
python-dotenv>=1.0.0
jinja2>=3.1.0
scikit-learn>=1.3.0
numpy>=1.24.0
```

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

3. **Verify Ollama is running:**
   ```bash
   ollama list
   # Should show available models including llama3.2
   ```

4. **Test the pipeline:**
   ```bash
   python src/main.py --dry-run
   ```

5. **Setup cron job:**
   ```bash
   crontab -e
   # Add: 0 6,18 * * * /path/to/venv/bin/python /path/to/src/main.py
   ```

