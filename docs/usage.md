# Usage Guide

`mockdata-generator` の使い方をまとめたドキュメントです。
全体の仕様や設計方針は [spec.md](spec.md) を参照してください。

## 基本の流れ

```text
1. examples/<task_name>/input/ に入力ファイルを配置する
2. /synthesize examples/<task_name> を実行する
3. work/、src/、output/ の成果物を確認する
4. 必要に応じて入力仕様を直し、再実行する
```

## タスクディレクトリを作る

タスクごとに `examples/<task_name>/` を作成します。

```text
examples/<task_name>/
└── input/
```

既存サンプルをコピーして始めることもできます。

```bash
cp -r examples/customer examples/my_task
```

## 入力ファイルを配置する

`input/` には、生成したいデータの仕様を置きます。

```text
examples/<task_name>/input/
├── *table_definition.csv
├── *sample_data.csv
├── data_spec.md
└── constraints.md
```

各ファイルの役割は以下です。

| ファイル | 役割 |
| --- | --- |
| `*table_definition.csv` | 列名、型、必須/任意、桁数、コード値などのテーブル定義 |
| `*sample_data.csv` | 値域、分布、欠損率、カテゴリ比率などを推定するためのサンプル |
| `data_spec.md` | 業務ルール、列同士の関係、生成時に守りたい前提 |
| `constraints.md` | 必須制約、推奨制約、評価観点 |

複数テーブルを扱う場合は、テーブルごとに `*table_definition.csv` と `*sample_data.csv` を配置します。

```text
examples/customer_transactions/input/
├── customer_table_definition.csv
├── customer_sample_data.csv
├── transaction_table_definition.csv
├── transaction_sample_data.csv
├── data_spec.md
└── constraints.md
```

## 一括実行する

Claude Code で以下を実行します。

```text
/synthesize examples/<task_name>
```

例:

```text
/synthesize examples/customer
```

`/synthesize` は PM エージェントとして動作し、以下のステップを順番に実行します。

```text
0_spec_ingest
  ↓
1_generation_plan
  ↓
2_generator_impl
  ↓
3_evaluate_and_refine
```

## 出力を確認する

実行後、タスクディレクトリには以下の成果物が作成されます。

```text
examples/<task_name>/
├── work/
│   ├── inferred_schema.json
│   ├── constraint_plan.md
│   └── generation_plan.md
├── src/
│   ├── generator.py
│   └── evaluate.py
└── output/
    ├── synthetic_data.csv
    ├── evaluation_report.md
    └── constraints_check.csv
```

主に確認するファイルは以下です。

| ファイル | 確認内容 |
| --- | --- |
| `output/synthetic_data.csv` | 生成された合成データ |
| `output/evaluation_report.md` | 評価結果のサマリ |
| `output/constraints_check.csv` | 制約ごとの判定結果 |
| `src/generator.py` | 再実行可能な生成器 |
| `src/evaluate.py` | 評価スクリプト |

## 生成済みコードを再実行する

`generator.py` と `evaluate.py` が作成された後は、Claude Code を使わずに Python 側だけで再実行できます。

```bash
uv run python examples/customer/src/generator.py --rows 10000 --seed 42
uv run python examples/customer/src/evaluate.py
```

複数テーブルの例:

```bash
uv run python examples/customer_transactions/src/generator.py --customers 1000 --seed 42
uv run python examples/customer_transactions/src/evaluate.py
```

## ステップごとに実行する

一括実行ではなく、途中成果物を確認しながら進めたい場合は、各ステップを個別に実行できます。

```text
/0_spec_ingest         examples/<task_name>
/1_generation_plan     examples/<task_name>
/2_generator_impl      examples/<task_name>
/3_evaluate_and_refine examples/<task_name>
```

ステップごとの主な役割は以下です。

| ステップ | 役割 | 主な出力 |
| --- | --- | --- |
| `0_spec_ingest` | 入力仕様を読み取り、機械可読なスキーマと制約計画を作る | `work/inferred_schema.json`, `work/constraint_plan.md` |
| `1_generation_plan` | 各列の生成方式を設計する | `work/generation_plan.md` |
| `2_generator_impl` | 生成器を実装し、合成データを出力する | `src/generator.py`, `output/*.csv` |
| `3_evaluate_and_refine` | 制約・仕様・サンプルに照らして評価し、必要に応じて修正する | `src/evaluate.py`, `output/evaluation_report.md`, `output/constraints_check.csv` |

## 入力を修正して再実行する

生成結果が期待と違う場合は、まず `input/` の仕様を更新します。

- 列の意味や生成ルールを足す場合: `data_spec.md`
- 必ず守る条件を追加する場合: `constraints.md`
- 型、桁数、コード値を直す場合: `*table_definition.csv`
- 分布や値域の参考を変える場合: `*sample_data.csv`

修正後、同じコマンドを再実行します。

```text
/synthesize examples/<task_name>
```

## 関連ドキュメント

- [spec.md](spec.md): ワークフロー仕様、設計方針、Acceptance Criteria
- [../.claude/skills/synthesize/SKILL.md](../.claude/skills/synthesize/SKILL.md): 一括実行の PM エージェント
- [../.claude/skills/0_spec_ingest/SKILL.md](../.claude/skills/0_spec_ingest/SKILL.md): 仕様読み取り
- [../.claude/skills/1_generation_plan/SKILL.md](../.claude/skills/1_generation_plan/SKILL.md): 生成方針設計
- [../.claude/skills/2_generator_impl/SKILL.md](../.claude/skills/2_generator_impl/SKILL.md): 生成器実装
- [../.claude/skills/3_evaluate_and_refine/SKILL.md](../.claude/skills/3_evaluate_and_refine/SKILL.md): 評価と改善
