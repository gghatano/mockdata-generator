# mockdata-generator

仕様駆動で合成データを生成するためのエージェントワークフローです。
テーブル定義書、サンプルデータ、データ仕様、制約条件を入力し、再実行可能な Python 生成器と評価レポートを出力します。

## Quickstart

### 1. 依存関係を準備する

```bash
uv sync
```

必要環境:

- Python 3.14+
- uv

### 2. 入力ファイルを配置する

タスクごとに `examples/<task_name>/input/` を作成し、以下を配置します。

```text
examples/<task_name>/input/
├── *table_definition.csv   # 列名、型、許容値など
├── *sample_data.csv        # 統計量・値域の参考サンプル
├── data_spec.md            # 業務ルールや生成仕様
└── constraints.md          # 必須/推奨制約
```

複数テーブルの場合は、テーブルごとに `*table_definition.csv` と `*sample_data.csv` を配置します。

### 3. 合成データを生成する

Claude Code で次を実行します。

```text
/synthesize examples/<task_name>
```

例:

```text
/synthesize examples/customer
```

生成後は、主に以下のファイルを確認します。

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

## 生成済みコードの再実行

`/synthesize` で `generator.py` / `evaluate.py` が作成された後は、Python 側だけで再実行できます。

```bash
# 顧客マスタ単体
uv run python examples/customer/src/generator.py --rows 10000 --seed 42
uv run python examples/customer/src/evaluate.py

# 顧客 x 取引
uv run python examples/customer_transactions/src/generator.py --customers 1000 --seed 42
uv run python examples/customer_transactions/src/evaluate.py
```

## ステップごとに実行する場合

一括実行ではなく、各ステップを個別に確認しながら進めることもできます。

```text
/0_spec_ingest         examples/<task_name>
/1_generation_plan     examples/<task_name>
/2_generator_impl      examples/<task_name>
/3_evaluate_and_refine examples/<task_name>
```

## 詳細ドキュメント

- [docs/spec.md](docs/spec.md): ワークフロー、設計方針、各ステップの詳細
- [.claude/skills/synthesize/SKILL.md](.claude/skills/synthesize/SKILL.md): 一括実行の PM エージェント
- [.claude/skills/0_spec_ingest/SKILL.md](.claude/skills/0_spec_ingest/SKILL.md): 仕様読み取り
- [.claude/skills/1_generation_plan/SKILL.md](.claude/skills/1_generation_plan/SKILL.md): 生成方針設計
- [.claude/skills/2_generator_impl/SKILL.md](.claude/skills/2_generator_impl/SKILL.md): 生成器実装
- [.claude/skills/3_evaluate_and_refine/SKILL.md](.claude/skills/3_evaluate_and_refine/SKILL.md): 評価と改善

## 注意

- 生成データは仕様駆動の合成データであり、匿名加工情報ではありません。
- 実データの統計再現性は保証しません。
- PoC、画面モック、分析仮説検討用途を想定しています。
