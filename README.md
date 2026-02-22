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

- Python 3.12+ (実行環境は Python 3.6+ 互換)
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

### 4. OPML ファイルの配置

RSS フィード一覧（OPMLファイル）をプロジェクトディレクトリに配置します。デフォルトでは `default_rss.opml` というファイル名が想定されています。

---

## 設定の詳細

`config.yaml` および `.env` でシステム全体の動作を詳細にカスタマイズできます。

### 1. RSS フィード設定 (`feeds`)

| 項目 | デフォルト | 説明 |
|---|---|---|
| `opml_file` | `default_rss.opml` | 読み込む OPML ファイルのパス。 |
| `timeout_seconds` | `10` | 1つのフィード取得のタイムアウト時間。 |
| `skip_feedly_proxy` | `true` | Feedly 独自のプロキシ URL をスキップするかどうか。 |

### 2. スケジュール設定 (`schedule`)

| 項目 | デフォルト | 説明 |
|---|---|---|
| `interval_hours` | `24` | 実行間隔（ドキュメント上の基準値）。 |
| `time_window_hours` | `24` | 取得対象とする記事の過去時間範囲。メール本文の「過去 XX 時間」の表示にも反映されます。 |

### 3. LLM/重複排除設定 (`llm`, `deduplication`)

| 項目 | デフォルト | 説明 |
|---|---|---|
| `llm.base_url` | `${OLLAMA_BASE_URL}` | Ollama API のエンドポイント。 |
| `llm.embedding_model` | `nomic-embed-text` | タイトル類似度計算に使用するモデル名。 |
| `llm.dedup_threshold` | `0.85` | 重複とみなす類似度の閾値 (0.0-1.0)。値が高いほど厳格（似ているものだけを重複とする）。 |
| `deduplication.preferred_sources` | (リスト) | 重複記事の中から1つ選ぶ際、優先的に採用するソース名のリスト（例: Reuters, Bloomberg等）。 |

### 4. メール送信設定 (`email`)

| 項目 | デフォルト | 説明 |
|---|---|---|
| `smtp_server` | `smtp.gmail.com` | SMTP サーバのアドレス。 |
| `smtp_port` | `587` | SMTP ポート番号。 |
| `sender_email` | `${GMAIL_ADDRESS}` | 送信元アドレス。 |
| `sender_password` | `${GMAIL_APP_PASSWORD}` | Gmail のアプリパスワード。 |
| `recipients` | (リスト) | 受信者のメールアドレスリスト。 |
| `max_articles_per_email` | `200` | 1通のメールに含める最大記事数。超過分は切り捨てられ、フッターに通知が表示されます。 |

### 5. 出力・状態管理 (`output`)

| 項目 | デフォルト | 説明 |
|---|---|---|
| `save_html` | `true` | 生成された HTML をファイルとして保存するかどうか。 |
| `html_dir` | `./output` | HTML ファイルの保存先ディレクトリ。 |
| `log_file` | `./logs/news_filter.log` | 実行ログの出力先。 |
| `state_file` | `./state/last_run.json` | 最終実行時刻を記録するファイル（重複取得防止用）。 |

### 6. システム動作 (`system`)

| 項目 | デフォルト | 説明 |
|---|---|---|
| `poweroff_after_run` | `false` | `true` に設定すると、全処理が正常完了した 5 分後に PC を自動シャットダウンします。 |

---

## 自動シャットダウン機能

`config.yaml` の `system.poweroff_after_run` を `true` に設定すると、正常にメール送信（またはドライランでのHTML保存）が完了した後、5分間の待機を経て `poweroff` コマンドを実行します。

- 待機時間（5分）の間に `Ctrl+C` を押すことで、シャットダウンをキャンセルできます。

### OS側の設定（パスワードなしでの実行許可）

スクリプトから自動でシャットダウンを行うには、`poweroff` コマンドをパスワードなしで実行できるように設定する必要があります。以下の手順で設定を行ってください。

1. ターミナルで `sudo visudo` コマンドを実行します。
2. ファイルの末尾に以下の一行を追記します（`username` はご自身のPCのユーザー名に変えてください）。

```bash
username ALL=(ALL) NOPASSWD: /usr/sbin/poweroff
```

※ 環境によってはパスが `/sbin/poweroff` の場合があります。`which poweroff` コマンドで正しいパスを確認してください。

## 障害時の動作

Ollama が停止している、または指定されたモデルが見つからない場合、システムは以下の動作を行います：

1.  処理を中断し、エラー内容を記載した通知メールを全宛先に送信します。
2.  エラーログを記録し、非ゼロの終了コードで終了します。
3.  `state/last_run.json` は更新されません。これにより、次回実行時に今回の時間ウィンドウの記事が再処理されます。

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

## プロジェクト構成

```
news_filtering/
├── design/
│   ├── architecture.md       # システムアーキテクチャ設計
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

## 重複排除の精度検証

記事タイトルの類似度に基づく重複排除の精度を調整するために、以下の手順でカスタムデータを注入して検証できます。

### 1. テストデータの準備

`tests/test_data_template.py` ファイルを編集します。

### 2. テストデータ注入の有効化

`src/deduplicator.py` ファイルの `deduplicate_articles` 関数の冒頭にあるコメントアウトを解除します。

### 3. 類似度閾値の調整

`config.yaml` の `llm.dedup_threshold` の値を調整して実行・確認を繰り返します。
