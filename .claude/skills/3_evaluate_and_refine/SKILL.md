---
name: 3_evaluate_and_refine
description: タスクディレクトリ ($ARGUMENTS) の合成データを、仕様・サンプル・制約に照らして評価し、必要に応じて generator.py を修正する。evaluation_report.md と constraints_check.csv を出力する。
---

# 3_evaluate_and_refine

合成データの品質と制約充足を評価し、必要に応じて生成器を refine するステップ。

## 引数

`$ARGUMENTS` にタスクのルートディレクトリを受け取る。

## 入力

- `$ARGUMENTS/input/*_sample_data.csv`
- `$ARGUMENTS/output/<table>.csv`
- `$ARGUMENTS/work/inferred_schema.json`
- `$ARGUMENTS/work/constraint_plan.md`
- `$ARGUMENTS/src/generator.py`

## 出力

- `$ARGUMENTS/src/evaluate.py`
- `$ARGUMENTS/output/evaluation_report.md`
- `$ARGUMENTS/output/constraints_check.csv`

## タスク

1. **src/evaluate.py を実装する**。

2. **評価観点**:
   - 列名一致 / 型一致 / 欠損率
   - ユニーク数
   - 数値列の min / max / mean / std / median
   - カテゴリ列の頻度分布
   - 日付列の範囲
   - 主要な列間相関（rank × 金額、年齢 × 配偶者有無 等）
   - 制約違反件数（constraint_plan.md のすべての制約をチェック）
   - 複数テーブル: 参照整合性、子テーブルの値が親の制約内であること

3. **制約違反を `constraints_check.csv` に出力**:
   - 列: `table, constraint_id, constraint, violations, total, violation_rate, sample_violation`

4. **evaluation_report.md** に以下を記載:
   - 入力概要（件数、対象テーブル）
   - スキーマ評価
   - 分布評価（数値列・カテゴリ列）
   - 列間関係 / 相関評価
   - 制約評価
   - 主な所見・OK/NG 判定
   - 注意事項（匿名加工情報ではない旨など）

5. **重大な問題があれば generator.py を修正**:
   - 型不一致
   - 必須制約違反
   - 明らかな値域逸脱
   - 欠損率の大幅乖離
   - カテゴリ値の仕様違反

   修正後は `2_generator_impl` の Acceptance Criteria を再確認する。

6. **既存ロジックの再利用**:
   - 他タスクの evaluate.py の関数 (`check_constraints` 等) を `importlib` で再利用しても良い（例: `examples/customer_transactions/src/evaluate.py`）。

## ルール

- 評価結果をごまかさない。
- サンプルデータに過剰適合させない。
- 仕様違反と統計的差異を区別する。
- 匿名加工済みデータであるとは記載しない。
- 合成データの利用範囲（PoC・モック・分析仮説検討用途）を明示する。

## Acceptance Criteria

- `evaluation_report.md` が生成されている。
- `constraints_check.csv` が生成されている。
- 重大な仕様違反がない（または 0 件である）。
- 既知の限界が明記されている。

## 参考

完全な仕様は `docs/spec.md` の `SKILL: 3_evaluate_and_refine` 節を参照。
既存実装の参考:
- 単一テーブル: `examples/customer/src/evaluate.py`
- 複数テーブル: `examples/customer_transactions/src/evaluate.py`
