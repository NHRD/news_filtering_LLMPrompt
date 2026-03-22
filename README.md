# RSS News Filtering System

RSS フィードから過去24時間以内の記事を取得し、Gemini CLI によるタイトル類似度クラスタリングで重複排除を行い、英語タイトルを日本語に翻訳してから HTML ダイジェストメールを Gmail で送信するシステム。

## 処理フロー

```
OPML (フィード一覧)
  → RSS 取得 (feedparser)
  → 時間フィルタ (過去24時間)
  → 重複排除 (URL完全一致 + Gemini CLI によるタイトルクラスタリング)
  → 翻訳 (Gemini CLI による英語→日本語タイトル翻訳)
  → 番号付け (カテゴリ別アルファベット順・日付降順で連番付与)
  → HTML メール生成 (Jinja2)
  → インデックス保存 (JSON ファイル)
  → Gmail SMTP 送信
```

## 必要なもの

- Python 3.12+ (実行環境は Python 3.6+ 互換)
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) (重複排除・翻訳用)
- Gmail アカウント (2段階認証 + アプリパスワード)
- RSS フィード一覧 (OPML ファイル)

## セットアップ

### 1. Python 環境の構築

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Gemini CLI のセットアップ

```bash
# Gemini CLI をインストール
npm install -g @google/gemini-cli

# 認証
gemini auth login
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
OPML_FILE=default_rss.opml
```

### 4. OPML ファイルの配置

RSS フィード一覧（OPMLファイル）をプロジェクトディレクトリに配置します。デフォルトでは `default_rss.opml` というファイル名が想定されています。

---

## 設定の詳細

`config.yaml` および `.env` でシステム全体の動作を詳細にカスタマイズできます。

### 1. RSS フィード設定 (`feeds`)

| 項目 | デフォルト | 説明 |
|---|---|---|
| `opml_file` | `${OPML_FILE}` (or `default_rss.opml`) | 読み込む OPML ファイルのパス。 |
| `timeout_seconds` | `10` | 1つのフィード取得のタイムアウト時間。 |
| `skip_feedly_proxy` | `true` | Feedly 独自のプロキシ URL をスキップするかどうか。 |

### 2. スケジュール設定 (`schedule`)

| 項目 | デフォルト | 説明 |
|---|---|---|
| `interval_hours` | `24` | 実行間隔（ドキュメント上の基準値）。 |
| `time_window_hours` | `24` | 取得対象とする記事の過去時間範囲。メール本文の「過去 XX 時間」の表示にも反映されます。 |

### 3. Gemini/重複排除設定 (`gemini`, `deduplication`)

| 項目 | デフォルト | 説明 |
|---|---|---|
| `gemini.model` | `gemini-2.0-flash` | 重複排除・翻訳に使用する Gemini モデル名。 |
| `gemini.dedup_batch_size` | `80` | 1回の Gemini 呼び出しで処理する記事数の上限。記事数がこれを超えると複数回に分割して呼び出される。 |
| `deduplication.preferred_sources` | (リスト) | 重複記事の中から1つ選ぶ際、優先的に採用するソース名のリスト（例: Reuters, Bloomberg等）。 |
| `deduplication.on_dedup_failure` | `send_anyway` | Gemini 呼び出し失敗時の動作。`send_anyway`: URL重複排除のみの結果でメール送信。`abort`: パイプラインを中断してエラーメールを送信。 |

### 4. 翻訳設定 (`translation`)

| 項目 | デフォルト | 説明 |
|---|---|---|
| `translation.enabled` | `true` | 翻訳機能の ON/OFF。`false` にすると英語タイトルのままメールを生成する。 |
| `translation.batch_size` | `80` | 1回の Gemini 呼び出しで翻訳する記事数の上限。 |
| `translation.on_translate_failure` | `skip` | 翻訳失敗時の動作。`skip`: 元の英語タイトルをそのまま使用。`fail`: パイプラインを中断してエラーを返す。 |

### 5. メール送信設定 (`email`)

| 項目 | デフォルト | 説明 |
|---|---|---|
| `smtp_server` | `smtp.gmail.com` | SMTP サーバのアドレス。 |
| `smtp_port` | `587` | SMTP ポート番号。 |
| `sender_email` | `${GMAIL_ADDRESS}` | 送信元アドレス。 |
| `sender_password` | `${GMAIL_APP_PASSWORD}` | Gmail のアプリパスワード。 |
| `recipients` | (リスト) | 受信者のメールアドレスリスト。 |
| `max_articles_per_email` | `200` | 1通のメールに含める最大記事数。超過分は切り捨てられ、フッターに通知が表示されます。 |

### 6. 出力・状態管理 (`output`)

| 項目 | デフォルト | 説明 |
|---|---|---|
| `save_html` | `true` | 生成された HTML をファイルとして保存するかどうか。 |
| `html_dir` | `./output` | HTML ファイルの保存先ディレクトリ。 |
| `log_file` | `./logs/news_filter.log` | 実行ログの出力先。 |
| `state_file` | `./state/last_run.json` | 最終実行時刻を記録するファイル（重複取得防止用）。 |

### 7. インデックス保存設定 (`index`)

| 項目 | デフォルト | 説明 |
|---|---|---|
| `index.save_index` | `true` | 記事一覧を JSON インデックスファイルとして保存するかどうか。 |
| `index.index_dir` | `./output` | JSON インデックスの保存先ディレクトリ。 |
| `index.max_files` | `3` | 保持するインデックスファイルの最大数。超過した古いファイルは FIFO で自動削除される。 |

### 8. システム動作 (`system`)

| 項目 | デフォルト | 説明 |
|---|---|---|
| `system.poweroff_after_run` | `false` | `true` に設定すると、全処理が正常完了した 3 分後に PC を自動シャットダウンします。 |

---

## 自動シャットダウン機能
config.yaml の system.poweroff_after_run を`true`に設定すると正常にメール送信が完了した後3分間の待機を経てシャットダウンコマンドを実行します。
待機時間（3分）の間に Ctrl+C を押すことで、シャットダウンをキャンセルできます。

### OS側の設定（重要：パスワードなしでの実行許可）
Pythonスクリプト（特に venv 環境）から`sudo`経由で電源を切る場合、OS側のセキュリティ設定(sudoers)を正しく構成する必要があります。
設定の記述場所やコマンドのパスが異なると、パスワードを要求されて処理が失敗します。
ターミナルで`sudo visudo`コマンドを実行します。
**ファイルの最下行（重要）**に以下を追記します。
```bash
# username はご自身のユーザー名に書き換えてください
username ALL=(ALL) NOPASSWD: /usr/bin/systemctl poweroff, /usr/bin/systemctl
```
※ sudoers は下の行の設定が上の設定を上書きするため、必ず %sudo などのグループ設定よりも後に記述してください。

### 設定の反映確認
設定保存後、以下のコマンドを実行してパスワードを聞かれずにヘルプ画面が表示されれば設定完了です。

```bash
sudo -n /usr/bin/systemctl poweroff --help
```

## 障害時の動作

Gemini CLI の呼び出しが失敗した場合、`deduplication.on_dedup_failure` の設定に応じて以下のいずれかの動作を行います：

- `send_anyway`（デフォルト）: URL重複排除のみの結果（Stage 1）でメール送信を続行します。
- `abort`: 処理を中断し、エラー内容を記載した通知メールを全宛先に送信します。エラーログを記録し、非ゼロの終了コードで終了します。`state/last_run.json` は更新されないため、次回実行時に今回の時間ウィンドウの記事が再処理されます。

翻訳が失敗した場合は、`translation.on_translate_failure` の設定に応じて動作します：

- `skip`（デフォルト）: 翻訳できなかった記事は英語タイトルのままメールを送信します。
- `fail`: パイプラインを中断して非ゼロの終了コードで終了します。

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
│   ├── deduplicator.py       # 2段階重複排除 (URL + Gemini CLI タイトルクラスタリング)
│   ├── translator.py         # Gemini CLI による英語→日本語タイトル翻訳
│   ├── numbering.py          # カテゴリ別・日付降順での記事連番付与
│   ├── html_builder.py       # HTML メール生成
│   ├── index_writer.py       # JSON インデックスファイル保存 (FIFO rotation)
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

### 3. バッチサイズの調整

`config.yaml` の `gemini.dedup_batch_size` の値を調整して実行・確認を繰り返します。
