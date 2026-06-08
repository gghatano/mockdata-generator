"""ケース2: 顧客×取引 合成データ評価器。"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# 既存の評価ロジック（ケース1）を再利用 -------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "case1_evaluate", PROJECT_ROOT / "examples" / "customer" / "src" / "evaluate.py"
)
_case1 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["case1_evaluate"] = _case1
_spec.loader.exec_module(_case1)

REFERENCE_DATE = date(2026, 5, 20)
ONE_YEAR_AGO = REFERENCE_DATE - timedelta(days=365)

ALLOWED_STORES = {f"S{i:03d}" for i in range(1, 51)}
ALLOWED_CATEGORIES = {"FOOD", "DAILY", "APPAREL", "HOME", "BOOKS", "ELECTRONICS"}
ALLOWED_PAYMENTS = {"CASH", "CREDIT", "DEBIT", "EMONEY", "POINT"}


def check_case2_schema(
    cust: pd.DataFrame, tx: pd.DataFrame, schema: dict
) -> list[str]:
    """ケース2のスキーマ整合をチェックし、blocking 扱いの問題を文字列で返す（空なら OK）。

    customer / transaction 両テーブルについて
      - 列名・列順が inferred_schema.json と一致するか
      - 宣言された data_type と値が整合するか（case1 のロジックを再利用）
      - nullable=false の列に欠損がないか（case1 のロジックを再利用）
    を検証し、さらに transaction の FK 列（member_id）が定義どおり存在するかを確認する。
    """
    problems: list[str] = []
    tables = schema.get("tables", {})
    frames = {"customer": cust, "transaction": tx}

    for table_name, df in frames.items():
        tdef = tables.get(table_name)
        if tdef is None:
            problems.append(f"{table_name}: inferred_schema.json にテーブル定義がありません。")
            continue

        declared = [c["column_name"] for c in tdef["columns"]]
        actual = list(df.columns)
        if declared != actual:
            missing = sorted(set(declared) - set(actual))
            extra = sorted(set(actual) - set(declared))
            problems.append(
                f"{table_name}: 列名または列順が不一致 (missing={missing}, extra={extra})"
            )
            # 列が揃っていない段階で型・欠損チェックは無意味なのでスキップ
            continue

        # data_type / nullable の整合（case1 の判定ロジックを再利用）
        for col in tdef["columns"]:
            name = col["column_name"]
            series = df[name]
            ok, sample = _case1._data_type_ok(series, col.get("data_type", "string"))
            if not ok:
                problems.append(
                    f"{table_name}.{name}: 値が data_type={col.get('data_type')} と不整合 (例 {sample})"
                )
            # transaction の FK / PK 等、明示 nullable 指定がない列は非null前提
            if col.get("nullable", False) is False:
                n_missing = int(_case1._is_missing(series).sum())
                if n_missing > 0:
                    problems.append(
                        f"{table_name}.{name}: nullable=false の列に欠損が {n_missing} 件"
                    )

        # FK 列の存在確認
        for fk in tdef.get("foreign_keys", []):
            fk_col = fk.get("column")
            if fk_col and fk_col not in actual:
                problems.append(
                    f"{table_name}: FK列 {fk_col} が存在しません（references={fk.get('references')}）。"
                )

    return problems


def check_tx_constraints(tx: pd.DataFrame, cust: pd.DataFrame) -> pd.DataFrame:
    rows = []

    def add(cid: str, name: str, count: int, total: int) -> None:
        rows.append(
            {
                "constraint_id": cid,
                "constraint": name,
                "violations": int(count),
                "total": int(total),
                "violation_rate": round(count / total, 6) if total else 0.0,
            }
        )

    n = len(tx)

    # T1: transaction_id 一意
    add("T1", "transaction_id 一意", tx["transaction_id"].duplicated().sum(), n)

    # T2: FK
    fk_missing = (~tx["member_id"].isin(cust["member_id"])).sum()
    add("T2", "member_id FK 整合", fk_missing, n)

    # T3: 在籍期間内 & 基準日以前
    merged = tx.merge(
        cust[["member_id", "join_date", "leave_date"]],
        on="member_id", how="left",
    )
    merged["leave_date"] = merged["leave_date"].astype(str).replace("nan", "")
    before_join = merged["transaction_date"].astype(str) < merged["join_date"].astype(str)
    has_leave = merged["leave_date"] != ""
    after_leave = has_leave & (merged["transaction_date"].astype(str) > merged["leave_date"])
    after_ref = merged["transaction_date"].astype(str) > REFERENCE_DATE.isoformat()
    add("T3a", "transaction_date >= join_date", before_join.sum(), n)
    add("T3b", "transaction_date <= leave_date（退会者）", after_leave.sum(), int(has_leave.sum()))
    add("T3c", f"transaction_date <= {REFERENCE_DATE.isoformat()}", after_ref.sum(), n)

    # T4: amount >= 1
    add("T4", "amount >= 1", (tx["amount"] < 1).sum(), n)

    # T5: quantity >= 1
    add("T5", "quantity >= 1", (tx["quantity"] < 1).sum(), n)

    # T6: コード値
    add("T6a", "store_code ∈ S001..S050",
        (~tx["store_code"].astype(str).isin(ALLOWED_STORES)).sum(), n)
    add("T6b", "product_category 許容値",
        (~tx["product_category"].isin(ALLOWED_CATEGORIES)).sum(), n)
    add("T6c", "payment_method 許容値",
        (~tx["payment_method"].isin(ALLOWED_PAYMENTS)).sum(), n)

    # T7: 値域
    add("T7a", "amount ∈ [1, 500000]",
        ((tx["amount"] < 1) | (tx["amount"] > 500_000)).sum(), n)
    add("T7b", "quantity ∈ [1, 30]",
        ((tx["quantity"] < 1) | (tx["quantity"] > 30)).sum(), n)

    return pd.DataFrame(rows)


def evaluate_t8(tx: pd.DataFrame, cust: pd.DataFrame) -> dict:
    """直近1年の amount 合計 ≒ annual_spend を在籍顧客で評価。"""
    one_yr = ONE_YEAR_AGO.isoformat()
    cust = cust.copy()
    cust["leave_date_str"] = cust["leave_date"].astype(str).replace("nan", "")
    # 退会済みかつ leave_date < one_yr → 対象外
    left_before = (cust["leave_date_str"] != "") & (cust["leave_date_str"] < one_yr)
    active = cust.loc[~left_before, ["member_id", "annual_spend"]]

    recent = tx[tx["transaction_date"].astype(str) >= one_yr]
    recent_total = recent.groupby("member_id")["amount"].sum()
    actual = active["member_id"].map(recent_total).fillna(0).astype(int)
    ratio = (actual / active["annual_spend"].clip(lower=1)).replace([np.inf, -np.inf], np.nan).fillna(0)

    return {
        "n_active": int(len(active)),
        "n_excluded_left_before": int(left_before.sum()),
        "ratio_mean": round(float(ratio.mean()), 3),
        "ratio_median": round(float(ratio.median()), 3),
        "ratio_std": round(float(ratio.std()), 3),
        "within_25pct": round(float(ratio.between(0.75, 1.25).mean()), 3),
    }


def evaluate_t9(tx: pd.DataFrame, cust: pd.DataFrame) -> pd.DataFrame:
    one_yr = ONE_YEAR_AGO.isoformat()
    recent = tx[tx["transaction_date"].astype(str) >= one_yr]
    merged = recent.merge(cust[["member_id", "member_rank"]], on="member_id")
    counts = merged.groupby(["member_id", "member_rank"]).size().reset_index(name="n")
    return counts.groupby("member_rank")["n"].agg(["count", "mean", "median"]).round(2)


def evaluate_t10(tx: pd.DataFrame) -> dict:
    high = tx[tx["amount"] >= 50_000]
    n_high = len(high)
    n_card = int(high["payment_method"].isin(["CREDIT", "DEBIT"]).sum()) if n_high else 0
    return {
        "n_high": n_high,
        "credit_debit_rate": round(n_card / n_high, 3) if n_high else 0.0,
    }


def write_report(
    out_path: Path,
    cust: pd.DataFrame,
    tx: pd.DataFrame,
    c_violations: pd.DataFrame,
    t_violations: pd.DataFrame,
    t8: dict,
    t9: pd.DataFrame,
    t10: dict,
    quality_gate: dict,
    schema_problems: list[str] | None = None,
) -> None:
    lines: list[str] = []
    lines.append("# 合成データ評価レポート（ケース2: 顧客×取引）")
    lines.append("")
    lines.append("## 入力概要")
    lines.append(f"- 顧客件数: {len(cust)}")
    lines.append(f"- 取引件数: {len(tx)}")
    lines.append(f"- 基準日: {REFERENCE_DATE.isoformat()}")
    lines.append("")

    lines.append("## スキーマ評価")
    if schema_problems:
        lines.append("- 列名・列順・型・FK 検証で **NG**:")
        for p in schema_problems:
            lines.append(f"  - {p}")
    else:
        lines.append("- customer / transaction の列名・列順・data_type・nullable・FK列はすべて inferred_schema.json と整合。")
    lines.append("")

    lines.append("## customer 側 制約評価")
    lines.append(c_violations.to_markdown(index=False))
    lines.append("")

    lines.append("## transaction 側 制約評価")
    lines.append(t_violations.to_markdown(index=False))
    lines.append("")

    total_violations = int(c_violations["violations"].sum()) + int(t_violations["violations"].sum())

    lines.append("## 取引：列分布")
    for col in ["product_category", "payment_method", "store_code"]:
        lines.append(f"### {col}")
        s = tx[col].value_counts(normalize=True).round(4)
        lines.append(s.to_frame("ratio").head(15).to_markdown())
        lines.append("")

    lines.append("### amount 統計")
    lines.append(tx["amount"].describe().round(2).to_frame().to_markdown())
    lines.append("")
    lines.append("### quantity 統計")
    lines.append(tx["quantity"].describe().round(2).to_frame().to_markdown())
    lines.append("")

    lines.append("## T8: 直近1年の amount 合計 ≒ annual_spend")
    lines.append(f"- 対象（直近1年在籍）顧客: {t8['n_active']}")
    lines.append(f"- 除外（直近1年より前に退会）: {t8['n_excluded_left_before']}")
    lines.append(f"- ratio (actual / annual_spend): mean={t8['ratio_mean']}, median={t8['ratio_median']}, std={t8['ratio_std']}")
    lines.append(f"- ±25% 以内の顧客率: **{t8['within_25pct']}**")
    lines.append("")

    lines.append("## T9: rank別 直近1年取引件数")
    lines.append(t9.to_markdown())
    lines.append("")

    lines.append("## T10: 高額（>= 50,000円）取引の支払方法")
    lines.append(f"- 対象件数: {t10['n_high']}")
    lines.append(f"- CREDIT/DEBIT 比率: **{t10['credit_debit_rate']}**")
    lines.append("")

    lines.append("## 主な所見")
    if total_violations == 0:
        lines.append("- 必須制約 C1〜C6 / T1〜T7 すべて違反 **0件**。")
    else:
        lines.append(f"- 必須制約に **{total_violations}件** の違反あり。constraints_check.csv 参照。")
    rank_order_ok = list(t9["mean"].sort_values().index.tolist()) == ["BRONZE", "SILVER", "GOLD", "PLATINUM"]
    lines.append(f"- T9 (rank別件数の順序): {'OK' if rank_order_ok else 'NG'}")
    lines.append(f"- T10 (高額CREDIT/DEBIT >= 0.9): {'OK' if t10['credit_debit_rate'] >= 0.9 else 'NG'}")
    if t8["within_25pct"] >= 0.6:
        lines.append(f"- T8 (±25%以内 >= 0.6): OK ({t8['within_25pct']})")
    else:
        lines.append(f"- T8 (±25%以内 >= 0.6): NG ({t8['within_25pct']})")
    lines.append("")
    lines.append("## 品質ゲート")
    lines.append(f"- status: **{quality_gate['status']}**")
    lines.append(f"- requires_refinement: **{str(quality_gate['requires_refinement']).lower()}**")
    lines.append(f"- blocking_issues: {quality_gate['blocking_issue_count']}")
    lines.append(f"- warnings: {quality_gate['warning_issue_count']}")
    lines.append("- 機械可読な判定は `quality_gate.json` を参照。")
    lines.append("")
    lines.append("## 注意事項")
    lines.append("- 本データは仕様駆動の合成データであり、匿名加工情報ではない。")
    lines.append("- 実データの統計的再現性は保証しない。PoC・画面モック・分析仮説検討用途を想定。")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="ケース2: 評価器")
    parser.add_argument("--customers", default="examples/customer_transactions/output/customers.csv")
    parser.add_argument("--transactions", default="examples/customer_transactions/output/transactions.csv")
    parser.add_argument("--report", default="examples/customer_transactions/output/evaluation_report.md")
    parser.add_argument("--constraints", default="examples/customer_transactions/output/constraints_check.csv")
    parser.add_argument("--quality-gate", default="examples/customer_transactions/output/quality_gate.json")
    parser.add_argument("--schema", default="examples/customer_transactions/work/inferred_schema.json")
    args = parser.parse_args()

    cust = pd.read_csv(
        args.customers,
        dtype={"prefecture_code": str, "leave_date": str, "member_id": str},
        keep_default_na=False,
    )
    tx = pd.read_csv(
        args.transactions,
        dtype={"store_code": str, "transaction_id": str, "member_id": str},
        keep_default_na=False,
    )

    c_violations = _case1.check_constraints(cust)
    c_violations.insert(0, "table", "customer")

    t_violations = check_tx_constraints(tx, cust)
    t_violations.insert(0, "table", "transaction")

    all_violations = pd.concat([c_violations, t_violations], ignore_index=True)
    Path(args.constraints).parent.mkdir(parents=True, exist_ok=True)
    all_violations.to_csv(args.constraints, index=False, encoding="utf-8")

    t8 = evaluate_t8(tx, cust)
    t9 = evaluate_t9(tx, cust)
    t10 = evaluate_t10(tx)
    rank_order_ok = list(t9["mean"].sort_values().index.tolist()) == ["BRONZE", "SILVER", "GOLD", "PLATINUM"]
    relation_checks = {
        "t8_recent_amount_matches_annual_spend": t8["within_25pct"] >= 0.6,
        "t9_rank_transaction_count_order": rank_order_ok,
        "t10_high_amount_credit_debit_rate": t10["credit_debit_rate"] >= 0.9,
    }
    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    schema_problems = check_case2_schema(cust, tx, schema)

    quality_gate = _case1.build_quality_gate(
        constraints_df=all_violations,
        schema_ok=not schema_problems,
        relation_checks=relation_checks,
        schema_problems=schema_problems,
    )
    _case1.write_quality_gate(Path(args.quality_gate), quality_gate)

    write_report(
        Path(args.report), cust, tx, c_violations, t_violations, t8, t9, t10, quality_gate,
        schema_problems=schema_problems,
    )

    print(f"[evaluate] wrote {args.report}")
    print(f"[evaluate] wrote {args.constraints}")
    print(f"[evaluate] wrote {args.quality_gate}")
    print(
        f"[evaluate] violations: customer={int(c_violations['violations'].sum())} "
        f"transaction={int(t_violations['violations'].sum())}"
    )
    print(f"[evaluate] quality gate: {quality_gate['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
