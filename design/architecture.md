# RSS News Filtering Architecture

## Overview

This document defines the system architecture for the RSS News Filtering System. The system runs twice daily (08:00 and 20:00), fetches RSS articles published since the last run, deduplicates them using the Gemini CLI, translates titles to Japanese, builds a numbered HTML email and a JSON index file for downstream curation, and sends the HTML email summary.

**Note:** For workflow details (agent coordination, step-by-step execution), see `workflow.md`.

## System Flow Diagram

```
                    +----------------+
                    |   Scheduler    |
                    | (cron/systemd) |
                    | 08:00 / 20:00  |
                    +-------+--------+
                            |
                            v
+------------------+    +-------------------+    +------------------+
|  default_rss.opml| -> |  RSS Fetcher      | -> |  Article List    |
|  (feed sources)  |    |  (feedparser)     |    |  (raw articles)  |
+------------------+    +-------------------+    +--------+---------+
                                                         |
                                                         | filter: since last run
                                                         v
                                               +-------------------+
                                               | Time Filter       |
                                               | (published_date   |
                                               |  >= last_run)     |
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
                                               |   Translator      |
                                               | (Gemini CLI,      |
                                               |  EN -> JA titles) |
                                               +---------+---------+
                                                         |
                                                         v
                                               +-------------------+
                                               | Article Numbering |
                                               | (global seq. No.) |
                                               +---------+---------+
                                                         |
                                               +---------+---------+
                                               |                   |
                                               v                   v
                                    +------------------+  +------------------+
                                    |  HTML Builder    |  |  Index Writer    |
                                    | (No. + JA title  |  | (JSON, FIFO x3) |
                                    |  + URL, grouped) |  +--------+---------+
                                    +--------+---------+           |
                                             |                     | news_index_YYYYMMDD_AM|PM.json
                                             v                     v
                                    +-------------------+  +------------------+
                                    |  Email Sender     |  |  output/         |
                                    |  (Gmail SMTP)     |  |  (local storage) |
                                    +--------+----------+  +------------------+
                                             |
                                             v
                                    +-------------------+
                                    | Recipients:       |
                                    | - Personal Gmail  |
                                    | - Company Email   |
                                    +--------+----------+
                                             |
                                             v
                                    +-------------------+
                                    |  Auto Shutdown    |
                                    |  (Optional)       |
                                    +-------------------+
```

## Components

### 1. Scheduler

**Responsibility:** Trigger the pipeline twice daily at 08:00 and 20:00

**Options:**
- **cron** (recommended for simplicity)
- **systemd timer**

**cron example:**
```cron
0 8  * * * /path/to/venv/bin/python /path/to/main.py >> /path/to/logs/news_filter.log 2>&1
0 20 * * * /path/to/venv/bin/python /path/to/main.py >> /path/to/logs/news_filter.log 2>&1
```

**Execution times:** 08:00 (AM session) and 20:00 (PM session) daily

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
    title: str       # original title (English)
    link: str
    published: datetime
    source: str
    category: str    # from OPML folder
    title_ja: str = ""  # Japanese translation; empty until Translator step
```

<!-- DESIGN NOTE: NamedTuple default value compatibility
Python の NamedTuple では、デフォルト値を持つフィールドはデフォルト値なしのフィールドより後に配置しなければならない。
現在の定義ではデフォルト値なしフィールド (title, link, published, source, category) の後に `title_ja` を置いているため、
定義自体に問題はない。

ただし以下の互換性リスクに注意すること:
- 既存コードで位置引数コンストラクタ `Article(title, link, published, source, category)` を使っている場合:
  `title_ja` が末尾でデフォルト値を持つため、呼び出し側は変更不要。互換性あり。
- 既存コードで `Article(*values)` のようにアンパックしている場合:
  フィールド数が 5 → 6 に変わるため、アンパック元のシーケンスが 5 要素なら互換性あり。
  6 要素で `title_ja` を含むシーケンスを渡す場合も問題なし。
- `_replace()` / `_asdict()` は新フィールドを認識するため問題なし。

代替案 (より安全にしたい場合):
  `dataclass(frozen=True)` への移行を検討。`frozen=True` にすることで NamedTuple と同様のイミュータブル性を保ちつつ、
  フィールド追加時の互換性管理が容易になる。ただし現状の NamedTuple 定義で互換性リスクは低いため、
  既存コードが 5 引数の位置引数呼び出しのみであれば変更不要。
-->


---

### 3. Time Filter

**Input:** All fetched articles

**Output:** Articles published within the last 24 hours (or since last successful run)

**Logic:**
```python
cutoff = compute_cutoff(time_window_hours, last_run)
# cutoff = max(last_run_timestamp, now - time_window_hours)
recent_articles = [a for a in articles if a.published >= cutoff]
```
<!-- FIXED: Clarified that the cutoff logic prevents both missing news during short outages and overwhelming users with old news during long outages. -->

**Edge cases:**
- Articles without `published_date`: **exclude** and log WARNING
- Timezone handling: normalize all dates to UTC
- **Timezone-naive dates:** If `published_parsed` lacks timezone info, assume UTC and log WARNING
- **First Run:** If `state_file` is missing, `last_run_timestamp` is assumed to be `now - 24h`. <!-- FIXED: Defined behavior for the initial execution. -->

**State Persistence (Failure Recovery):**
- Save timestamp of last successful run to `state/last_run.json`.
- **Update Timing:** The `state/last_run.json` file is updated with the current timestamp **only after** the entire pipeline has completed successfully. A successful completion means either:
  - The news summary email has been sent without errors.
  - The `--dry-run` option was used and the HTML file was saved successfully.
- If any step in the pipeline fails (including network errors, LLM failures, etc.), the state file **will not** be updated.
- On the next run, the system will use the older timestamp from the state file, ensuring that any articles from the failed run's time window are re-processed and not missed (up to a 24h limit).

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

#### Stage 1: Exact URL Deduplication（URL正規化付き）
- `link` からクエリ文字列（`?` 以降）とフラグメント（`#` 以降）を除去して正規化し、正規化後のURLが一致する記事を重複とみなす
- Keep the most recent one (by `published` date)

**背景（2026-03-18 修正）:** WSJ などのメディアは同一記事を複数のRSSフィードに配信する際、
トラッキング用のクエリパラメータ（例: `?mod=rss_markets_main`, `?mod=pls_whats_news_us_business_f`）
を付与する。これによりURLが異なってみえるため、修正前は Stage 1 を通過して重複として残っていた。
クエリパラメータは記事の同一性判定に無関係なため、正規化してから比較することで Stage 1 で確実に除去できる。

#### Stage 2: Title Deduplication via Gemini CLI
1. Sort articles by `title` alphabetically before batching. <!-- FIXED: Added sorting to ensure similar titles are more likely to appear in the same batch. -->
2. Build a numbered list of `"N. [title] (source)"` from Stage 1 output
3. If article count exceeds `gemini.dedup_batch_size` (default: 80), split into batches and process each batch independently
   - **バッチ内の番号は 1 から始まるローカル番号を使う。** Gemini への入力・出力はバッチごとに独立した 1 始まり番号とし、
     返却インデックスを元の articles スライス上のオフセットに変換して残す記事を決定する。
     バッチまたぎの重複は検出できない（アーキテクチャ上の制約）。タイトルアルファベット順ソートにより
     類似記事が同じバッチに収まる可能性を高めることで緩和する。
4. Pass the list to Gemini CLI with the following prompt:
   ```
   以下はニュース記事のタイトル一覧です（番号. タイトル (ソース) の形式）。
   同じニュースを報じている記事をグループ化し、各グループから1記事だけ残してください。
   残す記事の選択基準（優先順）:
     1. preferred_sources（Reuters, Bloomberg, TechCrunch, The Verge）に含まれるソースがあればその中で最新のもの
     2. なければグループ内で最新のもの
   出力は残す記事の番号のみをカンマ区切りで返してください。説明文は不要です。
   例: 1,3,5,8,12
   ```
5. Parse the comma-separated index list from Gemini's output
6. Return the articles at the specified indices

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
- **Preferred Sources Match:** Matching of `preferred_sources` is case-insensitive. <!-- FIXED: Clarified matching logic for sources. -->

---

### 5. Translator

**Input:** Deduplicated articles (List[Article] with `title_ja=""`)

**Output:** List[Article] with `title_ja` filled in (Japanese translation of `title`)

**Purpose:** Translate English article titles to Japanese to reduce user screening load

**Process:**
1. Build a numbered list: `"N. [title]"` from input articles
2. If article count exceeds `translation.batch_size` (default: 80), split into batches and process independently
   - **バッチ内の番号は 1 から始まるローカル番号を使う。** <!-- NOTE: config パスは translation.batch_size。dedup の gemini.dedup_batch_size とは別キー。 --> バッチごとに 1 始まりの番号リストを Gemini に渡し、
     返却された番号をバッチ内オフセットに変換して元の articles 全体のインデックスに対応付ける。
     バッチ境界をまたいだ番号の混同が起きないよう、各バッチのパース結果は独立して処理すること。
3. Pass to Gemini CLI with the following prompt:
   ```
   以下の英語ニュースタイトルを日本語に翻訳してください。
   出力は「番号. 翻訳テキスト」の形式で1行ずつ返してください。説明文は不要です。
   例:
   1. 連邦準備制度、政策金利を0.25%引き上げ
   2. Appleが次世代チップを発表
   ```
4. Parse output: each line `"N. <translation>"` → map index N to translated title
5. Return articles with `title_ja` set; if parse fails for a specific item, fall back to original `title`

**Output Parsing Detail:**
Gemini の出力を行単位でパースする際、以下のケースを明示的に処理すること:

```
出力フォーマット: "N. 翻訳テキスト"  (N は 1 始まりの整数)

正常ケース:
  行が正規表現 r"^(\d+)\.\s+(.+)$" にマッチする → N を記事インデックスとして title_ja に格納

異常ケース (いずれも「該当記事のみ original title へフォールバック + WARNING ログ」):
  (a) 番号なし行:  "翻訳テキストだけ" や "- 翻訳テキスト" など数字+ピリオドで始まらない行
        → その行全体を無視し、対応する no の記事を original title へフォールバック
  (b) 範囲外番号:  N < 1 または N > len(articles) のケース
        → その行を無視し、対応する no の記事を original title へフォールバック
  (c) 番号重複:    同じ N が複数行に現れた場合
        → 後出し優先 (最後に出現した行の翻訳を採用) し WARNING ログを出力
  (d) 全行パース失敗または空出力:
        → on_translate_failure の設定に従う (skip: 全記事を original title, fail: パイプライン中断)

実装例:
  parsed = {}
  for line in output.splitlines():
      m = re.match(r"^(\d+)\.\s+(.+)$", line.strip())
      if not m:
          continue
      n = int(m.group(1))
      if 1 <= n <= len(articles):
          parsed[n] = m.group(2).strip()
  if not parsed:
      # 全行パース失敗 → on_translate_failure に従う
      ...
  for i, article in enumerate(articles):
      title_ja = parsed.get(i + 1, article.title)  # フォールバック: original title
      result.append(article._replace(title_ja=title_ja))
```

**Failure Behavior:**
- **Gemini CLI unavailable / non-zero exit:** Controlled by `translation.on_translate_failure` config setting:
  - `skip` (default): Use original English title as `title_ja`. Log WARNING. Pipeline continues.
  - `fail`: Abort pipeline with exit code 1. Log ERROR.
- **Partial parse failure (individual line):** Fall back to original English title for that article. Log WARNING.
- **Out-of-range number:** Ignore the line, fall back to original title for that index. Log WARNING.
- **Duplicate number:** Accept the last occurrence, log WARNING.
- **All lines failed to parse / empty output:** Treat as Gemini unavailable; apply `on_translate_failure` behavior.

**CLI Integration:**
```python
result = subprocess.run(
    ["gemini", "-p", prompt],
    capture_output=True, text=True, timeout=120
)
```

---

### 6. Article Numbering

**Input:** Translated articles (List[Article])

**Output:** List of `NumberedArticle` with global sequential `no` field

**Purpose:** Assign a stable sequential number to each article that is consistent between the HTML email and the JSON index, enabling downstream curation by number reference.

**Data Structure:**
```python
class NumberedArticle(NamedTuple):
    no: int
    article: Article
```

**Numbering Logic:**
1. Group articles by category (categories sorted alphabetically)
2. Within each category, sort by `published` date descending (newest first)
3. Assign sequential integers starting at 1, incrementing across all categories top-to-bottom

**Invariant:** The same numbered list is passed to both `HTML Builder` and `Index Writer`, guaranteeing that No. in the email matches No. in the JSON index.

<!-- DESIGN NOTE: HTML Builder は受け取った NumberedArticle のリストをソートし直してはならない。
numbering.py が確定させたカテゴリ順・記事順・番号を壊さないよう、HTML Builder の _group_articles() は
「既に付与済みの no の順番を保持したままカテゴリでグルーピングするだけ」で済む。
具体的には: itertools.groupby(numbered_articles, key=lambda na: na.article.category) のように
「ソート済み前提のグルーピング」を使い、各カテゴリ内での並び替えは行わないこと。
これにより「Article Numbering 後に再ソートして番号がずれる」問題を回避できる。
もし HTML Builder 側でソートが必要な局面が生じた場合は numbering.py の責務を拡張し、
HTML Builder はソートを一切行わないという分担を維持すること。
-->

---

### 7. HTML Builder

**Input:** List[NumberedArticle]

**Output:** HTML email body

**Changes from previous version:**
- Added `no` column on the left side of each article row
- Displays `title_ja` as the primary title with `title` (original) shown as subtitle or tooltip
- Numbers are pre-assigned and passed in from Article Numbering step

**Template Structure (key changes):**
```html
<style>
    .article-no { font-size: 1em; font-weight: bold; color: #555;
                  min-width: 2.5em; text-align: right; padding-right: 10px; }
    .article-title-ja { font-weight: bold; margin-bottom: 2px; }
    .article-title-en { font-size: 0.85em; color: #888; margin-bottom: 4px; }
    /* existing styles remain */
</style>

<!-- Article row layout -->
<div class="article" style="display:flex; align-items:flex-start;">
    <div class="article-no">{{ no }}.</div>
    <div style="flex:1;">
        <div class="article-title-ja">
            <a href="{{ link }}" class="article-link">{{ title_ja }}</a>
        </div>
        <div class="article-title-en">{{ title }}</div>
        <div class="article-meta">{{ source }} | {{ published }}</div>
    </div>
</div>
```

**Max Articles Handling:**
- To prevent overly large emails, the number of articles is limited by the `max_articles_per_email` setting in `config.yaml`.
- **適用タイミング:** Truncation は Article Numbering の**前**に行う。
  具体的には Translator の出力リスト (List[Article]) を `published` 降順でソートし、
  上位 `max_articles_per_email` 件に絞ってから numbering.py に渡す。
  これにより番号 1 始まりの連番が最大 `max_articles_per_email` 内に収まる。
- **Index Writer との整合:** Truncation 後に numbering.py が付与した番号が JSON インデックスにも
  そのまま記録されるため、番号の一貫性が保たれる。
- When truncation occurs, a notification will be added to the email's footer. For example: "Showing the 200 most recent articles out of 250 found."
- **v2.0 テスト状況:** Truncation→Numbering の順序制約の明示的なユニットテストは v2.0 では未実装（次バージョン推奨）。IT-005-1〜3 で間接的に動作を確認。

**Date Formatting:**
- All dates displayed in the email are formatted as `YYYY-MM-DD HH:MM UTC` by the HTML Builder using `strftime('%Y-%m-%d %H:%M UTC')`.

**Empty Article List:**
- When no articles remain after filtering/dedup, render a "No articles found" message instead of empty content.

**Grouping:**
- Group articles by OPML category (e.g., Tech news, Finance, General)
- Within each category, articles are already sorted by publication date (newest first) by the Article Numbering step
- **重要: HTML Builder はグルーピングのみを行い、カテゴリ内・カテゴリ間のいかなる再ソートも行わないこと。**
  Article Numbering が確定させた `no` の順序を変えると、JSON インデックスの番号と不一致が生じる。
  `_group_articles()` は `no` の昇順を保ったままカテゴリで分割するだけとし、
  ソートロジックは numbering.py に集約する。

**Email Subject Line:**
- Format: `News Digest | [AM|PM] | [article_count] articles | [window_start] - [window_end]`
- Example: `News Digest | AM | 89 articles | 2026-03-11 08:00 JST - 2026-03-11 20:00 JST`
- **タイムゾーン:** 件名の日付・時刻はすべて JST（UTC+9）の配信日ベースで表示する。内部処理は UTC で行うが、ユーザーへの表示は JST に変換してフォーマットする。

---

### 8. Index Writer

**Input:** List[NumberedArticle], session label (`"AM"` or `"PM"`)

**Output:** `news_index_YYYYMMDD_AM.json` or `news_index_YYYYMMDD_PM.json` saved to `output/`

**Purpose:** Persist the numbered article list for downstream curation (Claude Code News skill reads this file to look up articles by number)

**Session Label Determination:**
- `run_hour = datetime.now().hour`
- `session = "AM" if run_hour < 12 else "PM"`

**File Format:**
```json
{
  "session": "AM",
  "run_time": "2026-03-11T08:00:48+09:00",
  "article_count": 87,
  "articles": [
    {
      "no": 1,
      "title_ja": "連邦準備制度、政策金利を0.25%引き上げ",
      "title_en": "Federal Reserve raises rates by 25 basis points",
      "link": "https://...",
      "source": "Reuters",
      "category": "Finance",
      "published": "2026-03-11T06:30:00+00:00"
    },
    ...
  ]
}
```

**FIFO Management:**
- After saving the new index file, scan `index_dir` for files matching `news_index_*.json`
- Sort by filename (lexicographic = chronological given `YYYYMMDD_AM|PM` naming)
- If count > `index.max_files` (default: 3), delete oldest files until count == `max_files`
- This ensures the last 3 sessions (≈ yesterday PM + today AM + today PM) are always retained

<!-- DESIGN NOTE: ファイル名ソートの AM/PM 辞書順の検証
`news_index_20260311_AM.json` と `news_index_20260311_PM.json` を辞書順で比較すると:
  'A' (ASCII 65) < 'P' (ASCII 80)
のため AM < PM となり、AM が「古い」セッションとして正しく先頭に並ぶ。
ファイル名の YYYYMMDD 部分が同一の場合も AM が PM より前になるため、FIFO の削除ロジックは正しく動作する。

Glob パターン `news_index_*.json` について:
`.json` 拡張子で終わるファイルのみにマッチするため、同一ディレクトリ内の `.html` ファイルには
マッチしない。HTML ファイルと JSON ファイルが `output/` に混在する構成でも誤削除は起きない。
-->

<!-- DESIGN NOTE: index_dir と html_dir の関係
デフォルトでは `index.index_dir: "./output"` と `output.html_dir: "./output"` が同一ディレクトリを指し、
HTML ファイルと JSON インデックスファイルが混在する。これは意図した設計であり、
FIFO の Glob `news_index_*.json` が HTML ファイルにマッチしないため運用上の問題はない。
`index_dir` が存在しない場合、index_writer.py は `os.makedirs(index_dir, exist_ok=True)` で
ディレクトリを自動作成する。自動作成に失敗した場合は LOG ERROR を出力してパイプラインは継続する。
-->

**Failure Behavior:**
- File I/O error: Log ERROR, do NOT abort pipeline (email still sent)

---

### 9. Email Sender

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
- Use `smtplib` and `email.mime` modules.
- **Retries:** In case of temporary network errors, retry up to 3 times with exponential backoff (e.g., 5s, 15s, 45s). <!-- FIXED: Explicitly defined retry logic. -->

---

### 10. Auto Shutdown

**Responsibility:** Shut down the system after successful completion

**Logic:**
1. Wait for 3 minutes (180 seconds) to allow logs to be flushed and give user a chance to cancel.
2. Execute `sudo -n /usr/bin/systemctl poweroff` command. <!-- FIXED: Updated to modern systemd command for better compatibility. -->

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
  model: "gemini-2.0-flash"  # Model passed to gemini CLI
  dedup_batch_size: 80  # Max articles per Gemini dedup request

# Deduplication Settings
deduplication:
  on_dedup_failure: "send_anyway"  # Options: send_anyway, fail
  preferred_sources:
    - "Reuters"
    - "Bloomberg"
    - "TechCrunch"
    - "The Verge"

# Translation Settings
translation:
  enabled: true
  batch_size: 80               # Max articles per Gemini translation request
  on_translate_failure: "skip" # Options: skip (use original title), fail

# Index Settings
index:
  save_index: true
  index_dir: "./output"        # Same directory as HTML output
  max_files: 3                 # FIFO: keep last N index files

# Email Configuration
email:
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  sender_email: "${GMAIL_ADDRESS}"
  sender_password: "${GMAIL_APP_PASSWORD}"
  recipients:
    - "${PERSONAL_EMAIL}"
    - "${COMPANY_EMAIL}"
  max_articles_per_email: 200

# Output Configuration
output:
  save_html: true
  html_dir: "./output"
  log_file: "./logs/news_filter.log"
  state_file: "./state/last_run.json"

# System Configuration
system:
  poweroff_after_run: false
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
| Translator | Gemini CLI unavailable / error | Configurable: use original title (`skip`) or abort (`fail`) |
| Translator | Partial parse failure (single line) | Fall back to original title for that article, log warning |
| Translator | Out-of-range number in output | Ignore that line, fall back to original title for that index, log warning |
| Translator | Duplicate number in output | Accept last occurrence, log warning |
| Translator | All lines failed to parse / empty output | Apply `on_translate_failure` behavior |
| Index Writer | File I/O error | Log ERROR, pipeline continues (email still sent) |
| HTML Builder | Template error | Exit with error |
| Email Sender | Auth failure | Exit with error |
| Email Sender | Network error | Retry 3 times with exponential backoff |

---

## Logging

**Log Levels:**
- `INFO`: Normal operation (fetching feeds, article counts)
- `WARNING`: Recoverable errors (feed timeout, skipped articles)
- `ERROR`: Critical failures (pipeline aborts)
- `CRITICAL`: Configuration errors requiring human intervention

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
│   ├── architecture.md        # システムアーキテクチャ設計 (This file)
│   ├── architecture_review.md # 設計レビュー結果
│   └── review_artifact/       # 実行後の評価資料
├── session_summaries/
│   └── session_summary_*.md   # 毎セッションの作業記録
├── src/
│   ├── __init__.py            # Article / NumberedArticle データクラス
│   ├── main.py                # エントリーポイント (CLI)
│   ├── config.py              # 設定読み込み (TranslationConfig, IndexConfig 追加)
│   ├── rss_fetcher.py         # OPML 解析 + RSS 取得
│   ├── time_filter.py         # 時間フィルタリング + 状態管理
│   ├── deduplicator.py        # URL重複排除 + Gemini CLI重複排除
│   ├── translator.py          # Gemini CLI による英→日タイトル翻訳 (NEW)
│   ├── numbering.py           # グローバル通し番号付与 (NEW)
│   ├── html_builder.py        # HTML メール生成 (No.列 + 日本語タイトル追加)
│   ├── index_writer.py        # JSON インデックス保存 + FIFO管理 (NEW)
│   └── email_sender.py        # Gmail SMTP 送信
├── templates/
│   ├── email.html             # HTML メールテンプレート (Jinja2)
│   └── error.html             # エラー通知テンプレート (Jinja2)
├── state/                     # Runtime state (git-ignored)
│   └── last_run.json          # 最終実行時刻
├── output/                    # Generated HTML files (git-ignored)
├── logs/                      # Log files (git-ignored)
├── tests/
│   └── test_*.py              # ユニットテスト・統合テスト
├── config.yaml                # 設定ファイル
├── .env                       # 認証情報 (git 管理外)
├── .env.example               # .env のテンプレート
├── default_rss.opml           # RSS フィード一覧
├── workflow.md                # ワークフロー定義
└── requirements.txt           # Python 依存関係
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
