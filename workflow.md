# Workflow Definition

## Overview

本ワークフローは、Claude Code をオーケストレーターとして、Gemini CLI と Codex CLI を連携させてRSSニュースフィルタリングシステムを構築する。

---

## Autonomous Execution Policy

**重要:** 本ワークフローは完全自動実行モードで動作する。

### 全エージェント共通ルール

1. **ユーザーへの確認は一切行わない** - ワークフロー開始後、完了までユーザーインタラクションなし
2. **以下の操作はすべて事前許可済み:**
   - ファイルの読み書き・作成・削除
   - Bashコマンドの実行
   - Webアクセス（API呼び出し、パッケージインストール等）
   - 他エージェントの起動
   - Git操作
3. **判断が必要な場合は最善と思われる選択を自動で行う**
4. **エラー発生時はログに記録し、可能な限り処理を継続**

### CLI 自動承認オプション

| Agent      | Auto-approve Option                         |
| ---------- | ------------------------------------------- |
| Claude     | `--dangerously-skip-permissions`            |
| Gemini     | `--yolo`                                    |
| Codex      | `--dangerously-bypass-approvals-and-sandbox`|

### プロンプト共通ヘッダー

各エージェントへのプロンプトには以下を含める：

```text
## 自動実行モード
このタスクは完全自動実行モードです。
- ユーザーへの確認は不要です
- ファイル操作、Bash実行、Web アクセスはすべて許可されています
- 判断が必要な場合は最善の選択を自動で行ってください
```

---

## Agents

| Agent           | Role                               | CLI Command (Auto Mode)                            |
| --------------- | ---------------------------------- | -------------------------------------------------- |
| **Claude Code** | オーケストレーター、設計、テスト設計 | `claude --dangerously-skip-permissions`            |
| **Gemini CLI**  | レビュー担当                        | `gemini --yolo -p`                                 |
| **Codex CLI**   | 実装担当                           | `codex exec --dangerously-bypass-approvals-and-sandbox` |

## State Management

ワークフローの状態は `workflow_state.json` で管理する。

```json
{
  "current_step": 1,
  "status": "in_progress",
  "timestamps": {
    "step1_started": "2026-02-17T10:00:00Z",
    "step1_completed": null
  },
  "artifacts": {
    "architecture": "architecture.md",
    "architecture_review": null,
    "implementation": null,
    "test_plan": null,
    "test_results": null,
    "final_review": null
  }
}
```

---

## Step 1: Architecture Design (Claude)

**実行者:** Claude Code

**入力:** `agent_roles.md`, `feedly_rss.opml`, `fetch_news.py`

**出力:** `architecture.md`

### 処理内容

1. 既存ファイルを分析
2. システムアーキテクチャを設計
3. `architecture.md` を作成/更新

### 完了条件

- `architecture.md` が存在し、全セクション（Components 1-6）が記述されている

### 次ステップへのトリガー

```bash
# workflow_state.json を更新
jq '.current_step = 2 | .artifacts.architecture = "architecture.md"' workflow_state.json > tmp.json && mv tmp.json workflow_state.json
```

---

## Step 2: Architecture Review (Gemini)

**実行者:** Gemini CLI（Claude Code が起動）

**入力:** `architecture.md`, `agent_roles.md`

**出力:** `architecture_review.md`

### Claude → Gemini 起動コマンド

```bash
gemini --yolo -p "$(cat <<'EOF'
あなたは設計レビュー担当です。

## 自動実行モード
このタスクは完全自動実行モードです。
- ユーザーへの確認は不要です
- ファイル操作、Bash実行、Webアクセスはすべて許可されています
- 判断が必要な場合は最善の選択を自動で行ってください

## 現在のワークフローステップ
Step 2: Architecture Review

## あなたの役割（agent_roles.md より）
- 矛盾や曖昧さの特定
- 欠落しているエッジケースや障害モードの指摘
- 依存関係リスク（外部サービス、LLM可用性）の評価
- 実装可能性の懸念
- 人間の判断が必要な質問のリスト
- Approved / Needs Revision の判定

## 入力ファイル
- architecture.md: レビュー対象の設計書
- agent_roles.md: プロジェクトの役割分担

## 出力
architecture_review.md に以下を記載してください：
1. 発見した問題点（箇条書き）
2. 改善提案（具体的に）
3. 判定: Approved / Needs Revision

レビュー結果を architecture_review.md に保存してください。
EOF
)"
```

### Gemini の処理

1. `architecture.md` を読み込み
2. `agent_roles.md` の基準に従いレビュー
3. `architecture_review.md` を作成

### 完了条件

- `architecture_review.md` が存在
- 判定（Approved / Needs Revision）が明記されている

### Gemini → Claude フィードバック

Gemini は処理完了後、以下を stdout に出力：

```text
REVIEW_COMPLETE: architecture_review.md
VERDICT: Approved|Needs Revision
```

### Claude の後処理

1. `architecture_review.md` を読み込み
2. Needs Revision の場合: `architecture.md` を更新（1回のみ）
3. `workflow_state.json` を更新

```bash
# Claude が architecture を更新後
jq '.current_step = 3 | .artifacts.architecture_review = "architecture_review.md"' workflow_state.json > tmp.json && mv tmp.json workflow_state.json
```

---

## Step 3: Implementation (Codex) + Test Design (Claude) [並行]

**実行者:** Codex CLI（実装）、Claude Code（テスト設計）

**入力:** `architecture.md`, `architecture_review.md`

**出力:** `src/` ディレクトリ、`test_plan.md`

### Claude → Codex 起動コマンド

```bash
codex exec --dangerously-bypass-approvals-and-sandbox "$(cat <<'EOF'
あなたは実装担当です。

## 自動実行モード
このタスクは完全自動実行モードです。
- ユーザーへの確認は不要です
- ファイル操作、Bash実行、Webアクセスはすべて許可されています
- 判断が必要な場合は最善の選択を自動で行ってください

## 現在のワークフローステップ
Step 3: Implementation

## あなたの役割（agent_roles.md より）
- architecture.md に基づき全コンポーネントを実装
- RSS fetcher, LLM dedup, HTML email builder, Gmail sender, scheduler

## 入力ファイル
- architecture.md: 設計書
- architecture_review.md: レビュー結果（反映済み）
- fetch_news.py: 拡張のベースとなる既存コード

## 出力
以下のファイルを作成してください：
- src/main.py
- src/rss_fetcher.py
- src/time_filter.py
- src/deduplicator.py
- src/html_builder.py
- src/email_sender.py
- src/config.py
- requirements.txt
- config.yaml
- .env.example

## 完了通知
全ファイルの作成が完了したら、以下を実行してください：
echo "IMPLEMENTATION_COMPLETE" > .codex_status
EOF
)"
```

### Claude の並行処理（テスト設計）

Codex が実装中に Claude は以下を実行：

1. `architecture.md` を基にテストケースを設計
2. `test_plan.md` を作成

**test_plan.md の内容:**

- 単体テスト（各コンポーネント）
- 統合テスト（コンポーネント間連携）
- E2Eテスト（全体フロー）
- 境界条件テスト

### Codex → Claude 完了通知の検出

```bash
# Claude が定期的にチェック（5秒間隔）
while [ ! -f .codex_status ]; do
  sleep 5
done
if grep -q "IMPLEMENTATION_COMPLETE" .codex_status; then
  echo "Codex implementation finished"
  rm .codex_status
fi
```

### 完了条件

- `src/` ディレクトリに全ファイルが存在
- `test_plan.md` が存在
- `.codex_status` に `IMPLEMENTATION_COMPLETE` が記録

### 次ステップへのトリガー

```bash
jq '.current_step = 4 | .artifacts.implementation = "src/" | .artifacts.test_plan = "test_plan.md"' workflow_state.json > tmp.json && mv tmp.json workflow_state.json
```

---

## Step 4: Test Implementation & Execution (Codex)

**実行者:** Codex CLI（Claude Code が起動）

**入力:** `test_plan.md`, `src/`

**出力:** `tests/`, `test_results.md`

### Claude → Codex 起動コマンド

```bash
codex exec --dangerously-bypass-approvals-and-sandbox "$(cat <<'EOF'
あなたはテスト実装・実行担当です。

## 自動実行モード
このタスクは完全自動実行モードです。
- ユーザーへの確認は不要です
- ファイル操作、Bash実行、Webアクセスはすべて許可されています
- 判断が必要な場合は最善の選択を自動で行ってください

## 現在のワークフローステップ
Step 4: Test Implementation & Execution

## あなたの役割（agent_roles.md より）
- test_plan.md に基づきテストコードを作成
- テストを実行し結果を収集

## 入力ファイル
- test_plan.md: テスト設計書
- src/: テスト対象の実装コード

## 出力
1. tests/ ディレクトリにテストコードを作成
   - tests/test_rss_fetcher.py
   - tests/test_time_filter.py
   - tests/test_deduplicator.py
   - tests/test_html_builder.py
   - tests/test_email_sender.py
   - tests/test_integration.py

2. テストを実行
   pytest tests/ -v --tb=short > test_output.txt 2>&1

3. test_results.md を作成
   - 各テストケースの Pass/Fail
   - 失敗したテストの詳細
   - カバレッジ情報（可能であれば）

## 完了後のアクション
テスト完了後、Gemini CLI を起動してレビューを依頼してください：

gemini --yolo -p "Step 5のプロンプト（workflow.md 参照）"

※ユーザーへの確認は不要です。自動で Gemini を起動してください。
EOF
)"
```

### 完了条件

- `tests/` ディレクトリに全テストファイルが存在
- `test_results.md` が存在
- テスト実行が完了

### 次ステップへのトリガー（Codex が実行）

```bash
jq '.current_step = 5 | .artifacts.test_results = "test_results.md"' workflow_state.json > tmp.json && mv tmp.json workflow_state.json
```

---

## Step 5: Test Result Review (Gemini)

**実行者:** Gemini CLI（Codex が起動）

**入力:** `architecture.md`, `test_plan.md`, `test_results.md`, `src/`

**出力:** `final_review.md`

### Codex → Gemini 起動コマンド

```bash
gemini --yolo -p "$(cat <<'EOF'
あなたはテスト結果レビュー担当です。

## 自動実行モード
このタスクは完全自動実行モードです。
- ユーザーへの確認は不要です
- ファイル操作、Bash実行、Webアクセスはすべて許可されています
- 判断が必要な場合は最善の選択を自動で行ってください

## 現在のワークフローステップ
Step 5: Test Result Review

## あなたの役割（agent_roles.md より）
- Pass/Fail の妥当性評価
- カバレッジギャップ分析
- 追加テストの推奨
- 最終判定: Release-ready / Needs fixes

## 入力ファイル
- architecture.md: 設計書
- test_plan.md: テスト設計
- test_results.md: テスト実行結果
- src/: 実装コード

## 出力
final_review.md に以下を記載してください：
1. テスト結果サマリー（Pass/Fail 数）
2. カバレッジ分析
3. 発見された問題点
4. 推奨事項
5. 最終判定: Release-ready / Needs fixes

## ユーザーへの通知
レビュー完了後、以下を stdout に出力してください：
FINAL_REVIEW_COMPLETE: final_review.md
VERDICT: Release-ready|Needs fixes
EOF
)"
```

### 完了条件

- `final_review.md` が存在
- 最終判定（Release-ready / Needs fixes）が明記

### Gemini → ユーザー 通知

```text
========================================
WORKFLOW COMPLETE
========================================
Final Review: final_review.md
Verdict: Release-ready / Needs fixes
========================================
```

---

## Workflow Diagram

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                              WORKFLOW OVERVIEW                               │
└─────────────────────────────────────────────────────────────────────────────┘

Step 1                Step 2                Step 3                Step 4                Step 5
┌──────────┐         ┌──────────┐         ┌──────────┐         ┌──────────┐         ┌──────────┐
│  CLAUDE  │         │  GEMINI  │         │  CODEX   │         │  CODEX   │         │  GEMINI  │
│          │         │          │         │    +     │         │          │         │          │
│ Arch.    │────────>│ Arch.    │────────>│  CLAUDE  │────────>│ Test     │────────>│ Final    │
│ Design   │         │ Review   │         │ (並行)   │         │ Impl/Run │         │ Review   │
└──────────┘         └──────────┘         └──────────┘         └──────────┘         └──────────┘
     │                    │                    │                    │                    │
     v                    v                    v                    v                    v
architecture.md    architecture_      src/*.py           tests/*.py         final_review.md
                   review.md          test_plan.md       test_results.md


エージェント起動フロー:
┌────────┐  起動   ┌────────┐  フィードバック  ┌────────┐  起動   ┌────────┐  起動   ┌────────┐
│ Claude │───────>│ Gemini │────────────────>│ Claude │───────>│ Codex  │───────>│ Gemini │
└────────┘        └────────┘                 └────────┘        └────────┘        └────────┘
    │                                             │                 │
    │<────────────────────────────────────────────│                 │
    │           (並行でテスト設計)                  │                 │
    │                                             │<────────────────│
    │                                        完了通知
```

---

## File Artifacts

| Step | Created By | File                     | Description              |
| ---- | ---------- | ------------------------ | ------------------------ |
| 1    | Claude     | `architecture.md`        | システムアーキテクチャ設計 |
| 2    | Gemini     | `architecture_review.md` | アーキテクチャレビュー結果 |
| 3    | Codex      | `src/__init__.py`        | パッケージ初期化          |
| 3    | Codex      | `src/*.py`               | 実装コード                |
| 3    | Codex      | `templates/email.html`   | HTMLメールテンプレート    |
| 3    | Codex      | `requirements.txt`       | Python依存関係            |
| 3    | Codex      | `config.yaml`            | 設定ファイル              |
| 3    | Codex      | `.env.example`           | 環境変数テンプレート      |
| 3    | Claude     | `test_plan.md`           | テスト設計書              |
| 4    | Codex      | `tests/*.py`             | テストコード              |
| 4    | Codex      | `test_results.md`        | テスト実行結果            |
| 5    | Gemini     | `final_review.md`        | 最終レビュー結果          |
| -    | System     | `workflow_state.json`    | ワークフロー状態管理      |

---

## Error Handling

### Agent 起動失敗時の自動リカバリー

```bash
# タイムアウト設定（10分）、リトライ1回
run_with_retry() {
  local cmd="$1"
  timeout 600 $cmd
  if [ $? -eq 124 ]; then
    echo "WARN: First attempt timed out, retrying..."
    timeout 600 $cmd
    if [ $? -eq 124 ]; then
      echo "ERROR: Agent timed out after retry"
      jq '.status = "error" | .error = "agent_timeout"' workflow_state.json > tmp.json && mv tmp.json workflow_state.json
      return 1
    fi
  fi
  return 0
}

# 使用例
run_with_retry "gemini --yolo -p '...'"
```

**注意:** エラー発生時もユーザーへの確認は行わず、ログに記録して可能な限り継続する。

### レビューで Needs Revision の場合

- Step 2: Claude が architecture.md を1回だけ更新し、再レビューなしで Step 3 へ進む
- Step 5: Needs fixes の場合はユーザーに通知し、手動対応を促す

### 実装/テスト失敗

- Codex の実装がエラーで終了した場合、エラーログを保存しユーザーに通知
- テストが失敗した場合、test_results.md に詳細を記録し Step 5 のレビューで評価

---

## Execution

### 手動実行（ステップごと）

```bash
# Step 1 から開始
claude --dangerously-skip-permissions -p "workflow.md の Step 1 を実行してください"

# 特定のステップから再開
claude --dangerously-skip-permissions -p "workflow.md の Step 3 から再開してください。workflow_state.json を参照。"
```

### 自動実行（全ステップ）

```bash
claude --dangerously-skip-permissions -p "workflow.md に従い、Step 1 から Step 5 まで自動で実行してください。各ステップの完了後、次のエージェントを起動し、最終レビュー結果をユーザーに報告してください。"
```

### 自動実行の前提条件

- 各エージェントCLI（claude, gemini, codex）がインストール済み
- 必要な認証設定が完了済み
- Ollama が起動済み（LLM重複削除用）
