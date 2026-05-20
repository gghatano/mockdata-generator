---
name: synthesize
description: タスクディレクトリ ($ARGUMENTS) の input/ を読み取り、合成データ生成パイプライン（0_spec_ingest → 1_generation_plan → 2_generator_impl → 3_evaluate_and_refine）を end-to-end で順次自動実行する。各ステップの Acceptance Criteria を満たさない場合は停止して報告する。
---

# synthesize

仕様駆動の合成データ生成パイプラインを **一発で end-to-end 実行する** マスタースキル。

ユーザーがやることは `input/` を整備することのみ。あとはこのスキルが 0→1→2→3 を順次回す。

## 引数

`$ARGUMENTS` にタスクのルートディレクトリを受け取る。
例: `examples/university_enrollment`

引数が空の場合は、`examples/` 配下のタスクディレクトリ一覧を提示してユーザーに選択を促す。

## 前提（実行前チェック）

開始前に以下を確認する。1つでも欠ければユーザーに不足を報告して停止する。

- `$ARGUMENTS/input/` ディレクトリが存在する
- `$ARGUMENTS/input/` 配下に以下のうち少なくとも以下4種が揃っている：
  - 1つ以上の `*table_definition*` ファイル（.csv または .xlsx）
  - 1つ以上の `*sample_data*` ファイル
  - `data_spec.md`
  - `constraints.md`

## 実行手順

以下の4ステップを **順番に** 実行する。各ステップは独立した SKILL として `.claude/skills/<step>/SKILL.md` に詳細が定義されているので、その内容に従う。

### Step 0: 0_spec_ingest

- `.claude/skills/0_spec_ingest/SKILL.md` の指示に従い、`$ARGUMENTS/work/inferred_schema.json` と `$ARGUMENTS/work/constraint_plan.md` を作成する。
- Acceptance Criteria（同 SKILL.md 末尾）を満たすことを確認してから次へ進む。

### Step 1: 1_generation_plan

- `.claude/skills/1_generation_plan/SKILL.md` の指示に従い、`$ARGUMENTS/work/generation_plan.md` を作成する。
- Acceptance Criteria を確認してから次へ進む。

### Step 2: 2_generator_impl

- `.claude/skills/2_generator_impl/SKILL.md` の指示に従い、`$ARGUMENTS/src/generator.py` を実装し、`$ARGUMENTS/output/<table>.csv` を生成する。
- 必ず `uv run python $ARGUMENTS/src/generator.py …` を実行し、CSV が生成されることまで確認する。
- Acceptance Criteria を確認してから次へ進む。

### Step 3: 3_evaluate_and_refine

- `.claude/skills/3_evaluate_and_refine/SKILL.md` の指示に従い、`$ARGUMENTS/src/evaluate.py` を実装し、評価レポートを生成する。
- 必ず `uv run python $ARGUMENTS/src/evaluate.py …` を実行し、`evaluation_report.md` と `constraints_check.csv` が生成されることまで確認する。
- 重大な制約違反が出た場合は、`generator.py` を修正して 2_generator_impl と 3_evaluate_and_refine を再実行する（最大2回まで）。

## サブエージェント委譲（任意）

タスクが大規模でメインコンテキストが圧迫されそうな場合は、各ステップを `Agent` ツール経由でサブエージェントに委譲してよい。
その際は

- 各エージェントに `$ARGUMENTS` と該当 SKILL.md のパスを渡し、
- 完了後の主な成果物パスと Acceptance Criteria 充足の判定を簡潔に返してもらう

ようにする。サブエージェント不要な小規模タスクは、メインのままで順次実行する。

## 進捗報告

ステップごとに **1行のステータス更新** をユーザーに返す（無言で進めない）。

例：
```
[0_spec_ingest] work/inferred_schema.json と constraint_plan.md を作成
[1_generation_plan] work/generation_plan.md を作成
[2_generator_impl] generator.py 実装 → output/synthetic_data.csv を10000行生成
[3_evaluate_and_refine] 評価レポート出力。必須制約違反 0 件
```

## 完了報告

全ステップ成功時は、最後に以下をまとめて報告する。

- 生成ファイルパス（output/, work/, src/）
- 主な評価結果（制約違反件数、データ件数、主要分布の要約）
- 改善が必要な点（あれば）

## 失敗時の挙動

- 前提チェックで不足があった場合: ユーザーに不足ファイルを明示して停止
- 中間ステップが Acceptance Criteria を満たさない場合: そのステップでの問題を報告して停止
- ステップ間でファイル整合が崩れた場合（例: schema にあるが sample にない列など）: 問題を提示してユーザーに判断を仰ぐ

## ルール

- ユーザーが追加情報を与えていない限り、`input/` 配下のファイルだけを参照すること。
- 個人情報を直接コピーしないこと。
- 既に存在する `work/`, `src/`, `output/` のファイルは上書きする（ユーザー指示で incremental にしたい場合は別途オプション）。

## 参考

- 各 SKILL の詳細: `.claude/skills/<skill_name>/SKILL.md`
- パイプラインの完全な仕様: `docs/spec.md`
- 既存タスク例: `examples/customer/`, `examples/customer_transactions/`, `examples/university_enrollment/`
