"""ケース2: 顧客マスタ × 取引履歴 合成データ生成器。

仕様の根拠は
- examples/customer_transactions/work/inferred_schema.json
- examples/customer_transactions/work/generation_plan.md
- examples/customer_transactions/input/data_spec.md

顧客マスタ生成はケース1の `<project>/src/generator.py` を再利用する。
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# --- 顧客マスタ生成（ケース1の再利用）-------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_customer_gen_path = PROJECT_ROOT / "examples" / "customer" / "src" / "generator.py"
_spec = importlib.util.spec_from_file_location("customer_gen", _customer_gen_path)
_customer_gen = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["customer_gen"] = _customer_gen  # @dataclass がモジュール解決で sys.modules を参照するため
_spec.loader.exec_module(_customer_gen)

# --- ケース2固有の仕様 ----------------------------------------------------

REFERENCE_DATE = date(2026, 5, 20)

PRODUCT_CATEGORIES = ["FOOD", "DAILY", "APPAREL", "HOME", "BOOKS", "ELECTRONICS"]
_PROD_W = np.array([35, 18, 20, 12, 8, 7], dtype=float)
PRODUCT_WEIGHTS = _PROD_W / _PROD_W.sum()

CATEGORY_COEF = {
    "FOOD": 0.5, "DAILY": 0.4, "APPAREL": 1.3,
    "HOME": 1.8, "BOOKS": 0.6, "ELECTRONICS": 3.0,
}

RANK_TX_LAMBDA = {"BRONZE": 8.0, "SILVER": 18.0, "GOLD": 35.0, "PLATINUM": 55.0}

PAYMENTS = ["CASH", "CREDIT", "DEBIT", "EMONEY", "POINT"]
_PAY_W = np.array([15, 40, 15, 25, 5], dtype=float)
DEFAULT_PAY_WEIGHTS = _PAY_W / _PAY_W.sum()
HIGH_PAY_CHOICES = ["CREDIT", "DEBIT"]
HIGH_PAY_WEIGHTS = np.array([0.7, 0.3])

STORES = [f"S{i:03d}" for i in range(1, 51)]

AMOUNT_MIN, AMOUNT_MAX = 1, 500_000
QTY_MAX = 30
HIGH_AMOUNT_THRESHOLD = 50_000
ONE_YEAR_AGO = REFERENCE_DATE - timedelta(days=365)

POISSON_MU = {"FOOD": 3.0, "DAILY": 2.0, "APPAREL": 1.0, "HOME": 1.0, "BOOKS": 2.0}


@dataclass
class TxLog:
    customers: int
    transactions: int
    removed_t3: int  # 在籍期間外
    customers_no_tx: int


def _parse_date(s) -> date | None:
    if s is None or s == "" or pd.isna(s):
        return None
    if isinstance(s, date):
        return s
    return datetime.strptime(str(s), "%Y-%m-%d").date()


def _generate_tx_for_customer(
    rng: np.random.Generator,
    member_id: str,
    join_dt: date,
    leave_dt: date | None,
    member_rank: str,
    annual_spend: int,
) -> list[dict]:
    end_dt = min(leave_dt, REFERENCE_DATE) if leave_dt is not None else REFERENCE_DATE
    if end_dt < join_dt:
        return []

    span_days = (end_dt - join_dt).days + 1
    span_years = max(0.05, span_days / 365.25)

    n_tx = int(rng.poisson(RANK_TX_LAMBDA[member_rank] * span_years))
    if n_tx == 0:
        return []

    offsets = rng.integers(0, span_days, size=n_tx)
    tx_dates = [join_dt + timedelta(days=int(o)) for o in offsets]

    # 直近1年 / それ以前 で配分
    amounts = np.zeros(n_tx, dtype=float)
    recent_pos = [i for i, d in enumerate(tx_dates) if d >= ONE_YEAR_AGO]
    old_pos = [i for i, d in enumerate(tx_dates) if d < ONE_YEAR_AGO]

    if recent_pos:
        shares = rng.dirichlet([2.0] * len(recent_pos)) * float(annual_spend)
        for j, i in enumerate(recent_pos):
            amounts[i] = shares[j]

    if old_pos:
        years_arr = np.array([tx_dates[i].year for i in old_pos])
        for y in np.unique(years_arr):
            pos_in_old = np.where(years_arr == y)[0]
            tx_indices = [old_pos[k] for k in pos_in_old]
            scale = rng.uniform(0.7, 1.3)
            target = float(annual_spend) * scale
            shares = rng.dirichlet([2.0] * len(tx_indices)) * target
            for j, i in enumerate(tx_indices):
                amounts[i] = shares[j]

    # category
    categories = rng.choice(PRODUCT_CATEGORIES, size=n_tx, p=PRODUCT_WEIGHTS)
    coef = np.array([CATEGORY_COEF[c] for c in categories])
    mean_coef = coef.mean() if coef.mean() > 0 else 1.0
    amounts = amounts * coef / mean_coef
    amounts = np.clip(amounts, AMOUNT_MIN, AMOUNT_MAX).round().astype(int)
    amounts = np.maximum(amounts, AMOUNT_MIN)

    # quantity
    quantities = np.empty(n_tx, dtype=int)
    for i, cat in enumerate(categories):
        if cat == "ELECTRONICS":
            quantities[i] = 1 if rng.random() < 0.9 else 2
        else:
            quantities[i] = min(QTY_MAX, 1 + int(rng.poisson(POISSON_MU[cat])))

    # payment
    payments = np.empty(n_tx, dtype=object)
    high_mask = amounts >= HIGH_AMOUNT_THRESHOLD
    n_high = int(high_mask.sum())
    n_low = n_tx - n_high
    if n_high > 0:
        payments[high_mask] = rng.choice(HIGH_PAY_CHOICES, size=n_high, p=HIGH_PAY_WEIGHTS)
    if n_low > 0:
        payments[~high_mask] = rng.choice(PAYMENTS, size=n_low, p=DEFAULT_PAY_WEIGHTS)

    stores = rng.choice(STORES, size=n_tx)

    return [
        {
            "member_id": member_id,
            "transaction_date": tx_dates[i].strftime("%Y-%m-%d"),
            "store_code": stores[i],
            "product_category": categories[i],
            "quantity": int(quantities[i]),
            "amount": int(amounts[i]),
            "payment_method": str(payments[i]),
        }
        for i in range(n_tx)
    ]


def generate(customers: int, seed: int) -> tuple[pd.DataFrame, pd.DataFrame, TxLog]:
    rng = np.random.default_rng(seed)

    # 顧客マスタ: ケース1の generate() に同一 seed を渡す
    customer_df, _ = _customer_gen.generate(customers, seed)

    # 取引: 顧客ごとに生成
    tx_rng = np.random.default_rng(seed + 1)
    all_tx: list[dict] = []
    no_tx = 0

    for _, row in customer_df.iterrows():
        join_dt = _parse_date(row["join_date"])
        leave_dt = _parse_date(row["leave_date"])
        tx_list = _generate_tx_for_customer(
            tx_rng,
            row["member_id"],
            join_dt,
            leave_dt,
            row["member_rank"],
            int(row["annual_spend"]),
        )
        if not tx_list:
            no_tx += 1
        all_tx.extend(tx_list)

    tx_df = pd.DataFrame(all_tx)

    log = TxLog(
        customers=len(customer_df),
        transactions=len(tx_df),
        removed_t3=0,
        customers_no_tx=no_tx,
    )

    # post sampling: 在籍期間外チェック（理論上発生しないが念のため）
    if len(tx_df) > 0:
        cust_idx = customer_df.set_index("member_id")[["join_date", "leave_date"]]
        merged = tx_df.merge(cust_idx, left_on="member_id", right_index=True, how="left")
        bad = (merged["transaction_date"] < merged["join_date"]) | (
            (merged["leave_date"].astype(str) != "") & (merged["transaction_date"] > merged["leave_date"])
        ) | (merged["transaction_date"] > REFERENCE_DATE.isoformat())
        if bad.any():
            log.removed_t3 = int(bad.sum())
            tx_df = tx_df.loc[~bad.values].reset_index(drop=True)

    # transaction_id を付与（日付順にソートしてから付与）
    if len(tx_df) > 0:
        tx_df = tx_df.sort_values(["transaction_date", "member_id"]).reset_index(drop=True)
        tx_df.insert(0, "transaction_id", [f"T{i + 1:010d}" for i in range(len(tx_df))])
        # 列順を仕様に合わせる
        tx_df = tx_df[
            [
                "transaction_id", "member_id", "transaction_date", "store_code",
                "product_category", "quantity", "amount", "payment_method",
            ]
        ]

    log.transactions = len(tx_df)
    return customer_df, tx_df, log


def main() -> int:
    parser = argparse.ArgumentParser(description="顧客×取引 合成データ生成器")
    parser.add_argument("--customers", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--customer-output", type=str,
        default="examples/customer_transactions/output/customers.csv",
    )
    parser.add_argument(
        "--transaction-output", type=str,
        default="examples/customer_transactions/output/transactions.csv",
    )
    args = parser.parse_args()

    customer_df, tx_df, log = generate(args.customers, args.seed)

    cust_path = Path(args.customer_output)
    tx_path = Path(args.transaction_output)
    cust_path.parent.mkdir(parents=True, exist_ok=True)
    tx_path.parent.mkdir(parents=True, exist_ok=True)
    customer_df.to_csv(cust_path, index=False, encoding="utf-8")
    tx_df.to_csv(tx_path, index=False, encoding="utf-8")

    print(
        f"[generator] customers={log.customers} transactions={log.transactions} "
        f"customers_no_tx={log.customers_no_tx} removed_T3={log.removed_t3}",
        file=sys.stderr,
    )
    print(f"[generator] wrote {cust_path} and {tx_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
