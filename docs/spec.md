以下の構成がよいです。
GReaTではなく、**仕様駆動のPython生成器をLLMに作らせ、実行・評価まで回す方式**です。

---

# 1. 全体ワークフロー

```text
入力
  ├─ テーブル定義書
  ├─ サンプルデータ
  ├─ データ仕様メモ
  └─ 制約条件
      ↓
仕様理解
      ↓
生成方針設計
      ↓
generator.py 作成
      ↓
合成データ生成
      ↓
post sampling / rule filtering
      ↓
品質評価
      ↓
出力
  ├─ synthetic_data.csv
  ├─ generator.py
  ├─ evaluation_report.md
  ├─ constraints_check.csv
  └─ quality_gate.json
```

---

# 2. 推奨ディレクトリ構成

```text
spec-driven-synth-demo/
├── input/
│   ├── table_definition.xlsx
│   ├── sample_data.csv
│   ├── data_spec.md
│   └── constraints.md
├── work/
│   ├── inferred_schema.json
│   ├── generation_plan.md
│   └── constraint_plan.md
├── src/
│   ├── generator.py
│   ├── validate.py
│   └── evaluate.py
├── output/
│   ├── synthetic_data.csv
│   ├── evaluation_report.md
│   ├── constraints_check.csv
│   └── quality_gate.json
└── README.md
```

---

# 3. ワークフロー定義

## Step 1. 入力整理

目的：入力資料から、生成に使う仕様を機械可読化する。

実施内容：

```text
- テーブル定義書から列名、型、説明、必須/任意、コード値、桁数を抽出
- サンプルデータから実際の値域、分布、欠損率、カテゴリ値を確認
- データ仕様メモから業務ルールを抽出
- 制約条件を「生成時制約」と「生成後制約」に分類
```

成果物：

```text
work/inferred_schema.json
work/constraint_plan.md
```

---

## Step 2. 生成方針設計

目的：各列をどう生成するか決める。

分類は以下。

| 生成方式          | 対象             |
| ------------- | -------------- |
| 固定値           | システム区分、年度など    |
| カテゴリ抽選        | 性別、地域、ステータス    |
| 数値分布          | 年齢、金額、件数       |
| 日付生成          | 登録日、受診日、申請日    |
| 相関付き生成        | 年齢×医療費、世帯人数×所得 |
| ルール生成         | コード体系、ID採番     |
| post sampling | 複雑な組合せ制約       |

成果物：

```text
work/generation_plan.md
```

---

## Step 3. generator.py 作成

目的：再実行可能なPython生成器を作る。

必須要件：

```text
- seed指定可能
- 生成件数指定可能
- pandas DataFrameを返す
- CSV出力可能
- 入力仕様をコメントで明示
- 乱数生成は numpy.random.Generator を使う
- 生成後に制約違反チェックを行う
```

実行イメージ：

```bash
uv run python src/generator.py \
  --rows 10000 \
  --seed 42 \
  --output output/synthetic_data.csv
```

---

## Step 4. post sampling / rule filtering

目的：生成時に表現しにくい制約を、生成後に満たす。

例：

```text
- 年齢 < 18 の場合、配偶者ありを除外
- 退職日 < 入社日 の行を除外
- 医療費が0円なのに受診回数が1以上の行を除外
- 特定コードの組合せが仕様上あり得ない行を除外
```

重要なのは、**削除件数を記録すること**です。

成果物：

```text
output/constraints_check.csv
```

---

## Step 5. 評価レポート作成

目的：合成データが仕様・サンプルにどの程度合っているか説明する。

最低限の評価項目：

| 評価観点   | 内容             |
| ------ | -------------- |
| スキーマ適合 | 列名、型、NULL、桁数   |
| 値域     | min/max、カテゴリ値  |
| 欠損率    | サンプルとの比較       |
| 分布     | 数値列・カテゴリ列の分布比較 |
| 相関     | 主要数値列の相関比較     |
| 制約充足   | 制約違反件数         |
| 生成ログ   | 生成件数、削除件数、最終件数 |

成果物：

```text
output/evaluation_report.md
output/quality_gate.json
```

評価で必須制約違反、スキーマ不一致、明示仕様に反する値域・カテゴリ・日付関係などの品質課題が見つかった場合は、`generator.py` を修正して再生成し、同じ評価を再実行する。サンプル統計との差異が仕様違反ではない場合は、過剰に合わせ込まず、既知の限界または追加仕様が必要な点としてレポートに残す。

`quality_gate.json` は PM エージェントが改善ループの要否を判定するための機械可読な品質ゲートであり、最低限以下を含める。

```json
{
  "status": "pass",
  "requires_refinement": false,
  "blocking_issue_count": 0,
  "warning_issue_count": 0,
  "blocking_issues": [],
  "warnings": [],
  "summary": "品質ゲートを通過しました。"
}
```

---

# 4. SKILL定義案

Claude Code等に渡すなら、以下の4つに分けるのが扱いやすいです。

```text
0_spec_ingest
1_generation_plan
2_generator_impl
3_evaluate_and_refine
```

---

# SKILL: 0_spec_ingest

```md
# 0_spec_ingest

## Purpose

テーブル定義書、サンプルデータ、データ仕様メモ、制約条件を読み取り、合成データ生成に必要な仕様を機械可読な形に整理する。

## Inputs

- input/table_definition.xlsx または input/table_definition.csv
- input/sample_data.csv
- input/data_spec.md
- input/constraints.md

## Outputs

- work/inferred_schema.json
- work/constraint_plan.md

## Tasks

1. テーブル定義書から以下を抽出する。
   - column_name
   - logical_name
   - data_type
   - nullable
   - description
   - allowed_values
   - min_value
   - max_value
   - format
   - primary_key
   - foreign_key

2. サンプルデータから以下を推定する。
   - 実データ型
   - 欠損率
   - ユニーク数
   - 代表値
   - 数値列の min / max / mean / std
   - カテゴリ列の頻度
   - 日付列の範囲

3. データ仕様メモと制約条件から、ルールを抽出する。

4. 制約を以下に分類する。
   - generation_constraint: 生成時に直接反映する制約
   - post_sampling_constraint: 生成後にフィルタリングする制約
   - validation_only_constraint: 評価のみ行う制約

## Rules

- サンプルデータとテーブル定義書が矛盾する場合は、矛盾点を明示する。
- 推定した内容と明示仕様を区別する。
- 不明な仕様は勝手に確定せず、assumption として記録する。
- 個人情報を直接再現するような処理は行わない。

## Acceptance Criteria

- work/inferred_schema.json が生成されている。
- work/constraint_plan.md に制約分類が記載されている。
- 明示仕様、推定仕様、仮定が区別されている。
```

---

# SKILL: 1_generation_plan

```md
# 1_generation_plan

## Purpose

inferred_schema.json と constraint_plan.md をもとに、各列の生成方法を設計する。

## Inputs

- work/inferred_schema.json
- work/constraint_plan.md
- input/sample_data.csv

## Outputs

- work/generation_plan.md

## Tasks

1. 各列について生成方式を決める。
   - sequential_id
   - random_category
   - weighted_category
   - numeric_distribution
   - date_range
   - correlated_numeric
   - rule_based
   - derived_column
   - free_text_template

2. サンプルデータから使う統計量を決める。

3. 列間関係を特定する。
   - 年齢と金額
   - 日付の前後関係
   - コードと名称
   - ステータスと日付
   - 親子関係

4. 複雑な制約は post sampling に回す。

5. 生成件数に対して、post sampling後に必要件数を確保できるよう、oversampling倍率を決める。

## Rules

- 生成ロジックは説明可能であること。
- 実データの特定レコードを再現しないこと。
- サンプルデータの分布を過度にコピーしないこと。
- 乱数 seed により再現可能にすること。
- 仕様が不明な列は、保守的な生成方法を選ぶ。

## Acceptance Criteria

- 全列に生成方式が割り当てられている。
- post sampling対象の制約が明示されている。
- 生成ロジックの根拠が記載されている。
```

---

# SKILL: 2_generator_impl

````md
# 2_generator_impl

## Purpose

generation_plan.md に基づいて、合成データ生成用の Python スクリプトを実装する。

## Inputs

- work/generation_plan.md
- work/inferred_schema.json
- work/constraint_plan.md
- input/sample_data.csv

## Outputs

- src/generator.py
- output/synthetic_data.csv

## Tasks

1. src/generator.py を作成する。

2. generator.py は以下のCLIを持つこと。

```bash
uv run python src/generator.py --rows 10000 --seed 42 --output output/synthetic_data.csv
````

3. generator.py は以下を満たすこと。

   * pandas DataFrame を生成する
   * numpy.random.default_rng(seed) を使う
   * 生成件数を指定できる
   * seed を指定できる
   * CSV出力できる
   * UTF-8で出力する
   * post sampling を実行できる
   * 削除件数をログ出力する

4. 難しい制約は、生成後にフィルタリングする。

5. 最終行数が指定件数に足りない場合は、再サンプリングする。

## Rules

* 生成コードは再実行可能にする。
* 外部APIには依存しない。
* 個人情報を直接含めない。
* サンプルデータの行をそのままコピーしない。
* コード内に仕様の根拠をコメントで残す。
* ruffで整形可能なPythonコードにする。

## Acceptance Criteria

* generator.py がエラーなく実行できる。
* 指定件数のCSVが生成される。
* 列名と型が inferred_schema.json と整合している。
* post sampling の削除件数が確認できる。

````

---

# SKILL: 3_evaluate_and_refine

```md
# 3_evaluate_and_refine

## Purpose

生成された合成データを、仕様・サンプルデータ・制約条件に照らして評価し、品質課題があれば generator.py を修正して再生成・再評価する。

## Inputs

- input/sample_data.csv
- output/synthetic_data.csv
- work/inferred_schema.json
- work/constraint_plan.md
- src/generator.py

## Outputs

- src/evaluate.py
- output/evaluation_report.md
- output/constraints_check.csv
- output/quality_gate.json

## Tasks

1. src/evaluate.py を作成する。

2. 以下の観点で評価する。
   - 列名一致
   - 型一致
   - 欠損率
   - ユニーク数
   - 数値列の min / max / mean / std
   - カテゴリ列の頻度分布
   - 日付列の範囲
   - 主要な列間相関
   - 制約違反件数

3. 制約違反を constraints_check.csv に出力する。

4. quality_gate.json に以下を記載する。
   - status: pass / fail
   - requires_refinement: generator.py の修正が必要なら true
   - blocking_issues: 必須制約違反、スキーマ不一致、明示仕様違反
   - warnings: 統計的差異、サンプル不足、追加仕様が必要な非ブロッキング課題
   - summary: PM エージェント向けの短い判定理由

5. evaluation_report.md に以下を記載する。
   - 入力概要
   - 生成概要
   - スキーマ評価
   - 分布評価
   - 相関評価
   - 制約評価
   - 品質ゲート
   - 主な差異
   - 改善案
   - 注意事項

6. 評価結果に重大な問題がある場合、generator.py を修正する。
   - 型不一致
   - 制約違反
   - 明らかな値域逸脱
   - 欠損率の大幅乖離
   - カテゴリ値の仕様違反

7. 修正後は generator.py を再実行して合成データを作り直し、evaluate.py を再実行する。

8. evaluation_report.md には、改善した項目、残った課題、追加仕様が必要な項目を明記する。

## Rules

- 評価結果をごまかさない。
- サンプルデータに過剰適合させない。
- 仕様違反と統計的差異を区別する。
- generator.py を修正した場合は、必ず再生成と再評価まで行う。
- 匿名加工済みデータであるとは記載しない。
- 合成データの利用範囲を明示する。

## Acceptance Criteria

- evaluation_report.md が生成されている。
- constraints_check.csv が生成されている。
- quality_gate.json が生成され、status と requires_refinement が機械可読に記録されている。
- 重大な仕様違反がない。
- 品質課題に対応して generator.py を修正した場合、修正後データで再評価済みである。
- 残課題がある場合、その理由と追加で必要な仕様が明記されている。
- 既知の限界が明記されている。
````

---

# 5. Claude Codeに渡す初回プロンプト案

````md
# 依頼

仕様駆動で合成データを生成するデモを作成してください。

## 目的

テーブル定義書、サンプルデータ、データ仕様メモ、制約条件を入力として、仕様に沿った合成データを生成する Python スクリプトを作成し、生成データと評価レポートを出力する。

## 入力

以下のファイルを利用してください。

- input/table_definition.xlsx
- input/sample_data.csv
- input/data_spec.md
- input/constraints.md

## 出力

以下を作成してください。

- work/inferred_schema.json
- work/generation_plan.md
- work/constraint_plan.md
- src/generator.py
- src/evaluate.py
- output/synthetic_data.csv
- output/evaluation_report.md
- output/constraints_check.csv
- output/quality_gate.json

## 進め方

以下のSKILL順に進めてください。

1. 0_spec_ingest
2. 1_generation_plan
3. 2_generator_impl
4. 3_evaluate_and_refine

## 実装方針

- Pythonで実装してください。
- パッケージ管理は uv を使ってください。
- pandas, numpy を基本としてください。
- faker は必要な場合のみ使ってください。
- 外部APIには依存しないでください。
- 生成ロジックは generator.py に明示してください。
- 難しい制約は post sampling として生成後に除外してください。
- post sampling で除外した件数を記録してください。
- seed 指定により再現可能にしてください。
- サンプルデータの行をそのままコピーしないでください。
- 出力データを匿名加工情報とは表現しないでください。

## 実行コマンド

以下で動作するようにしてください。

```bash
uv run python src/generator.py --rows 10000 --seed 42 --output output/synthetic_data.csv
uv run python src/evaluate.py --sample input/sample_data.csv --synthetic output/synthetic_data.csv --report output/evaluation_report.md
````

## 完了条件

* 上記コマンドがエラーなく実行できること
* synthetic_data.csv が指定件数で生成されること
* evaluation_report.md に評価結果が出力されること
* constraints_check.csv に制約チェック結果が出力されること
* quality_gate.json に pass/fail と改善要否が出力されること
* README.md に使い方が記載されていること

````

---

# 6. 実務上の設計判断

このデモでは、最初から高精度な統計再現を狙わない方がよいです。

主張すべき価値は以下です。

```text
テーブル定義書・仕様メモを起点に、
説明可能な生成ロジックを作成し、
PoC・画面モック・分析仮説検討に使えるデータを迅速に準備する。
````

避けるべき主張は以下です。

```text
実データと同等の分析ができる
匿名加工情報として安全である
個人情報保護上の安全性が保証される
```

この線引きを入れておくと、顧客説明・社内レビュー・法務確認で安定します。
