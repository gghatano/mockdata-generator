---
name: 2_generation_plan
description: タスクディレクトリ ($ARGUMENTS) の inferred_schema.json と constraint_plan.md をもとに、各列の生成方式を設計し work/generation_plan.md を作成する。
---

# 2_generation_plan

合成データの生成方針を設計するステップ。1_spec_ingest の後に実行する。

## 引数

`$ARGUMENTS` にタスクのルートディレクトリを受け取る。

## 入力

- `$ARGUMENTS/work/inferred_schema.json`
- `$ARGUMENTS/work/constraint_plan.md`
- `$ARGUMENTS/input/data_spec.md`
- `$ARGUMENTS/input/*sample_data*`（単一: `sample_data.csv` / 複数: `<table>_sample_data.csv`）

## 出力

- `$ARGUMENTS/work/generation_plan.md`

## タスク

1. **各列の生成方式を選定**:
   - `sequential_id`: 連番ID
   - `random_category` / `weighted_category`: カテゴリ抽選
   - `numeric_distribution`: 数値分布（正規分布、log-normal など）
   - `date_range`: 日付の一様/重み付きサンプル
   - `correlated_numeric`: 他列との相関を持つ数値
   - `rule_based`: 列値からの決定論的ルール（年齢→未成年フラグ等）
   - `derived_column`: 他列からの派生
   - `free_text_template`: テンプレート文字列

2. **統計量の利用方針**を決定（どの統計をサンプルから引き継ぐか、どこから data_spec.md の指定値を優先するか）。

3. **列間関係を特定**:
   - 数値相関（年齢×金額など）
   - 日付の前後関係
   - コードと名称の対応
   - ステータスと日付の整合
   - 親子関係（FK）

4. **複雑な制約は post sampling に回す** ことを明記。

5. **oversampling 倍率を決定**: post sampling 後に指定件数を確保できる倍率。違反がほぼ出ない設計なら 1.05 倍程度で十分。

6. **複数テーブル**の場合は、生成順序を明示（親→子）し、子テーブルの FK 制約、在籍/有効期間内のサンプリング方針を記述する。

## ルール

- 生成ロジックは説明可能であること。
- 実データの特定レコードを再現しないこと。
- サンプルデータの分布を過度にコピーしないこと。
- 乱数 seed により再現可能にすること。
- 仕様が不明な列は、保守的な生成方法を選ぶ。

## Acceptance Criteria

- 全列に生成方式が割り当てられている。
- post sampling 対象の制約が明示されている。
- 生成ロジックの根拠（仕様メモまたはサンプル統計）が記載されている。
- 複数テーブル構成の場合、生成順序と参照整合性の保証方法が記述されている。

## 参考

完全な仕様は `docs/spec.md` の `SKILL: 2_generation_plan` 節を参照。
既存実装の参考: `examples/customer/work/generation_plan.md`, `examples/customer_transactions/work/generation_plan.md`。
