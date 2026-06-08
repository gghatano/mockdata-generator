---
name: synthesize
description: 合成データ生成パイプラインの PM (project manager) エージェントとして起動する。必要に応じて原資料から input/ を作成し、5 つの SKILL (0_input_prepare → 1_spec_ingest → 2_generation_plan → 3_generator_impl → 4_evaluate_and_refine) を順次サブエージェントに委譲し、各ステップの Acceptance Criteria 充足を確認しながら end-to-end で実行する。
---

# synthesize（PM エージェント）

合成データ生成パイプラインの **PM エージェント** として動く。
ユーザーの責務はタスクディレクトリを用意して `/synthesize <task_dir>` を呼ぶことだけ。`input/` が未整備なら原資料から作成し、整備済みならそのまま後続ステップへ進む。

## 役割分担

| 役割 | 担当 |
|---|---|
| ワークフロー全体の把握・順序制御 | PM エージェント（このスキル） |
| Acceptance Criteria の確認 | PM エージェント |
| 進捗報告 | PM エージェント |
| 各ステップの実作業 | サブエージェント（最大 5 体） |
| タスク非依存の SKILL 仕様 | `.agents/skills/<step>/SKILL.md` |
| タスク固有の原資料・仕様 | `$ARGUMENTS` 配下の原資料と `$ARGUMENTS/input/` |

PM 自身は **実装も評価も行わず**、各ステップをサブエージェントに丸ごと任せる。

## 引数

`$ARGUMENTS`: タスクのルートディレクトリ。
例: `examples/university_enrollment`

引数が空の場合は、`examples/` 配下の候補一覧を提示してユーザーに選択を促す。

## 起動前チェック（PM の責務）

1. `$ARGUMENTS` が存在することを確認。
2. `$ARGUMENTS/input/` 配下に最低限以下が揃っているか確認：
   - 1つ以上の `*table_definition*` ファイル
   - 1つ以上の `*sample_data*` ファイル
   - `data_spec.md`
   - `constraints.md`

`input/` が不足している場合は、まず `source/` に原資料があるか確認する。互換的に `raw/`, `docs/`, `input_sources/` も確認してよい。原資料があれば `0_input_prepare` から開始する。原資料もない場合は、不足ファイルを具体的に報告して停止する。

## 実行フロー（PM の手順）

各ステップで PM は以下を行う：

1. **サブエージェントを起動**: 利用環境のサブエージェント / タスク委譲機構を使う（例: Claude Code では `Agent` ツールに `subagent_type=general-purpose` を指定、Codex 等では各環境のタスク委譲機構）。固有のツール名・パラメータ名はあくまで例示であり、環境に合わせて読み替える。
2. **委譲内容**を簡潔に伝える（次の節「サブエージェント起動テンプレ」参照）。
3. **完了報告**を受け取り、SKILL.md の Acceptance Criteria を満たしたか PM 自身で確認する。確認手段は、**成果物ファイルの存在を確認**し、step4 完了後は **`output/quality_gate.json` を read して `status` / `requires_refinement` の値を確認**する（サブエージェントの自己申告だけに頼らない）。
4. **未達** なら、その旨を報告して停止（必要なら同サブエージェントを再起動して修正を依頼）。
5. **OK** なら次のステップへ。

### ステップ一覧

| # | SKILL | 主な成果物 |
|---|-------|-----------|
| 0 | `0_input_prepare` | `input/*table_definition*`, `input/*sample_data*`, `input/data_spec.md`, `input/constraints.md` |
| 1 | `1_spec_ingest` | `work/inferred_schema.json`, `work/constraint_plan.md` |
| 2 | `2_generation_plan` | `work/generation_plan.md` |
| 3 | `3_generator_impl` | `src/generator.py`, `output/synthetic_data.csv`（単一）/ `output/<table>.csv`（複数） |
| 4 | `4_evaluate_and_refine` | `src/evaluate.py`, `output/evaluation_report.md`, `output/constraints_check.csv`, `output/quality_gate.json` |

### サブエージェント起動テンプレ

サブエージェント / タスク委譲機構に渡す `prompt`（Claude Code なら `Agent` ツールの `prompt`）は次の構造に揃える。

```
あなたは合成データ生成パイプラインの「<step_name>」サブエージェントです。

タスクディレクトリ: <task_dir>
従うべき SKILL 仕様: .agents/skills/<step_name>/SKILL.md
直前ステップの成果物（読込のみ）: <list>
あなたが生成すべき成果物: <list>

SKILL.md の Tasks / Rules / Acceptance Criteria に厳密に従ってください。
完了したら、生成したファイルのパス・件数・Acceptance Criteria を満たしているかどうかを
200 字以内で報告してください。
```

`description` は `"<step_name> 実行"` のように短く（例: `"0_input_prepare 実行"`）。

PM は **複数のサブエージェントを並列起動しない**（依存関係があるため、必ず逐次）。

## 改善ループ（PM が判定・制御する）

改善ループの責務は **PM 側にある**。step4（`4_evaluate_and_refine`）は「評価して `quality_gate.json` と推奨修正を出す」役割であり、step4 が内部で延々と自己修正ループを回すことはしない。最終的な再生成の要否判断は PM が `quality_gate.json` で行う。

手順:

1. `4_evaluate_and_refine` 完了後、PM は `$ARGUMENTS/output/quality_gate.json` を **read** する。
2. `requires_refinement == true` の場合のみ、`3_generator_impl` のサブエージェントを再起動して再生成し、続けて `4_evaluate_and_refine` を再実行する（`blocking_issues` と `summary` を原因として伝える）。
3. `requires_refinement == false`（または `status == "pass"`）なら、ループを終了して完了報告へ進む。

**打ち切り条件（一箇所で定義）**:

- 再生成（`3_generator_impl` → `4_evaluate_and_refine` の再実行）は **最大 2 回まで**。
- 上限に達しても `requires_refinement` が解消しない場合は、残課題を「追加仕様が必要な点」または「既知の限界」として `output/evaluation_report.md` に明記させ、ループを停止する。

## generator.py を修正する主体の境界

- **軽微で明白な修正**（型不一致・明らかな値域逸脱・カテゴリ値の仕様違反など）は step4 のサブエージェントが直接 generator.py に反映する。
- **構造的な作り直し**（生成方式そのものの見直し等）が必要な場合は、PM が `quality_gate.json` の `blocking_issues` を根拠に `3_generator_impl` を再委譲する。

## 進捗報告（PM が逐次出す）

各ステップ開始時と完了時に、1〜2 行のステータスを出力する。

```
[0_input_prepare] sub-agent 起動
[0_input_prepare] 完了: input/table_definition.csv, input/sample_data.csv, input/data_spec.md, input/constraints.md
[1_spec_ingest] sub-agent 起動
[1_spec_ingest] 完了: work/inferred_schema.json, work/constraint_plan.md
[2_generation_plan] sub-agent 起動
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
- **4_evaluate_and_refine で `requires_refinement == true`**: 「改善ループ」節の手順・打ち切り条件（再生成は最大 2 回まで）に従って `3_generator_impl` を再委譲する。上限到達後も解消しない場合は、残課題を `evaluation_report.md` に明記させてループを停止する。

## ルール

- PM は **コードを書かない、ファイルを編集しない**。すべての実作業をサブエージェントに委譲する。
- サブエージェントへの指示は **タスク非依存**にする（タスク固有情報は `$ARGUMENTS` 配下の原資料または `input/` を読みに行く形）。
- 既に存在する `work/`, `src/`, `output/` の旧成果物は **上書きしてよい**。
- 個人情報の直接コピーは禁止（サブエージェントへの指示にも含める）。

## 参考

- 各 SKILL の本体: `.agents/skills/<step>/SKILL.md`
- パイプライン仕様: `docs/spec.md`
- 既存タスク例: `examples/customer/`, `examples/customer_transactions/`, `examples/university_enrollment/`
