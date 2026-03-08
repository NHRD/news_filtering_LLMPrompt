# Black-box Test Plan

## 方針

- 実装の内部構造を参照せず、入力と出力の仕様のみに基づいてテストする
- 各コンポーネントを独立してテスト（ユニット）＋パイプライン全体のテスト（統合）
- テストデータはすべてモックまたはフィクスチャで用意し、実際のGmail送信・Gemini CLI呼び出しは行わない

---

## 1. RSS Fetcher

**入力:** OPMLファイルパス
**出力:** `Article` オブジェクトのリスト

| ID | テストパターン | 入力 | 期待出力 |
|----|---|---|---|
| RF-01 | 正常: 複数フィードを含む有効なOPML | 有効なOPMLファイル（3フィード、各5記事） | 15件のArticleリスト |
| RF-02 | 正常: FeedlyプロキシURLをスキップ | `https://feedly.com/web/...` を含むOPML | Feedlyプロキシ以外のフィードのみ取得 |
| RF-03 | 正常: 重複フィードURLを排除 | 同じフィードURLが2回出現するOPML | 重複なし、1回だけ取得 |
| RF-04 | 正常: フォルダ名がcategoryに設定される | OPMLのフォルダ名「Tech」 | Articleのcategoryが「Tech」 |
| RF-05 | 異常: OPMLが空 | 空のOPMLファイル | 空リスト（エラーなし） |
| RF-06 | 異常: 存在しないOPMLパス | 存在しないファイルパス | 例外またはエラーログ、空リスト |
| RF-07 | 異常: フィードがタイムアウト | タイムアウトするフィードURL（モック） | 当該フィードをスキップ、WARNINGログ、他フィードは正常取得 |
| RF-08 | 異常: フィードがHTTP 404 | 404を返すフィードURL（モック） | 当該フィードをスキップ、WARNINGログ |
| RF-09 | 異常: フィードのRSSが不正なXML | 破損したRSSレスポンス（モック） | 当該フィードをスキップ、WARNINGログ |
| RF-10 | 境界: published_dateが存在しない記事 | published_dateなしの記事を含むフィード | 当該記事を除外、WARNINGログ |
| RF-11 | 境界: タイムゾーン情報なしのpublished_date | タイムゾーンなし日時の記事 | UTCとみなして取得、WARNINGログ |
| RF-12 | 境界: 全フィードがエラー | すべてタイムアウトするOPML | 空リスト、WARNINGログ |
| RF-13 | 正常: RSS 2.0 と Atom 形式の混在 | RSS 2.0フィードとAtomフィードを含むOPML | 両形式から正しくtitle・link・publishedを抽出 <!-- ADDED: フィード形式の互換性確認 --> |
| RF-14 | 正常: HTTPリダイレクト(301/302)の発生 | リダイレクト先に有効なRSSがあるURL（モック） | リダイレクトを追跡して正常に記事を取得 <!-- ADDED: ネットワークの堅牢性確認 --> |

---

## 2. Time Filter

**入力:** Articleリスト + 設定（time_window_hours, state_file）
**出力:** カットオフ以降に公開されたArticleリスト

| ID | テストパターン | 入力 | 期待出力 |
|----|---|---|---|
| TF-01 | 正常: ウィンドウ内の記事のみ返す | now-12h, now-6h, now-1h の記事（window=24h） | 3件全部 |
| TF-02 | 正常: ウィンドウ外の記事を除外 | now-25h の記事（window=24h） | 0件 |
| TF-03 | 境界: カットオフ境界ちょうどの記事 | published == cutoff の記事 | 含まれる（>=） |
| TF-04 | 境界: カットオフより1秒前の記事 | published == cutoff - 1s | 除外される |
| TF-05 | 境界: state_fileなし（初回実行） | state_fileが存在しない | cutoff = now - 24h として処理 |
| TF-06 | 正常: state_fileあり（前回実行がウィンドウ内） | last_run = now-10h, window=24h | cutoff = now-10h（max(now-24h, last_run)を使用） <!-- FIXED: 判定ロジックを明示 --> |
| TF-07 | 正常: state_fileあり（前回実行がウィンドウ外） | last_run = now-30h, window=24h | cutoff = now-24h（max(now-24h, last_run)を使用） <!-- FIXED: 判定ロジックを明示 --> |
| TF-08 | 境界: 全記事がウィンドウ外 | now-48h の記事のみ | 空リスト |
| TF-09 | 境界: 空のArticleリスト | [] | [] |
| TF-10 | 境界: 異なるタイムゾーンの記事の比較 | 記事がJST 10:00（= UTC 01:00）、cutoffがUTC 00:30 | 正しくUTC換算してフィルタリング <!-- ADDED: タイムゾーン正規化の検証 --> |

---

## 3. Gemini Deduplicator

**入力:** Articleリスト + 設定（preferred_sources, dedup_batch_size, on_dedup_failure）
**出力:** 重複排除済みArticleリスト

### Stage 1: URL重複排除

| ID | テストパターン | 入力 | 期待出力 |
|----|---|---|---|
| DD-01 | 正常: 重複URLなし | URLがすべて異なる5記事 | 5件そのまま |
| DD-02 | 正常: URL重複あり | 同URLの記事が2件（公開日が異なる） | 新しい方の1件のみ |
| DD-03 | 境界: 全記事が同じURL | 同URL・異なる公開日の5記事 | 最新の1件のみ |
| DD-04 | 境界: 空リスト | [] | [] |

### Stage 2: Gemini CLIによるタイトル重複排除

| ID | テストパターン | 入力 | 期待出力 |
|----|---|---|---|
| DD-05 | 正常: 重複なし | 完全に異なるトピックの記事 | 全件返却 |
| DD-06 | 正常: 同一ニュースを別表現で報じた記事 | 「Fed利上げ25bp」「連邦準備制度0.25%引き上げ」（Geminiモック: 1件を返す） | 1件のみ |
| DD-07 | 正常: preferred_sourcesの記事を優先 | Reuters版(1)とその他版(2)が重複（Geminiモック: "1" を返す） | 1のみ保持 |
| DD-08 | 正常: preferred_sourcesが大文字小文字違い | 設定 "reuters"、記事source "Reuters" | 大文字小文字を無視して一致、優先される |
| DD-09 | 境界: 記事数がbatch_sizeちょうど | batch_size=80, 記事数=80 | バッチ分割なし、1回のGemini呼び出し |
| DD-10 | 境界: 記事数がbatch_sizeを超える | batch_size=80, 記事数=100 | 2バッチに分割してGeminiを呼び出し、結果をマージ |
| DD-11 | 境界: 記事数=1 | 1件のみ | そのまま1件返却（Gemini呼び出しなし） |
| DD-12 | 異常: Gemini CLI呼び出し失敗（send_anyway） | Geminiがexitcode=1を返す、on_dedup_failure=send_anyway | Stage1結果をそのまま返却、WARNINGログ |
| DD-13 | 異常: Gemini CLI呼び出し失敗（fail） | Geminiがexitcode=1を返す、on_dedup_failure=fail | SystemExit(1)、ERRORログ |
| DD-14 | 異常: Geminiの出力がパース不能 | Geminiが "sorry, I can't..." など無関係な文字列を返す（モック） | on_dedup_failureの動作を適用 |
| DD-15 | 異常: Geminiが範囲外インデックスを返す | Geminiが "1,99" を返す（記事数=5） | 99を無視して1のみ返却、WARNINGログ |
| DD-16 | 異常: Geminiがタイムアウト | Gemini呼び出しが設定秒数を超過（モック） | on_dedup_failureの動作を適用 |
| DD-17 | 異常: Geminiが空文字を返す | Geminiが何も返さない（モック） | on_dedup_failureの動作を適用 <!-- ADDED: 空レスポンスへの耐性 --> |
| DD-18 | 境界: 非常に長いタイトルを含む記事群 | 合計文字数がGeminiの入力上限付近 | エラーにならず、適切にバッチ分割またはトランケートして処理 <!-- ADDED: トークン制限付近の挙動確認 --> |

---

## 4. HTML Builder

**入力:** Articleリスト + 設定（max_articles_per_email）
**出力:** HTML文字列

| ID | テストパターン | 入力 | 期待出力 |
|----|---|---|---|
| HB-01 | 正常: 複数カテゴリの記事 | Tech 3件, Finance 2件 | カテゴリ別にグループ化されたHTML |
| HB-02 | 正常: カテゴリ内の記事が公開日降順 | 同カテゴリに古い順で渡した3記事 | HTMLでは新しい順に並ぶ |
| HB-03 | 正常: 日付フォーマット | published=2026-03-08 06:00:00 UTC | "2026-03-08 06:00 UTC" と表示 |
| HB-04 | 正常: タイトルとURLがHTMLに含まれる | title="Test", link="https://example.com" | aタグにtitle・href両方が含まれる |
| HB-05 | 境界: 空のArticleリスト | [] | "No articles found" メッセージを含むHTML |
| HB-06 | 境界: 記事数がmax_articles_per_emailを超える | max=5, 記事数=8 | 最新5件のみ表示、フッターに切り捨てメッセージ |
| HB-07 | 境界: 記事数=max_articles_per_email | max=5, 記事数=5 | 全5件表示、切り捨てメッセージなし |
| HB-08 | 正常: メール件名フォーマット | window_start=2026-03-07 06:00 UTC, 記事数=89 | "News Digest \| 89 articles \| 2026-03-07 06:00 UTC - 2026-03-08 06:00 UTC" |
| HB-09 | 境界: 特殊文字を含むタイトル | title="<script>alert(1)</script>" | HTMLエスケープされて表示（XSS対策） |

---

## 5. Email Sender

**入力:** HTML本文 + EmailConfig
**出力:** メール送信（副作用）

| ID | テストパターン | 入力 | 期待出力 |
|----|---|---|---|
| ES-01 | 正常: 送信成功 | 有効なEmailConfig（SMTPモック） | True返却、送信ログ |
| ES-02 | 異常: 認証失敗 | 無効なアプリパスワード（SMTPモック） | SystemExit、ERRORログ |
| ES-03 | 異常: 一時的なネットワークエラー → 3回リトライ後成功 | 1・2回目失敗、3回目成功（SMTPモック） | 送信成功、RETRYログ |
| ES-04 | 異常: 3回リトライしても失敗 | 3回ともネットワークエラー（SMTPモック） | SystemExit、ERRORログ |
| ES-05 | 正常: 複数宛先に送信 | recipients=["a@gmail.com", "b@company.com"] | 全宛先に送信される |

---

## 6. Integration（パイプライン全体）

**入力:** CLIオプション + 設定ファイル
**出力:** メール送信 or HTML保存 + state_file更新

| ID | テストパターン | 入力 | 期待出力 |
|----|---|---|---|
| IT-01 | 正常: フル実行成功 | 有効なOPML・Geminiモック・SMTPモック | メール送信、state_file更新 |
| IT-02 | 正常: --dry-run | --dry-runフラグ | HTMLファイル保存、メール未送信、state_file更新 |
| IT-03 | 正常: --fetch-only | --fetch-onlyフラグ | 記事取得のみ、重複排除・メール未送信、state_file未更新 |
| IT-04 | 正常: --force | last_run=now-1h、--forceフラグ | now-24hをcutoffとして使用（last_runを無視） |
| IT-05 | 異常: RSS取得で全フィードエラー | 全フィードがタイムアウト（モック） | 空リストで継続、"No articles found" メール送信、state_file更新 |
| IT-06 | 異常: Gemini失敗（send_anyway）でもメール送信 | Geminiがエラー（モック）、on_dedup_failure=send_anyway | 重複排除なしでメール送信、state_file更新 |
| IT-07 | 異常: Gemini失敗（fail）でパイプライン中断 | Geminiがエラー（モック）、on_dedup_failure=fail | SystemExit(1)、state_file未更新 |
| IT-08 | 異常: メール送信失敗 | SMTPがエラー（モック） | SystemExit、state_file未更新 |
| IT-09 | 異常: --dry-runでHTMLファイル保存失敗 | 書き込み権限なしのディレクトリ | SystemExit、state_file未更新 |
| IT-10 | 正常: poweroff_after_run=true | poweroff_after_run=true（poweroffコマンドはモック） | 成功後にpoweroffコマンド呼び出し |
| IT-11 | 異常: 必須環境変数の欠落 | .envが存在しない、またはGMAIL_ADDRESSが未設定 | エラーメッセージを出力してSystemExit <!-- ADDED: セットアップ不備の検知 --> |
| IT-12 | 異常: CLI引数の競合 | --dry-run と --fetch-only を同時に指定 | 定義された優先順位で動作、またはエラーメッセージを表示 <!-- ADDED: 引数の排他制御確認 --> |
