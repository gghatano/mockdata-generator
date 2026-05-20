---
name: 0_spec_ingest
description: タスクディレクトリ ($ARGUMENTS) の input/ を読み取り、合成データ生成に必要な仕様を機械可読化する。work/inferred_schema.json と work/constraint_plan.md を作成する。
---

# 0_spec_ingest

合成データ生成パイプラインの最初のステップ。

## 引数

`$ARGUMENTS` にタスクのルートディレクトリを受け取る。
例: `examples/university_enrollment`

## 入力

`$ARGUMENTS/input/` 配下のすべての関連ファイル。典型例：

- `*_table_definition.csv`（または `.xlsx`）: 列名・型・許容値・PK/FK などの仕様
- `*_sample_data.csv`: 統計量推定用サンプル
- `data_spec.md`: 業務ルールの自然言語仕様
- `constraints.md`: 必須/推奨制約

複数テーブルがある場合は、テーブル名がプレフィックスでファイル名に含まれている前提（`student_table_definition.csv` 等）。

## 出力

- `$ARGUMENTS/work/inferred_schema.json` — 機械可読なスキーマと統計量
- `$ARGUMENTS/work/constraint_plan.md` — 制約の分類（生成時 / post sampling / 評価のみ）

## タスク

1. **テーブル定義から抽出**: column_name, logical_name, data_type, nullable, description, allowed_values, min_value, max_value, format, primary_key, foreign_key。
2. **サンプルデータから推定**: 実データ型、欠損率、ユニーク数、代表値、数値列の min/max/mean/std、カテゴリ列の頻度、日付列の範囲。サンプル計算は uv run python で行う。
3. **data_spec.md / constraints.md を解釈**: 業務ルール、列間関係、生成不可な値（個人情報など）。
4. **制約を分類**して `constraint_plan.md` に記載:
   - `generation_constraint`: 生成時に直接反映する制約
   - `post_sampling_constraint`: 生成後にフィルタリング/上書きする制約
   - `validation_only_constraint`: 評価でのみ確認する制約
5. **複数テーブル**の場合は、`tables` キー配下に各テーブルのスキーマと、`relationships` キーに FK・列間関係を記述。

## ルール

- サンプルデータとテーブル定義書が矛盾する場合は、矛盾点を明示する。
- 推定した内容と明示仕様を区別する（`source: explicit` / `explicit+inferred`）。
- 不明な仕様は勝手に確定せず、`assumption` フィールドとして記録する。
- 個人情報を直接再現するような処理は行わない。
- サンプル件数が少ない場合は、構成比は data_spec.md の指定を優先する。

## Acceptance Criteria

- `$ARGUMENTS/work/inferred_schema.json` が生成されている。
- `$ARGUMENTS/work/constraint_plan.md` に制約分類が記載されている。
- 明示仕様・推定仕様・仮定が区別されている。
- 複数テーブル構成の場合、FK と列間関係が明示されている。

## 参考

完全な仕様は `docs/spec.md` の `SKILL: 0_spec_ingest` 節を参照。
既存実装の参考: `examples/customer/work/`, `examples/customer_transactions/work/`。
