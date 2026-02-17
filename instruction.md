# Instruction: Fetch 100 News Titles and Links from Feedly RSS Feeds

## Goal

Write a Python script that reads an OPML file exported from Feedly, parses the RSS feed URLs, fetches articles from those feeds, and outputs a list of 100 news article titles and their links (sorted by newest first).

## Overview

Since the Feedly API is restricted to Enterprise accounts, this approach uses OPML export to obtain the user's RSS feed list, then fetches articles directly from each RSS feed using `feedparser`.

## Prerequisites

- Python 3.9+
- A Feedly account (any plan)
- An OPML file exported from Feedly (already provided)

## OPML File

- **Filename:** `feedly-ca53bc95-9ca8-4579-a877-542cfb958671-2026-02-17.opml`
- **Format:** OPML 1.0 (XML)

### Data Structure

The OPML file has the following hierarchy:

```xml
<opml version="1.0">
  <head>
    <title>Naohisa subscriptions in feedly Cloud</title>
  </head>
  <body>
    <!-- Level 1: Category (folder) -->
    <outline text="Tech news" title="Tech news">
      <!-- Level 2: Individual feed (type="rss") -->
      <outline type="rss"
               text="Feed Display Name"
               title="Feed Display Name"
               xmlUrl="https://example.com/feed"
               htmlUrl="https://example.com"/>
    </outline>
  </body>
</opml>
```

### Categories and Feed Count

| Category | Feed Count | Description |
|---|---|---|
| **Tech news** | 31 | Autonomous vehicles, AI, EVs, automotive industry |
| **sub** | 54 | Finance, macro economics, market news, tech media |
| **Finance** | 29 | Markets, central banks, investment analysis |
| **Total** | **114** | (some feeds are duplicated across categories) |

### Key Attributes per Feed Entry

| Attribute | Required | Description | Example |
|---|---|---|---|
| `type` | Yes | Always `"rss"` for feed entries | `"rss"` |
| `text` | Yes | Display name of the feed | `"TechCrunch"` |
| `title` | Yes | Same as `text` in most cases | `"TechCrunch"` |
| `xmlUrl` | Yes | **The RSS feed URL to fetch** | `"https://techcrunch.com/feed/"` |
| `htmlUrl` | Yes | The website URL (not used for fetching) | `"https://techcrunch.com/"` |

### Important Notes on Feed URLs

Some `xmlUrl` values point to Feedly's internal proxy rather than direct RSS URLs:

- `https://feedly.com/web/...` — Feedly-proxied feeds (e.g., Ledge.ai, Substack). These will **not** work with `feedparser` directly. Skip them with a warning.
- `https://nitter.net/...` / `https://nitter.it/...` — Nitter RSS proxies for Twitter/X accounts. These may be unreliable or down.
- `https://feedproxy.feedly.com/...` — Feedly feed proxy. May or may not resolve.
- Standard RSS URLs (majority) — These work directly with `feedparser`.

### Parsing Logic

To extract feed URLs from the OPML:

1. Parse the XML with `xml.etree.ElementTree`.
2. Find all `<outline>` elements where `type="rss"`.
3. Extract the `xmlUrl` attribute from each matching element.
4. Extract the `text` attribute as the feed name (for logging).
5. **Skip** entries where `xmlUrl` starts with `https://feedly.com/web/` (Feedly proxy, not fetchable).
6. Deduplicate by `xmlUrl` (some feeds appear in multiple categories).

## Project Setup

Create the following files in the project directory:

```
feedly-ca53bc95-9ca8-4579-a877-542cfb958671-2026-02-17.opml  # Already provided
requirements.txt  # Dependencies
fetch_news.py     # Main script
```

### `requirements.txt`

```
feedparser
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Implementation (`fetch_news.py`)

The script should perform the following operations in order:

### 1. Parse the OPML File

- Use `xml.etree.ElementTree` to parse the OPML file.
- Find all `<outline type="rss">` elements (at any depth).
- Extract `xmlUrl` and `text` from each.
- Skip entries where `xmlUrl` starts with `https://feedly.com/web/`.
- Deduplicate by `xmlUrl`.
- Print the total number of feeds to fetch (expected: ~110 unique feeds).

### 2. Fetch Articles from Each Feed

- Iterate over the deduplicated feed URLs.
- Use `feedparser.parse(url)` to fetch and parse each RSS feed.
- Set a socket timeout of 10 seconds before fetching (`import socket; socket.setdefaulttimeout(10)`).
- Pass a User-Agent header to avoid being blocked: `feedparser.parse(url, request_headers={'User-Agent': 'Mozilla/5.0'})`.
- From each feed's `entries`, extract:
  - `entry.title` — the article title (string)
  - `entry.link` — the article URL (string)
  - `entry.published_parsed` or `entry.updated_parsed` — publication date (`time.struct_time` or `None`)
- Collect all entries into a single list.
- If a feed fails (network error, parse error, empty), log a warning with the feed name and URL, then continue.
- Print progress (e.g., `"[15/110] Fetching: TechCrunch..."`).

### 3. Sort and Select Top 100

- Sort all collected entries by publication date, newest first.
- Entries without a date should be placed at the end.
- Select the top 100 entries.

### 4. Output the Results

Print the results to stdout in the following format:

```
1. Article Title Here
   https://example.com/article-url

2. Another Article Title
   https://example.com/another-url

...
```

Also save the results to a file called `news_list.txt` in the same format.

## Error Handling

| Scenario | Action |
|---|---|
| OPML file not found | Print error with the expected filename and exit |
| OPML has no feeds | Print "No feeds found in OPML file." and exit |
| Feed URL starts with `https://feedly.com/web/` | Skip with info log |
| Individual feed timeout/error | Log warning (e.g., `"[WARN] Failed to fetch: FeedName (url)"`) and continue |
| No articles collected | Print "No articles found across all feeds." and exit |

## Verification

After implementation, run the script and verify:

1. The OPML file is parsed correctly and ~110 unique feed URLs are extracted.
2. Feedly proxy URLs are skipped.
3. Articles are fetched from multiple feeds with progress output.
4. Failed feeds are logged but do not crash the script.
5. Up to 100 articles are returned, sorted by newest first.
6. Each article has a title and a link.
7. The output is saved to `news_list.txt`.
