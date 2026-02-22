# RSS News Filtering System

RSS フィードから過去24時間以内の記事を取得し、Ollama による類似記事の重複排除を行い、カテゴリ別の HTML ダイジェストメールを Gmail で送信するシステム。

## 処理フロー

```
OPML (フィード一覧)
  → RSS 取得 (feedparser)
  → 時間フィルタ (過去24時間)
  → 重複排除 (URL完全一致 + Ollama embedding による類似度クラスタリング)
  → HTML メール生成 (Jinja2)
  → Gmail SMTP 送信
```

## 必要なもの

- Python 3.12+
- [Ollama](https://ollama.com/) (重複排除用の embedding モデル)
- Gmail アカウント (2段階認証 + アプリパスワード)
- RSS フィード一覧 (OPML ファイル)

## セットアップ

### 1. Python 環境の構築

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Ollama のセットアップ

```bash
# Ollama をインストール後、embedding モデルを取得
ollama pull nomic-embed-text
```

### 3. 環境変数の設定

```bash
cp .env.example .env
```

`.env` を編集して以下を設定:

```env
GMAIL_ADDRESS=your.email@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
PERSONAL_EMAIL=your.email@gmail.com
COMPANY_EMAIL=your.email@company.com
OLLAMA_BASE_URL=http://localhost:11434
```

Gmail アプリパスワードの取得方法:
1. Google アカウントで2段階認証を有効化
2. https://myaccount.google.com/apppasswords にアクセス
3. アプリ名を入力して生成

### 4. OPML ファイルの配置

Feedly などからエクスポートした OPML ファイルを `feedly_rss.opml` として配置。

### 5. 設定のカスタマイズ (任意)

`config.yaml` で各種パラメータを変更可能:

| 設定 | デフォルト | 説明 |
|---|---|---|
| `schedule.time_window_hours` | 24 | 取得する記事の時間範囲 (時間) |
| `llm.dedup_threshold` | 0.85 | 類似度の閾値 (0.0-1.0) |
| `email.max_articles_per_email` | 200 | 1通あたりの最大記事数 |
| `deduplication.on_dedup_failure` | send_anyway | Ollama 障害時の動作 (`send_anyway` / `fail`) |
| `deduplication.preferred_sources` | Reuters等 | 重複時に優先するソース |

## 使い方

### 通常実行 (メール送信あり)

```bash
python -m src.main
```

### ドライラン (メール送信なし、HTML ファイルのみ保存)

```bash
python -m src.main --dry-run
```

### フェッチのみ (重複排除・メール送信なし)

```bash
python -m src.main --fetch-only
```

### 強制実行 (前回実行時刻を無視)

```bash
python -m src.main --force
```

### オプションの組み合わせ

```bash
# 初回実行: 過去24時間の全記事を取得してHTMLだけ確認
python -m src.main --dry-run --force

# 設定ファイルを指定
python -m src.main --config /path/to/config.yaml
```

## 定期実行 (cron)

毎日 6:00 に実行する例:

```bash
crontab -e
```

```cron
0 6 * * * cd /path/to/news_filtering && /path/to/venv/bin/python -m src.main >> /dev/null 2>&1
```

## 出力

| 出力先 | 内容 |
|---|---|
| `output/news_digest_*.html` | 生成された HTML メール |
| `logs/news_filter.log` | 実行ログ (10MB x 5ファイルでローテーション) |
| `state/last_run.json` | 最終実行時刻 (障害復旧用) |

## テスト

```bash
pip install pytest pytest-cov

# 全テスト実行
pytest tests/ -v

# カバレッジ付き
pytest tests/ --cov=src --cov-report=term-missing
```

## プロジェクト構成

```
news_filtering/
├── src/
│   ├── __init__.py          # Article データクラス
│   ├── main.py              # エントリーポイント (CLI)
│   ├── config.py            # 設定読み込み
│   ├── rss_fetcher.py       # OPML 解析 + RSS 取得
│   ├── time_filter.py       # 時間フィルタリング
│   ├── deduplicator.py      # 2段階重複排除 (URL + Ollama embedding)
│   ├── html_builder.py      # HTML メール生成
│   └── email_sender.py      # Gmail SMTP 送信
├── templates/
│   └── email.html           # メールテンプレート (Jinja2)
├── tests/                   # テストコード
├── config.yaml              # 設定ファイル
├── .env                     # 認証情報 (git 管理外)
├── .env.example             # .env のテンプレート
├── feedly_rss.opml          # RSS フィード一覧
└── requirements.txt         # Python 依存関係
```
