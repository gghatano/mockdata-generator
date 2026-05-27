---
name: 0_input_prepare
description: タスクディレクトリ ($ARGUMENTS) の原データ・仕様書・業務ドキュメントを読み取り、合成データ生成パイプラインが参照する input/ 配下の table_definition、sample_data、data_spec.md、constraints.md を作成・更新する。
---

# 0_input_prepare

合成データ生成パイプラインの前処理ステップ。

原データ、既存CSV、Excel、PDF、Markdown、テキスト、DDL、API仕様、業務説明資料などから、後続の `1_spec_ingest` が読める `input/` を作成する。

## 引数

`$ARGUMENTS` にタスクのルートディレクトリを受け取る。
例: `examples/university_enrollment`

## 入力

`$ARGUMENTS/source/` 配下、またはユーザーが明示した原資料。`source/` を原資料の正本として扱う。典型例:

- `source/raw_data/`, `source/table_definitions/`, `source/docs/`, `source/notes/` 配下のファイル
- 互換的に `raw/`, `docs/`, `input_sources/` 配下のファイル
- 既存の業務CSV / TSV / Excel
- テーブル定義書、ER図、DDL、データ辞書
- 仕様書、README、業務ルール、制約メモ
- サンプルデータ、ダンプデータ、匿名化済みデータ

## 出力

`$ARGUMENTS/input/` 配下に、後続ステップが利用するファイルを作成・更新する。

単一テーブルの場合:

- `$ARGUMENTS/input/table_definition.csv`
- `$ARGUMENTS/input/sample_data.csv`
- `$ARGUMENTS/input/data_spec.md`
- `$ARGUMENTS/input/constraints.md`

複数テーブルの場合:

- `$ARGUMENTS/input/<table>_table_definition.csv`
- `$ARGUMENTS/input/<table>_sample_data.csv`
- `$ARGUMENTS/input/data_spec.md`
- `$ARGUMENTS/input/constraints.md`

必要に応じて、出典と判断根拠を `$ARGUMENTS/input/source_inventory.md` に記録してよい。

## タスク

1. **原資料を棚卸しする**:
   - ファイル種別、対象テーブル、抽出できそうな情報、利用可否を確認する。
   - 読めないファイルや不足資料があれば明示する。

2. **テーブル定義を抽出する**:
   - column_name, logical_name, data_type, nullable, description, allowed_values, min_value, max_value, format, primary_key, foreign_key を可能な範囲で整理する。
   - 明示仕様と推定仕様を区別する。
   - 不明な項目は空欄または `unknown` とし、推測で確定しない。

3. **サンプルデータを作成する**:
   - 原データがある場合は、後続の統計推定に使える代表的なサンプルを抽出する。
   - 個人情報や機微情報を含む可能性がある値は、直接コピーせず、マスク・一般化・削除する。
   - サンプル件数が大きい場合は、分布が大きく崩れない範囲で小さくする。

4. **業務仕様を `data_spec.md` に整理する**:
   - ドメイン概要、テーブル概要、列の意味、値の範囲、代表的な分布、列間関係を記載する。
   - 原資料から明示的に読み取れた事項と、作業上の仮定を分けて書く。

5. **制約を `constraints.md` に整理する**:
   - 必須制約、推奨制約、参照整合性、日付前後関係、禁止値、生成してはいけない値を整理する。
   - 後続で評価可能な形になるよう、できるだけ具体的に記載する。

6. **既存 `input/` がある場合は慎重に更新する**:
   - 既存ファイルを上書きする前に内容を確認する。
   - 既存仕様と原資料が矛盾する場合は、勝手に片方へ寄せず、矛盾点を `data_spec.md` または `source_inventory.md` に記録する。

## ルール

- 原資料の内容を、後続パイプライン向けに整理することが目的。生成器や評価器は作らない。
- `source/` を原資料の正本、`input/` を整形済み入力として扱う。
- 個人情報や機微情報を `input/` に直接残さない。
- 原データの実レコードをそのまま再配布可能な形でコピーしない。
- 推定した仕様は、明示仕様と区別する。
- 不明点を都合よく補完しない。必要なら `assumption` または「未確認」として記録する。
- ファイル形式の変換では、列名・型・制約の意味が変わらないようにする。

## Acceptance Criteria

- `$ARGUMENTS/input/` が存在する。
- 1つ以上の `*table_definition*` ファイルが作成または更新されている。
- 1つ以上の `*sample_data*` ファイルが作成または更新されている。
- `$ARGUMENTS/input/data_spec.md` が作成または更新されている。
- `$ARGUMENTS/input/constraints.md` が作成または更新されている。
- 明示仕様、推定仕様、仮定、不明点が区別されている。
- 個人情報や機微情報を直接コピーしていない。

## 参考

後続ステップ: `.agents/skills/1_spec_ingest/SKILL.md`
既存の `input/` 例: `examples/customer/input/`, `examples/customer_transactions/input/`, `examples/university_enrollment/input/`
