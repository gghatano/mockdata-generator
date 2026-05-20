# mockdata-generator

仕様駆動の合成データ生成パイプライン。
テーブル定義書 / サンプルデータ / データ仕様メモ / 制約条件を入力として、再現可能な Python 生成器と評価レポートを出力する。

## 思想

- 共通の **SKILL（パイプライン仕様）** は `docs/spec.md` で定義する。
- データ生成は **タスク単位** で独立。タスクごとに `input/`, `work/`, `src/`, `output/` を持つ。
- SKILL の順序 (`0_spec_ingest` → `1_generation_plan` → `2_generator_impl` → `3_evaluate_and_refine`) はどのタスクでも変わらない。
- 列名・テーブル名・制約はタスク固有。それぞれのタスクの `input/` 配下にすべて記述する。

## ディレクトリ構成

```
mockdata-generator/
├── docs/
│   └── spec.md                # SKILL定義（共通・タスク非依存）
├── pyproject.toml             # uv 環境
├── README.md                  # 本ドキュメント
└── examples/
    ├── customer/                       # タスク例1: 顧客マスタ単体
    │   ├── input/
    │   │   ├── table_definition.csv    # 列名・型・許容値などの仕様
    │   │   ├── sample_data.csv         # 統計量推定用サンプル
    │   │   ├── data_spec.md            # 業務ルールの自然言語仕様
    │   │   └── constraints.md          # 必須/推奨制約
    │   ├── work/                       # 中間成果物（0_spec_ingest / 1_generation_plan）
    │   │   ├── inferred_schema.json
    │   │   ├── constraint_plan.md
    │   │   └── generation_plan.md
    │   ├── src/                        # 2_generator_impl / 3_evaluate_and_refine
    │   │   ├── generator.py
    │   │   └── evaluate.py
    │   └── output/                     # 最終成果物
    │       ├── synthetic_data.csv
    │       ├── evaluation_report.md
    │       └── constraints_check.csv
    └── customer_transactions/          # タスク例2: 顧客×取引（FK・在籍期間・年合計整合）
        ├── input/  work/  src/  output/
```

## ワークフロー（新しいタスクを追加するとき）

1. `examples/<task_name>/input/` を作り、以下を配置する。
   - `table_definition.csv`（または `.xlsx`）
   - `sample_data.csv`（テーブルが複数なら複数ファイル可）
   - `data_spec.md`
   - `constraints.md`
2. `SKILL 0_spec_ingest` に従い、`work/inferred_schema.json` と `work/constraint_plan.md` を作成する。
3. `SKILL 1_generation_plan` に従い、`work/generation_plan.md` を作成する。
4. `SKILL 2_generator_impl` に従い、`src/generator.py` を実装する。
5. `SKILL 3_evaluate_and_refine` に従い、`src/evaluate.py` を実装し、評価レポートを生成する。
6. 必要に応じて、評価結果を踏まえて `generator.py` を修正する。

各 SKILL の詳細・入力・出力・Acceptance Criteria は `docs/spec.md` および `.claude/skills/<skill_name>/SKILL.md` を参照。

## SKILL の呼び出し（Claude Code）

各ステップは Claude Code の SKILL として `.claude/skills/` に登録されている。タスクのルートディレクトリを `$ARGUMENTS` として渡す。

```
/0_spec_ingest         examples/university_enrollment
/1_generation_plan     examples/university_enrollment
/2_generator_impl      examples/university_enrollment
/3_evaluate_and_refine examples/university_enrollment
```

スラッシュコマンドのほか、Claude が自動マッチで起動することもある（各 SKILL.md の `description` を参照）。

## 実行例

各タスクは独立して実行できる。コマンドはタスクのルート（プロジェクトルート）から実行する想定。

### タスク1（顧客マスタ単体）

```bash
uv run python examples/customer/src/generator.py --rows 10000 --seed 42
uv run python examples/customer/src/evaluate.py
```

### タスク2（顧客マスタ × 取引履歴）

```bash
uv run python examples/customer_transactions/src/generator.py --customers 1000 --seed 42
uv run python examples/customer_transactions/src/evaluate.py
```

タスク2 は親子関係（FK）・在籍期間内の取引日・直近1年の取引合計と annual_spend の整合といった、複数テーブルにまたがる制約のサンプル。`importlib` でタスク1 の generator/evaluate を再利用している（共通ロジックをタスク横断で使う一例）。

## 依存

- Python 3.13+
- uv（パッケージ管理）
- pandas, numpy, openpyxl, tabulate

```bash
uv sync
```

## 設計上の注意

- 生成データは **仕様駆動の合成データ**であり、匿名加工情報ではない。
- 実データの統計再現性は保証しない。PoC、画面モック、分析仮説検討用途を想定。
- 生成は `numpy.random.default_rng(seed)` で固定し再現可能にする。
- post sampling での除外件数は必ずログ出力する（`docs/spec.md` 参照）。
- サンプルデータの行をそのまま含めない。
