---
name: 3_evaluate_and_refine
description: タスクディレクトリ ($ARGUMENTS) の合成データを、仕様・サンプル・制約に照らして評価し、品質課題があれば generator.py を修正して再生成・再評価する。evaluation_report.md と constraints_check.csv を出力する。
---

# 3_evaluate_and_refine

合成データの品質と制約充足を評価し、品質課題があれば生成器を refine して再生成・再評価するステップ。

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
- `$ARGUMENTS/output/quality_gate.json`

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

4. **品質ゲートを `quality_gate.json` に出力**:
   - `status`: `pass` または `fail`
   - `requires_refinement`: 生成器修正と再評価が必要なら `true`
   - `blocking_issues`: 仕様違反、必須制約違反、スキーマ不一致など修正必須の課題
   - `warnings`: 統計的差異、サンプル不足、追加仕様が必要な非ブロッキング課題
   - `summary`: PM エージェント向けの短い判定理由

5. **evaluation_report.md** に以下を記載:
   - 入力概要（件数、対象テーブル）
   - スキーマ評価
   - 分布評価（数値列・カテゴリ列）
   - 列間関係 / 相関評価
   - 制約評価
   - 品質ゲート（`quality_gate.json` の要約）
   - 主な所見・OK/NG 判定
   - 注意事項（匿名加工情報ではない旨など）

6. **重大な問題があれば generator.py を修正**:
   - 型不一致
   - 必須制約違反
   - 明らかな値域逸脱
   - 欠損率の大幅乖離
   - カテゴリ値の仕様違反

   修正後は generator.py を再実行して合成データを作り直し、`2_generator_impl` の Acceptance Criteria を再確認する。

7. **修正後に再評価する**:
   - 修正後の出力 CSV に対して evaluate.py を再実行する。
   - `constraints_check.csv`、`quality_gate.json`、`evaluation_report.md` を更新する。
   - 改善した項目、残った課題、追加仕様が必要な項目を `evaluation_report.md` に明記する。
   - 仕様違反ではない統計的差異は、生成器に過剰適合させず「既知の限界」として扱う。

8. **既存ロジックの再利用**:
   - 他タスクの evaluate.py の関数 (`check_constraints` 等) を `importlib` で再利用しても良い（例: `examples/customer_transactions/src/evaluate.py`）。

## ルール

- 評価結果をごまかさない。
- サンプルデータに過剰適合させない。
- 仕様違反と統計的差異を区別する。
- 修正した場合は、必ず再生成と再評価まで行う。
- 匿名加工済みデータであるとは記載しない。
- 合成データの利用範囲（PoC・モック・分析仮説検討用途）を明示する。

## Acceptance Criteria

- `evaluation_report.md` が生成されている。
- `constraints_check.csv` が生成されている。
- `quality_gate.json` が生成され、`status` と `requires_refinement` が機械可読に記録されている。
- 重大な仕様違反がない（または 0 件である）。
- 品質課題に対応して generator.py を修正した場合、修正後データで再評価済みである。
- 残課題がある場合、その理由と追加で必要な仕様が明記されている。
- 既知の限界が明記されている。

## 参考

完全な仕様は `docs/spec.md` の `SKILL: 3_evaluate_and_refine` 節を参照。
既存実装の参考:
- 単一テーブル: `examples/customer/src/evaluate.py`
- 複数テーブル: `examples/customer_transactions/src/evaluate.py`
