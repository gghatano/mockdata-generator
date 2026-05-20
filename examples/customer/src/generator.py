"""顧客マスタ合成データ生成器。

仕様の根拠は docs/spec.md, work/inferred_schema.json, work/constraint_plan.md,
work/generation_plan.md を参照。
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# --- 仕様（generation_plan.md と整合）---------------------------------------

GENDER_VALUES = [1, 2, 9]
GENDER_WEIGHTS = [0.45, 0.50, 0.05]

RANKS = ["BRONZE", "SILVER", "GOLD", "PLATINUM"]
RANK_WEIGHTS = [0.45, 0.30, 0.18, 0.07]

CHANNELS = ["WEB", "STORE", "APP", "PHONE"]
CHANNEL_WEIGHTS = [0.40, 0.25, 0.25, 0.10]

# 都道府県：上位9 + 残り38を低めの均等
TOP_PREFS = ["13", "27", "14", "40", "11", "23", "28", "01", "12"]
TOP_PREF_WEIGHTS = [0.18, 0.10, 0.08, 0.06, 0.06, 0.06, 0.05, 0.04, 0.03]
OTHER_PREFS = [f"{i:02d}" for i in range(1, 48) if f"{i:02d}" not in TOP_PREFS]
# 残り (1 - 0.66) = 0.34 を 38都道府県に均等配分
OTHER_PREF_WEIGHT_EACH = (1.0 - sum(TOP_PREF_WEIGHTS)) / len(OTHER_PREFS)

ALL_PREFS = TOP_PREFS + OTHER_PREFS
ALL_PREF_WEIGHTS = TOP_PREF_WEIGHTS + [OTHER_PREF_WEIGHT_EACH] * len(OTHER_PREFS)

JOIN_DATE_MIN = date(2010, 1, 1)
JOIN_DATE_MAX = date(2025, 12, 31)
LEAVE_RATE = 0.15

AGE_MEAN = 40.0
AGE_STD = 17.0
AGE_MIN = 0
AGE_MAX = 110

# rank別 annual_spend パラメータ：(中央値, sigma, 下限)
RANK_SPEND_PARAMS: dict[str, tuple[float, float, int]] = {
    "BRONZE": (50_000, 0.7, 0),
    "SILVER": (200_000, 0.5, 0),
    "GOLD": (450_000, 0.4, 0),
    "PLATINUM": (800_000, 0.35, 500_000),
}
ANNUAL_SPEND_MAX = 3_000_000


def age_coefficient(age: np.ndarray) -> np.ndarray:
    """年齢から annual_spend に掛ける係数。25〜60歳をピークに 1.0、若年/高齢は低下。"""
    coef = np.full_like(age, 0.7, dtype=float)
    coef = np.where((age >= 18) & (age < 25), 0.8, coef)
    coef = np.where((age >= 25) & (age <= 60), 1.0, coef)
    coef = np.where((age > 60) & (age <= 75), 0.85, coef)
    coef = np.where(age > 75, 0.7, coef)
    return coef


def spouse_prob(age: np.ndarray) -> np.ndarray:
    """年齢別 has_spouse=1 となるベース確率。"""
    prob = np.zeros_like(age, dtype=float)
    prob = np.where((age >= 18) & (age < 30), 0.25, prob)
    prob = np.where((age >= 30) & (age < 40), 0.55, prob)
    prob = np.where((age >= 40) & (age < 60), 0.72, prob)
    prob = np.where(age >= 60, 0.78, prob)
    # age < 18 は 0 のまま（C3）
    return prob


# --- 生成本体 ---------------------------------------------------------------


@dataclass
class GenerationLog:
    requested_rows: int
    raw_generated: int
    removed_c2: int  # leave_date < join_date
    overwritten_c3: int  # age<18 & has_spouse=1 → 0 に上書き
    removed_c4_iterations: int  # PLATINUM 下限違反の再サンプリング回数
    final_rows: int


def _sample_dates(rng: np.random.Generator, n: int, lo: date, hi: date) -> np.ndarray:
    span = (hi - lo).days
    offsets = rng.integers(0, span + 1, size=n)
    base = np.datetime64(lo.isoformat())
    return base + offsets.astype("timedelta64[D]")


def _generate_block(rng: np.random.Generator, n: int, log: GenerationLog) -> pd.DataFrame:
    # gender
    gender = rng.choice(GENDER_VALUES, size=n, p=GENDER_WEIGHTS)

    # age: 切断正規。範囲外は再サンプル
    age = rng.normal(AGE_MEAN, AGE_STD, size=n).round().astype(int)
    mask = (age < AGE_MIN) | (age > AGE_MAX)
    while mask.any():
        age[mask] = np.round(rng.normal(AGE_MEAN, AGE_STD, size=mask.sum())).astype(int)
        mask = (age < AGE_MIN) | (age > AGE_MAX)

    # prefecture
    prefecture = rng.choice(ALL_PREFS, size=n, p=ALL_PREF_WEIGHTS)

    # join_date
    join_dt = _sample_dates(rng, n, JOIN_DATE_MIN, JOIN_DATE_MAX)

    # leave_date: 15% に派生。join_date + 1〜10年、上限 JOIN_DATE_MAX。
    has_leave = rng.random(n) < LEAVE_RATE
    leave_offset_days = rng.integers(365, 3650 + 1, size=n)
    leave_raw = join_dt + leave_offset_days.astype("timedelta64[D]")
    leave_clip = np.minimum(leave_raw, np.datetime64(JOIN_DATE_MAX.isoformat()))
    leave_dt = np.where(has_leave, leave_clip, np.datetime64("NaT"))

    # member_rank
    member_rank = rng.choice(RANKS, size=n, p=RANK_WEIGHTS)

    # annual_spend: rank別 log-normal × age係数。PLATINUM は下限を満たすまで再サンプル
    coef = age_coefficient(age)
    spend = np.zeros(n, dtype=float)
    for rank, (median, sigma, lower) in RANK_SPEND_PARAMS.items():
        idx = member_rank == rank
        if not idx.any():
            continue
        mu = np.log(median)
        draw = rng.lognormal(mean=mu, sigma=sigma, size=idx.sum()) * coef[idx]
        # C4: PLATINUM の下限を満たすまで再サンプル（reject sampling）
        if lower > 0:
            need = draw < lower
            iterations = 0
            while need.any() and iterations < 50:
                draw[need] = rng.lognormal(mean=mu, sigma=sigma, size=need.sum()) * coef[idx][need]
                need = draw < lower
                iterations += 1
            log.removed_c4_iterations += int((draw < lower).sum())
            # それでも未達なら下限値に強制
            draw = np.where(draw < lower, lower, draw)
        spend[idx] = draw
    annual_spend = np.clip(spend, 0, ANNUAL_SPEND_MAX).round().astype(int)

    # has_spouse: rule_based
    p_spouse = spouse_prob(age)
    has_spouse = (rng.random(n) < p_spouse).astype(int)
    # C3: age<18 は強制 0
    c3_violations = ((age < 18) & (has_spouse == 1)).sum()
    log.overwritten_c3 += int(c3_violations)
    has_spouse = np.where(age < 18, 0, has_spouse)

    # email_optin
    email_optin = (rng.random(n) < 0.70).astype(int)

    # channel
    channel = rng.choice(CHANNELS, size=n, p=CHANNEL_WEIGHTS)

    df = pd.DataFrame(
        {
            "gender": gender.astype(int),
            "age": age,
            "prefecture_code": prefecture,
            "join_date": pd.to_datetime(join_dt).strftime("%Y-%m-%d"),
            "leave_date": pd.Series(leave_dt).where(pd.notna(pd.Series(leave_dt)), None),
            "member_rank": member_rank,
            "annual_spend": annual_spend,
            "has_spouse": has_spouse.astype(int),
            "email_optin": email_optin,
            "registration_channel": channel,
        }
    )

    # leave_date を YYYY-MM-DD 文字列 or 空に整形
    df["leave_date"] = pd.to_datetime(df["leave_date"]).dt.strftime("%Y-%m-%d")
    df["leave_date"] = df["leave_date"].where(df["leave_date"].notna(), "")

    # C2 post sampling: leave_date >= join_date を確認
    has_leave_mask = df["leave_date"] != ""
    before_n = len(df)
    if has_leave_mask.any():
        violation = has_leave_mask & (df["leave_date"] < df["join_date"])
        log.removed_c2 += int(violation.sum())
        df = df.loc[~violation].reset_index(drop=True)
    _ = before_n  # noqa: F841

    return df


def generate(rows: int, seed: int) -> tuple[pd.DataFrame, GenerationLog]:
    rng = np.random.default_rng(seed)
    log = GenerationLog(
        requested_rows=rows,
        raw_generated=0,
        removed_c2=0,
        overwritten_c3=0,
        removed_c4_iterations=0,
        final_rows=0,
    )

    # oversampling 1.05倍 + 不足時の追加生成
    target = rows
    df = _generate_block(rng, int(target * 1.05) + 5, log)
    log.raw_generated = int(target * 1.05) + 5

    while len(df) < target:
        deficit = target - len(df)
        extra = _generate_block(rng, deficit + 5, log)
        log.raw_generated += deficit + 5
        df = pd.concat([df, extra], ignore_index=True)

    df = df.head(target).reset_index(drop=True)

    # member_id を最後に付与（C1）
    df.insert(0, "member_id", [f"M{i + 1:07d}" for i in range(len(df))])

    log.final_rows = len(df)
    return df, log


def main() -> int:
    parser = argparse.ArgumentParser(description="顧客マスタ合成データ生成器")
    parser.add_argument("--rows", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default="examples/customer/output/synthetic_data.csv")
    args = parser.parse_args()

    df, log = generate(args.rows, args.seed)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="utf-8")

    print(
        f"[generator] requested={log.requested_rows} "
        f"raw_generated={log.raw_generated} "
        f"final={log.final_rows} "
        f"removed_C2(leave<join)={log.removed_c2} "
        f"overwritten_C3(age<18&spouse)={log.overwritten_c3} "
        f"C4_PLATINUM_resamples={log.removed_c4_iterations}",
        file=sys.stderr,
    )
    print(f"[generator] wrote {out_path} ({len(df)} rows)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
