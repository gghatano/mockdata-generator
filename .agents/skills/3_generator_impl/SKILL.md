---
name: 3_generator_impl
description: タスクディレクトリ ($ARGUMENTS) の generation_plan.md に基づき、src/generator.py を実装し、output/ に合成データを生成する。
---

# 3_generator_impl

設計に基づき、再実行可能な Python 生成器を実装するステップ。

## 引数

`$ARGUMENTS` にタスクのルートディレクトリを受け取る。

## 入力

- `$ARGUMENTS/work/generation_plan.md`
- `$ARGUMENTS/work/inferred_schema.json`
- `$ARGUMENTS/work/constraint_plan.md`
- `$ARGUMENTS/input/*sample_data*`（単一: `sample_data.csv` / 複数: `<table>_sample_data.csv`）

## 出力

- `$ARGUMENTS/src/generator.py`
- 合成データ:
  - 単一テーブル: `$ARGUMENTS/output/synthetic_data.csv`
  - 複数テーブル: `$ARGUMENTS/output/<table>.csv`（テーブル名に応じてファイル分割）

## タスク

1. **src/generator.py を実装する**。

2. **CLI**:
   - 単一テーブル: `--rows`, `--seed`, `--output` を取る。
   - 複数テーブル: 親テーブルの件数 (`--customers` 等の意味のある名前), `--seed`, テーブル別の `--<table>-output` を取る。

   例:
   ```bash
   uv run python $ARGUMENTS/src/generator.py --rows 10000 --seed 42 \
     --output $ARGUMENTS/output/synthetic_data.csv
   ```

3. **generator.py の必須要件**:
   - `pandas.DataFrame` を生成する
   - `numpy.random.default_rng(seed)` を使う
   - 生成件数を指定できる
   - seed を指定できる
   - CSV 出力（UTF-8）
   - post sampling を実行する
   - 削除件数・上書き件数を stderr にログ出力する

4. **post sampling**:
   - generation_constraint で表現しにくい複合制約は、生成後にフィルタ/上書きする。
   - 「削除」と「上書き」を区別して件数を記録する。
   - 不足件数が出た場合は再サンプリングで補う。

5. **複数テーブル**:
   - 親テーブルを先に生成。
   - 子テーブルは親から member_id/PK をサンプルして FK を埋める。
   - 親の状態（在籍期間、ステータス）に応じた制約を満たす範囲でサンプリング。

6. **既存ロジックの再利用**:
   - 他タスクの generator.py に再利用できるロジックがあれば、`importlib.util` で読み込んでも良い（テスト済みの例: `examples/customer_transactions/src/generator.py`）。
   - その際は `sys.modules` に登録してから `exec_module` する（`@dataclass` 対策）。

7. **生成後の検証**:
   - 実行して `output/<table>.csv` を生成し、件数・スキーマを確認。
   - 制約違反が 0 件であることを uv run python で確認。

## ルール

- 生成コードは再実行可能にする。
- 外部 API には依存しない。
- 個人情報を直接含めない。
- サンプルデータの行をそのままコピーしない。
- 出力 CSV は UTF-8 で書く。
- 列名・列順は inferred_schema.json と整合させる。

## Acceptance Criteria

- `generator.py` がエラーなく実行できる。
- 指定件数の CSV が生成される。
- 列名と型が `inferred_schema.json` と整合している。
- post sampling の削除件数・上書き件数が確認できる。
- 必須制約の違反が 0 件（または許容できる極小値）である。

## 参考

完全な仕様は `docs/spec.md` の `SKILL: 3_generator_impl` 節を参照。
既存実装の参考:
- 単一テーブル: `examples/customer/src/generator.py`
- 複数テーブル: `examples/customer_transactions/src/generator.py`（importlib による再利用例も含む）
