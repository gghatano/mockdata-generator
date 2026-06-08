---
name: 4_evaluate_and_refine
description: タスクディレクトリ ($ARGUMENTS) の合成データを、仕様・サンプル・制約に照らして評価し、必要に応じて generator.py を修正する。evaluation_report.md と constraints_check.csv を出力する。
---

# 4_evaluate_and_refine

合成データの品質と制約充足を評価し、必要に応じて生成器を refine するステップ。

## 引数

`$ARGUMENTS` にタスクのルートディレクトリを受け取る。

## 入力

- `$ARGUMENTS/input/*sample_data*`（単一テーブル: `sample_data.csv` / 複数テーブル: `<table>_sample_data.csv`）
- 合成データ:
  - 単一テーブル: `$ARGUMENTS/output/synthetic_data.csv`
  - 複数テーブル: `$ARGUMENTS/output/<table>.csv`
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

4. **evaluation_report.md** に以下を記載:
   - 入力概要（件数、対象テーブル）
   - スキーマ評価
   - 分布評価（数値列・カテゴリ列）
   - 列間関係 / 相関評価
   - 制約評価
   - 主な所見・OK/NG 判定
   - 注意事項（匿名加工情報ではない旨など）
   - 残課題がある場合は「追加仕様が必要な点」または「既知の限界」として明記する

5. **`quality_gate.json` を出力する**（PM エージェントが改善ループの要否を機械可読に判定するためのゲート）。最低限以下を含める:
   - `status`: `pass` / `fail`
   - `requires_refinement`: generator.py の修正・再生成が必要なら `true`（boolean）
   - `blocking_issue_count`: blocking 課題の件数
   - `warning_issue_count`: warning 課題の件数
   - `blocking_issues[]`: 必須制約違反・スキーマ不一致・明示仕様違反など、修正が必要な課題の配列
   - `warnings[]`: 統計的差異・サンプル不足・追加仕様が必要な非ブロッキング課題の配列
   - `summary`: PM エージェント向けの短い判定理由

   重大度の定義:
   - **blocking**（= `requires_refinement: true` の根拠）: 必須制約違反 / スキーマ不一致（列名・列順・型）/ 明示仕様に反する値域・カテゴリ・日付関係。
   - **warning**: サンプル統計との差異、サンプル件数不足、追加仕様が必要な点など、仕様違反とは言えない課題。warning のみの場合は `status: pass` / `requires_refinement: false` とする。

   `blocking_issues[]` / `warnings[]` の各要素は `id, severity, category, table, column, message, requires_generator_fix, evidence` を持つ形を推奨（既存実装 `examples/customer/src/evaluate.py` の `build_quality_gate` 参照）。

6. **修正は最小限にとどめる**。このステップの責務は「評価して `quality_gate.json` と推奨修正を出す」ことであり、step4 内で延々と自己修正ループを回さない。
   - 評価中に気付いた **軽微で明白な修正**（型不一致、明らかな値域逸脱、カテゴリ値の仕様違反など）は、このステップで generator.py に反映してよい。その場合は修正後データで 1 回だけ再評価し、`3_generator_impl` の Acceptance Criteria を再確認する。
   - 構造的な作り直し（生成方式そのものの見直し等）が必要な場合は、自分で抱え込まず `quality_gate.json` の `blocking_issues` と `summary` に推奨修正を記載し、**最終的な再生成ループの判断は PM に委ねる**（PM が `3_generator_impl` を再委譲する）。

7. **既存ロジックの再利用**:
   - 他タスクの evaluate.py の関数 (`check_constraints`, `build_quality_gate` 等) を `importlib` で再利用しても良い（例: `examples/customer_transactions/src/evaluate.py`）。

## ルール

- 評価結果をごまかさない。
- サンプルデータに過剰適合させない。
- 仕様違反と統計的差異を区別する。
- 匿名加工済みデータであるとは記載しない。
- 合成データの利用範囲（PoC・モック・分析仮説検討用途）を明示する。

## Acceptance Criteria

- `evaluation_report.md` が生成されている。
- `constraints_check.csv` が生成されている。
- `quality_gate.json` が生成され、`status` と `requires_refinement` が機械可読に記録されている。
- 重大な仕様違反がない（または 0 件である）。
- 品質課題に対応して generator.py を修正した場合、修正後データで再評価済みである。
- 残課題がある場合、その理由と追加で必要な仕様が `evaluation_report.md` に明記されている。
- 既知の限界が明記されている。

## 参考

完全な仕様は `docs/spec.md` の `SKILL: 4_evaluate_and_refine` 節を参照。
既存実装の参考:
- 単一テーブル: `examples/customer/src/evaluate.py`
- 複数テーブル: `examples/customer_transactions/src/evaluate.py`
