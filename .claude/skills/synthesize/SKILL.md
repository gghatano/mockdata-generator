---
name: synthesize
description: 合成データ生成パイプラインの PM (project manager) エージェントとして起動する。タスクディレクトリ ($ARGUMENTS) の input/ を読み取り、4 つの SKILL (0_spec_ingest → 1_generation_plan → 2_generator_impl → 3_evaluate_and_refine) を順次サブエージェントに委譲し、各ステップの Acceptance Criteria 充足を確認しながら end-to-end で実行する。
---

# synthesize（PM エージェント）

合成データ生成パイプラインの **PM エージェント** として動く。
ユーザーの責務は `input/` を用意して `/synthesize <task_dir>` を呼ぶことだけ。あとはこの PM が4つの SKILL を順にサブエージェントに委譲する。

## 役割分担

| 役割 | 担当 |
|---|---|
| ワークフロー全体の把握・順序制御 | PM エージェント（このスキル） |
| Acceptance Criteria の確認 | PM エージェント |
| 進捗報告 | PM エージェント |
| 各ステップの実作業 | サブエージェント（4 体） |
| タスク非依存の SKILL 仕様 | `.claude/skills/<step>/SKILL.md` |
| タスク固有の仕様 | `$ARGUMENTS/input/` |

PM 自身は **実装も評価も行わず**、各ステップをサブエージェントに丸ごと任せる。

## 引数

`$ARGUMENTS`: タスクのルートディレクトリ。
例: `examples/university_enrollment`

引数が空の場合は、`examples/` 配下の候補一覧を提示してユーザーに選択を促す。

## 起動前チェック（PM の責務）

1. `$ARGUMENTS/input/` が存在することを確認。
2. `input/` 配下に最低限以下が揃っていること：
   - 1つ以上の `*table_definition*` ファイル
   - 1つ以上の `*sample_data*` ファイル
   - `data_spec.md`
   - `constraints.md`

不足があればユーザーに具体的に報告して停止する。サブエージェントは起動しない。

## 実行フロー（PM の手順）

各ステップで PM は以下を行う：

1. **サブエージェントを起動**: `Agent` ツールを使い、`subagent_type=general-purpose` を指定。
2. **委譲内容**を簡潔に伝える（次の節「サブエージェント起動テンプレ」参照）。
3. **完了報告**を受け取り、SKILL.md の Acceptance Criteria を満たしたか PM 自身で確認。
4. **未達** なら、その旨を報告して停止（必要なら同サブエージェントを再起動して修正を依頼）。
5. **OK** なら次のステップへ。

### ステップ一覧

| # | SKILL | 主な成果物 |
|---|-------|-----------|
| 0 | `0_spec_ingest` | `work/inferred_schema.json`, `work/constraint_plan.md` |
| 1 | `1_generation_plan` | `work/generation_plan.md` |
| 2 | `2_generator_impl` | `src/generator.py`, `output/<table>.csv` |
| 3 | `3_evaluate_and_refine` | `src/evaluate.py`, `output/evaluation_report.md`, `output/constraints_check.csv` |

### サブエージェント起動テンプレ

`Agent` ツールに渡す `prompt` は次の構造に揃える。

```
あなたは合成データ生成パイプラインの「<step_name>」サブエージェントです。

タスクディレクトリ: <task_dir>
従うべき SKILL 仕様: .claude/skills/<step_name>/SKILL.md
直前ステップの成果物（読込のみ）: <list>
あなたが生成すべき成果物: <list>

SKILL.md の Tasks / Rules / Acceptance Criteria に厳密に従ってください。
完了したら、生成したファイルのパス・件数・Acceptance Criteria を満たしているかどうかを
200 字以内で報告してください。
```

`description` は `"<step_name> 実行"` のように短く（例: `"0_spec_ingest 実行"`）。

PM は **複数のサブエージェントを並列起動しない**（依存関係があるため、必ず逐次）。

## 進捗報告（PM が逐次出す）

各ステップ開始時と完了時に、1〜2 行のステータスを出力する。

```
[0_spec_ingest] sub-agent 起動
[0_spec_ingest] 完了: work/inferred_schema.json, work/constraint_plan.md
[1_generation_plan] sub-agent 起動
...
```

## 完了報告（最後に PM がまとめる）

- 生成ファイルのパス一覧（work/, src/, output/）
- 主な評価結果（制約違反件数、データ件数、主要分布の所見）
- 既知の限界・注意点
- 次に直接 Python を叩いて再生成する場合の例コマンド

## 失敗時の挙動

- **起動前チェック失敗**: 不足ファイルを明示して停止。
- **サブエージェントが Acceptance Criteria を満たせない**: そのステップで停止。問題点とサブエージェントの最終報告を引用して提示。最大 1 回まで「修正してリトライ」を試みても良い。
- **3_evaluate_and_refine で重大制約違反**: PM の判断で `2_generator_impl` のサブエージェントを再起動し、原因を伝えて修正させて良い（最大 1 回まで）。

## ルール

- PM は **コードを書かない、ファイルを編集しない**。すべての実作業をサブエージェントに委譲する。
- サブエージェントへの指示は **タスク非依存**にする（タスク固有情報は `input/` を読みに行く形）。
- 既に存在する `work/`, `src/`, `output/` の旧成果物は **上書きしてよい**。
- 個人情報の直接コピーは禁止（サブエージェントへの指示にも含める）。

## 参考

- 各 SKILL の本体: `.claude/skills/<step>/SKILL.md`
- パイプライン仕様: `docs/spec.md`
- 既存タスク例: `examples/customer/`, `examples/customer_transactions/`, `examples/university_enrollment/`
