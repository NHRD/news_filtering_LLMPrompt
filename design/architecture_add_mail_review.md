# Architecture Review: Gmail Mailing List Integration

## 1. 発見した問題点・懸念点

### a. 重複排除ロジックの副作用 (Deduplicator)
現状の `src/deduplicator.py` の `_dedup_by_exact_url` は、`link` をキーとして辞書で管理しています。メーリングリストのメールで URL が抽出できなかった場合（`link=""`）、複数の異なるメールが「空文字列という同一 URL」として扱われ、最新の1件以外が Stage 1 で削除されてしまいます。

### b. IMAP 検索の効率性 (Main Pipeline)
`architecture_add_mail.md` の `run_pipeline` 擬似コードでは、`fetch_mail_articles` に `cutoff` 時間が渡されていません。IMAP サーバーから全件取得して Python 側でフィルタリングするのは非効率なため、IMAP の `SEARCH SINCE` コマンドを活用すべきです。

### c. メールのデコード処理 (Mail Fetcher)
RFC 2047 形式の Subject やマルチパート形式の本文（text/plain vs text/html）、エンコーディング（UTF-8, ISO-2022-JP等）の処理が複雑になりがちです。標準ライブラリ `email` を正しく組み合わせて使用する必要があります。

### d. 日付のタイムゾーン処理 (Mail Fetcher)
メールの `Date` ヘッダから取得した `published` 日時は、既存の `cutoff` (UTC) と比較可能なように、タイムゾーン情報を持つ (offset-aware) UTC `datetime` に変換する必要があります。

---

## 2. 改善提案（具体的修正指示）

AIエージェントが実装する際は、以下の点に留意して修正・実装を行ってください。

### Step 1: `src/deduplicator.py` の修正
`_dedup_by_exact_url` 関数を修正し、`link` が空文字列の場合は重複排除の対象外（常に保持）とするように変更してください。

```python
# 修正案
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

### Step 2: `src/config.py` の拡張
`architecture_add_mail.md` に記載された `MailingListEntry` および `MailFetchConfig` を追加し、`load_config` 関数内で `mailing_lists` セクションを読み込む処理を実装してください。`imap_user` と `imap_password` は既存の `email.sender_email` / `email.sender_password` から取得してください。

### Step 3: `src/mail_fetcher.py` の新規作成
以下の仕様で実装してください。
- **IMAP 接続**: `imaplib.IMAP4_SSL(host, port)` を使用。
- **検索**: `cutoff` 日時を `DD-Mon-YYYY` 形式に変換し、`SEARCH SINCE "..."` を使用。`match_by: from` の場合は `FROM "..."` を組み合わせる。
- **Subject**: `email.header.decode_header` を使用してデコード。
- **Date**: `email.utils.parsedate_to_datetime` を使用。
- **本文**: `email.message.Message.walk()` でパーツを走査。`text/html` を優先し、なければ `text/plain` を使用。
- **URL抽出**: 提案されている正規表現を使用。HTMLの場合はタグ等を除去したテキストから抽出するのが望ましいが、簡易的には生の本文から抽出でも可。

### Step 4: `src/main.py` の統合
`run_pipeline` 関数において、`filter_recent_articles` を呼び出す**前**に `fetch_mail_articles(config.mail_fetch, cutoff=...)` を呼び出すように変更してください。
※ `cutoff` は `load_last_run_timestamp` から算出される値を使用。

---

## 3. 判定

**判定: Approved (with comments)**

上記「2. 改善提案」の具体的修正を反映することを条件に、実装フェーズに進んでください。
特に `link=""` の重複排除漏れは、メーリングリスト統合において情報の欠落を招くため、必ず修正してください。
