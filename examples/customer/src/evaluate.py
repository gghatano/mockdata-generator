"""合成データ評価器。

生成データを inferred_schema.json / constraints / サンプルデータと比較し、
output/evaluation_report.md / output/constraints_check.csv /
output/quality_gate.json を出力する。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


# --- 制約チェック -----------------------------------------------------------

PLATINUM_MIN_SPEND = 500_000
AGE_MIN, AGE_MAX = 0, 110
SPEND_MIN, SPEND_MAX = 0, 3_000_000
ALLOWED_GENDER = {1, 2, 9}
ALLOWED_RANK = {"BRONZE", "SILVER", "GOLD", "PLATINUM"}
ALLOWED_CHANNEL = {"WEB", "STORE", "APP", "PHONE"}
ALLOWED_PREFS = {f"{i:02d}" for i in range(1, 48)}


def check_constraints(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    def add(cid: str, name: str, count: int, total: int, sample: str = "") -> None:
        rows.append(
            {
                "constraint_id": cid,
                "constraint": name,
                "violations": count,
                "total": total,
                "violation_rate": round(count / total, 6) if total else 0.0,
                "sample_violation": sample,
            }
        )

    n = len(df)

    # C1: member_id 一意性
    dup = df["member_id"].duplicated()
    add("C1", "member_id 一意性", int(dup.sum()), n,
        df.loc[dup, "member_id"].head(1).to_string(index=False) if dup.any() else "")

    # C2: leave_date >= join_date（leave_date 非null時）
    leave_str = df["leave_date"].astype(str).fillna("")
    has_leave = (leave_str != "") & (leave_str != "nan")
    c2_mask = has_leave & (leave_str < df["join_date"].astype(str))
    sample = df.loc[c2_mask, ["member_id", "join_date", "leave_date"]].head(1).to_dict(orient="records")
    add("C2", "leave_date >= join_date", int(c2_mask.sum()), int(has_leave.sum()),
        str(sample[0]) if sample else "")

    # C3: age<18 → has_spouse=0
    c3_mask = (df["age"] < 18) & (df["has_spouse"] == 1)
    add("C3", "age<18 → has_spouse=0", int(c3_mask.sum()), int((df["age"] < 18).sum()),
        str(df.loc[c3_mask, ["member_id", "age", "has_spouse"]].head(1).to_dict(orient="records")) if c3_mask.any() else "")

    # C4: PLATINUM → annual_spend >= 500000
    is_plat = df["member_rank"] == "PLATINUM"
    c4_mask = is_plat & (df["annual_spend"] < PLATINUM_MIN_SPEND)
    add("C4", "PLATINUM → annual_spend >= 500_000", int(c4_mask.sum()), int(is_plat.sum()),
        str(df.loc[c4_mask, ["member_id", "annual_spend"]].head(1).to_dict(orient="records")) if c4_mask.any() else "")

    # C5: 値域
    c5_age = (df["age"] < AGE_MIN) | (df["age"] > AGE_MAX)
    add("C5a", f"age ∈ [{AGE_MIN},{AGE_MAX}]", int(c5_age.sum()), n, "")
    c5_spend = (df["annual_spend"] < SPEND_MIN) | (df["annual_spend"] > SPEND_MAX)
    add("C5b", f"annual_spend ∈ [{SPEND_MIN},{SPEND_MAX}]", int(c5_spend.sum()), n, "")

    # C6: コード値
    add("C6a", "gender ∈ {1,2,9}", int((~df["gender"].isin(ALLOWED_GENDER)).sum()), n, "")
    add("C6b", "member_rank ∈ {BRONZE,SILVER,GOLD,PLATINUM}",
        int((~df["member_rank"].isin(ALLOWED_RANK)).sum()), n, "")
    add("C6c", "registration_channel ∈ {WEB,STORE,APP,PHONE}",
        int((~df["registration_channel"].isin(ALLOWED_CHANNEL)).sum()), n, "")
    add("C6d", "prefecture_code ∈ 01..47",
        int((~df["prefecture_code"].astype(str).isin(ALLOWED_PREFS)).sum()), n, "")

    return pd.DataFrame(rows)


# --- 推奨制約（C7/C8）の機械判定 -------------------------------------------

# C7: gender 構成比 1:2:9 = 45:50:5（±5pt 程度）
GENDER_TARGET = {1: 0.45, 2: 0.50, 9: 0.05}
GENDER_TOLERANCE_PT = 0.05

# C8: 年代別 has_spouse=1 比率レンジ（constraints.md より）
#  20代未満(<20) は 10% 以下、30代(30-39) は 40〜70%、40代以上(>=40) は 60〜85%。
C8_BANDS = [
    {"label": "<20", "predicate": lambda a: a < 20, "lo": 0.0, "hi": 0.10},
    {"label": "30-39", "predicate": lambda a: (a >= 30) & (a <= 39), "lo": 0.40, "hi": 0.70},
    {"label": "40+", "predicate": lambda a: a >= 40, "lo": 0.60, "hi": 0.85},
]


def check_recommended(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """推奨制約 C7/C8 を OK/NG で判定し、(判定行 DataFrame, warning issue リスト) を返す。

    仕様違反ではない統計差のため warning 扱い（blocking にしない）。
    """
    rows: list[dict] = []
    warnings: list[dict] = []
    n = len(df)

    # C7: gender 構成比
    freq = df["gender"].value_counts(normalize=True)
    c7_details = []
    c7_ok = True
    for code, target in GENDER_TARGET.items():
        actual = float(freq.get(code, 0.0))
        diff = actual - target
        ok = abs(diff) <= GENDER_TOLERANCE_PT
        c7_ok = c7_ok and ok
        c7_details.append(
            {"gender": code, "actual": round(actual, 4), "target": target, "diff_pt": round(diff, 4)}
        )
    rows.append(
        {
            "constraint_id": "C7",
            "severity": "recommended",
            "constraint": "gender 構成比 45:50:5 (±5pt)",
            "result": "OK" if c7_ok else "NG",
            "detail": str(c7_details),
        }
    )
    if not c7_ok:
        warnings.append(
            issue(
                "recommended_C7_gender_ratio",
                "warning",
                "distribution",
                "gender 構成比が目標(45:50:5)から ±5pt を超えて乖離しています。",
                column="gender",
                requires_generator_fix=False,
                evidence={"bands": c7_details, "tolerance_pt": GENDER_TOLERANCE_PT},
            )
        )

    # C8: 年代別 has_spouse=1 比率レンジ
    c8_details = []
    c8_ok = True
    for band in C8_BANDS:
        mask = band["predicate"](df["age"])
        cnt = int(mask.sum())
        ratio = float(df.loc[mask, "has_spouse"].mean()) if cnt else 0.0
        ok = (cnt == 0) or (band["lo"] <= ratio <= band["hi"])
        c8_ok = c8_ok and ok
        c8_details.append(
            {
                "band": band["label"],
                "count": cnt,
                "spouse_ratio": round(ratio, 4),
                "range": [band["lo"], band["hi"]],
                "ok": ok,
            }
        )
    rows.append(
        {
            "constraint_id": "C8",
            "severity": "recommended",
            "constraint": "年代別 has_spouse 比率レンジ",
            "result": "OK" if c8_ok else "NG",
            "detail": str(c8_details),
        }
    )
    if not c8_ok:
        warnings.append(
            issue(
                "recommended_C8_spouse_by_age",
                "warning",
                "distribution",
                "年代別 has_spouse=1 比率が想定レンジ外の年代があります。",
                column="has_spouse",
                requires_generator_fix=False,
                evidence={"bands": c8_details},
            )
        )

    return pd.DataFrame(rows), warnings


# --- スキーマ整合 -----------------------------------------------------------


def _is_missing(series: pd.Series) -> pd.Series:
    """空文字・NaN・"nan"/"NaN" 文字列を欠損とみなすマスクを返す。"""
    s = series.astype(str)
    return series.isna() | s.isin(["", "nan", "NaN", "NaT", "None"])


def _data_type_ok(series: pd.Series, data_type: str) -> tuple[bool, str]:
    """非欠損値が宣言 data_type と整合するか判定する。

    int: 整数として解釈できること。
    date: YYYY-MM-DD としてパースできること。
    string: 制約なし（常に OK）。
    """
    non_null = series[~_is_missing(series)].astype(str)
    if len(non_null) == 0:
        return True, ""
    if data_type == "int":
        coerced = pd.to_numeric(non_null, errors="coerce")
        bad = coerced.isna() | (coerced != coerced.round())
        if bad.any():
            return False, str(non_null[bad].head(1).to_list())
        return True, ""
    if data_type == "date":
        coerced = pd.to_datetime(non_null, format="%Y-%m-%d", errors="coerce")
        bad = coerced.isna()
        if bad.any():
            return False, str(non_null[bad].head(1).to_list())
        return True, ""
    # string / その他は型制約なし
    return True, ""


def check_schema(df: pd.DataFrame, schema: dict) -> list[str]:
    """列名・列順に加え、data_type 整合と nullable=false 列の欠損を点検する。"""
    notes = []
    declared = [c["column_name"] for c in schema["columns"]]
    actual = list(df.columns)
    if declared != actual:
        missing = set(declared) - set(actual)
        extra = set(actual) - set(declared)
        notes.append(f"列順または列名が不一致 (missing={sorted(missing)}, extra={sorted(extra)})")
        return notes

    notes.append("列名・列順ともに inferred_schema.json と一致")

    # (a) data_type 整合 / (b) nullable=false 列の欠損
    type_issues: list[str] = []
    null_issues: list[str] = []
    for col in schema["columns"]:
        name = col["column_name"]
        if name not in df.columns:
            continue
        series = df[name]
        ok, sample = _data_type_ok(series, col.get("data_type", "string"))
        if not ok:
            type_issues.append(f"{name}({col.get('data_type')}): 例 {sample}")
        if col.get("nullable", False) is False:
            n_missing = int(_is_missing(series).sum())
            if n_missing > 0:
                null_issues.append(f"{name}: 欠損 {n_missing} 件")

    if type_issues:
        notes.append("data_type 不整合: " + "; ".join(type_issues))
    else:
        notes.append("data_type は全列で整合")
    if null_issues:
        notes.append("nullable=false 列の欠損: " + "; ".join(null_issues))
    else:
        notes.append("nullable=false 列の欠損なし")
    return notes


def schema_issues(df: pd.DataFrame, schema: dict) -> list[str]:
    """blocking 扱いにすべきスキーマ違反を文字列リストで返す（空なら OK）。"""
    problems: list[str] = []
    declared = [c["column_name"] for c in schema["columns"]]
    if declared != list(df.columns):
        problems.append("列名または列順が inferred_schema.json と一致しません。")
        return problems
    for col in schema["columns"]:
        name = col["column_name"]
        if name not in df.columns:
            continue
        series = df[name]
        ok, sample = _data_type_ok(series, col.get("data_type", "string"))
        if not ok:
            problems.append(
                f"列 {name} の値が data_type={col.get('data_type')} と不整合です（例 {sample}）。"
            )
        if col.get("nullable", False) is False:
            n_missing = int(_is_missing(series).sum())
            if n_missing > 0:
                problems.append(
                    f"nullable=false の列 {name} に欠損が {n_missing} 件あります。"
                )
    return problems


def schema_matches(df: pd.DataFrame, schema: dict) -> bool:
    return not schema_issues(df, schema)


# --- 分布比較 ---------------------------------------------------------------


def compare_categorical(synth: pd.Series, sample: pd.Series) -> pd.DataFrame:
    a = synth.value_counts(normalize=True).rename("synthetic")
    b = sample.value_counts(normalize=True).rename("sample")
    out = pd.concat([a, b], axis=1).fillna(0.0).sort_values("synthetic", ascending=False)
    out["diff_pt"] = (out["synthetic"] - out["sample"]).round(4)
    return out


def compare_numeric(synth: pd.Series, sample: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "synthetic": [synth.min(), synth.max(), synth.mean(), synth.std(), synth.median()],
            "sample": [sample.min(), sample.max(), sample.mean(), sample.std(), sample.median()],
        },
        index=["min", "max", "mean", "std", "median"],
    ).round(2)


# --- 品質ゲート -------------------------------------------------------------


def issue(
    issue_id: str,
    severity: str,
    category: str,
    message: str,
    *,
    table: str = "synthetic_data",
    column: str | None = None,
    requires_generator_fix: bool = False,
    evidence: dict | None = None,
) -> dict:
    return {
        "id": issue_id,
        "severity": severity,
        "category": category,
        "table": table,
        "column": column,
        "message": message,
        "requires_generator_fix": requires_generator_fix,
        "evidence": evidence or {},
    }


def build_quality_gate(
    *,
    constraints_df: pd.DataFrame,
    schema_ok: bool,
    relation_checks: dict[str, bool],
    warnings: list[dict] | None = None,
    schema_problems: list[str] | None = None,
) -> dict:
    blocking_issues: list[dict] = []
    warning_issues = warnings or []

    if not schema_ok:
        problems = schema_problems or [
            "列名・列順・data_type・nullable のいずれかが inferred_schema.json と一致しません。"
        ]
        blocking_issues.append(
            issue(
                "schema_mismatch",
                "blocking",
                "schema",
                "スキーマ検証に失敗しました: " + " / ".join(problems),
                requires_generator_fix=True,
                evidence={"problems": problems},
            )
        )

    violated = constraints_df[constraints_df["violations"] > 0]
    for row in violated.to_dict(orient="records"):
        table = str(row.get("table") or "synthetic_data")
        blocking_issues.append(
            issue(
                f"constraint_{row['constraint_id']}",
                "blocking",
                "constraint",
                f"{row['constraint']} に {int(row['violations'])} 件の違反があります。",
                table=table,
                requires_generator_fix=True,
                evidence={
                    "constraint_id": row["constraint_id"],
                    "violations": int(row["violations"]),
                    "total": int(row["total"]),
                    "violation_rate": float(row["violation_rate"]),
                    "sample_violation": str(row.get("sample_violation", "")),
                },
            )
        )

    for check_id, ok in relation_checks.items():
        if not ok:
            blocking_issues.append(
                issue(
                    check_id,
                    "blocking",
                    "relationship",
                    f"列間関係チェック {check_id} が NG です。",
                    requires_generator_fix=True,
                )
            )

    status = "fail" if blocking_issues else "pass"
    return {
        "status": status,
        "requires_refinement": bool(blocking_issues),
        "blocking_issue_count": len(blocking_issues),
        "warning_issue_count": len(warning_issues),
        "blocking_issues": blocking_issues,
        "warnings": warning_issues,
        "summary": "品質ゲートを通過しました。" if status == "pass" else "生成器修正が必要な品質課題があります。",
    }


def write_quality_gate(out_path: Path, quality_gate: dict) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(quality_gate, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


# --- レポート出力 -----------------------------------------------------------


def write_report(
    out_path: Path,
    sample_df: pd.DataFrame,
    synth_df: pd.DataFrame,
    schema: dict,
    constraints_df: pd.DataFrame,
    quality_gate: dict,
    recommended_df: pd.DataFrame | None = None,
    gen_command: dict | None = None,
) -> None:
    lines: list[str] = []
    lines.append("# 合成データ評価レポート")
    lines.append("")
    if gen_command:
        lines.append("## 生成条件")
        lines.append(f"- 生成コマンド: `{gen_command.get('invocation', '')}`")
        lines.append(f"- rows: {gen_command.get('rows')} / seed: {gen_command.get('seed')}")
        lines.append("")
    lines.append("## 入力概要")
    lines.append(f"- サンプル件数: {len(sample_df)}")
    lines.append(f"- 合成件数: {len(synth_df)}")
    lines.append(f"- 列数: {len(synth_df.columns)}")
    lines.append("")

    lines.append("## スキーマ評価")
    for note in check_schema(synth_df, schema):
        lines.append(f"- {note}")
    lines.append("")
    lines.append("### 欠損率比較")
    lines.append("| 列 | sample | synthetic |")
    lines.append("|----|-------:|----------:|")
    for col in synth_df.columns:
        s_null = (sample_df[col].astype(str).isin(["", "nan", "NaN"]) | sample_df[col].isna()).mean()
        y_null = (synth_df[col].astype(str).isin(["", "nan", "NaN"]) | synth_df[col].isna()).mean()
        lines.append(f"| {col} | {s_null:.3f} | {y_null:.3f} |")
    lines.append("")

    lines.append("## 数値列の分布")
    for col in ["age", "annual_spend"]:
        lines.append(f"### {col}")
        lines.append("")
        cmp = compare_numeric(synth_df[col], sample_df[col])
        lines.append(cmp.to_markdown())
        lines.append("")

    lines.append("## カテゴリ列の頻度")
    for col in ["gender", "member_rank", "registration_channel", "has_spouse", "email_optin"]:
        lines.append(f"### {col}")
        cmp = compare_categorical(synth_df[col].astype(str), sample_df[col].astype(str))
        lines.append(cmp.to_markdown())
        lines.append("")

    lines.append("## 列間関係")
    lines.append("### member_rank × annual_spend 平均")
    rank_mean = synth_df.groupby("member_rank")["annual_spend"].mean().round().astype(int)
    lines.append(rank_mean.to_frame("mean_annual_spend").to_markdown())
    lines.append("")

    lines.append("### 年代別 has_spouse=1 比率")
    bins = [-1, 17, 29, 39, 59, 200]
    labels = ["<18", "18-29", "30-39", "40-59", "60+"]
    synth_df = synth_df.copy()
    synth_df["age_bin"] = pd.cut(synth_df["age"], bins=bins, labels=labels)
    spouse = synth_df.groupby("age_bin", observed=True)["has_spouse"].agg(["count", "mean"]).round(3)
    lines.append(spouse.to_markdown())
    lines.append("")

    lines.append("## 制約評価（必須 C1〜C6）")
    lines.append(constraints_df.to_markdown(index=False))
    lines.append("")

    if recommended_df is not None and not recommended_df.empty:
        lines.append("## 推奨制約の機械判定（C7/C8: warning 扱い）")
        lines.append(
            recommended_df[["constraint_id", "constraint", "result", "detail"]].to_markdown(index=False)
        )
        lines.append("")

    total_violations = int(constraints_df["violations"].sum())
    lines.append("## 主な差異と所見")
    if total_violations == 0:
        lines.append("- 必須制約 C1〜C6 の違反は **0件**。")
    else:
        lines.append(f"- 必須制約に **{total_violations}件** の違反あり。詳細は constraints_check.csv を参照。")
    rank_mean_dict = rank_mean.to_dict()
    order_ok = (
        rank_mean_dict.get("BRONZE", 0)
        < rank_mean_dict.get("SILVER", 0)
        < rank_mean_dict.get("GOLD", 0)
        < rank_mean_dict.get("PLATINUM", 0)
    )
    lines.append(f"- C9 (rank × annual_spend の平均順序): {'OK' if order_ok else 'NG'}")
    if recommended_df is not None and not recommended_df.empty:
        for rec in recommended_df.to_dict(orient="records"):
            lines.append(f"- {rec['constraint_id']} ({rec['constraint']}): {rec['result']}")
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
    lines.append("- サンプル件数が少ない (n=40) ため、サンプルとの差異は仕様優先で評価している。")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="合成データ評価器")
    parser.add_argument("--sample", default="examples/customer/input/sample_data.csv")
    parser.add_argument("--synthetic", default="examples/customer/output/synthetic_data.csv")
    parser.add_argument("--schema", default="examples/customer/work/inferred_schema.json")
    parser.add_argument("--report", default="examples/customer/output/evaluation_report.md")
    parser.add_argument("--constraints", default="examples/customer/output/constraints_check.csv")
    parser.add_argument("--quality-gate", default="examples/customer/output/quality_gate.json")
    parser.add_argument("--generation-log", default="examples/customer/output/generation_log.json")
    args = parser.parse_args()

    sample_df = pd.read_csv(args.sample, dtype={"prefecture_code": str, "leave_date": str}, keep_default_na=False)
    synth_df = pd.read_csv(args.synthetic, dtype={"prefecture_code": str, "leave_date": str}, keep_default_na=False)
    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))

    constraints_df = check_constraints(synth_df)

    # 推奨制約 C7/C8 の機械判定（warning 扱い、blocking にしない）
    recommended_df, recommended_warnings = check_recommended(synth_df)

    # constraints_check.csv に必須(mandatory)＋推奨(recommended)を併記
    mandatory_out = constraints_df.copy()
    mandatory_out.insert(1, "severity", "mandatory")
    mandatory_out["result"] = mandatory_out["violations"].apply(lambda v: "OK" if v == 0 else "NG")
    combined = pd.concat([mandatory_out, recommended_df], ignore_index=True)
    Path(args.constraints).parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(args.constraints, index=False, encoding="utf-8")

    rank_mean = synth_df.groupby("member_rank")["annual_spend"].mean().round().astype(int).to_dict()
    relation_checks = {
        "rank_annual_spend_order": (
            rank_mean.get("BRONZE", 0)
            < rank_mean.get("SILVER", 0)
            < rank_mean.get("GOLD", 0)
            < rank_mean.get("PLATINUM", 0)
        )
    }
    schema_problems = schema_issues(synth_df, schema)
    quality_gate = build_quality_gate(
        constraints_df=constraints_df,
        schema_ok=not schema_problems,
        relation_checks=relation_checks,
        warnings=recommended_warnings,
        schema_problems=schema_problems,
    )
    write_quality_gate(Path(args.quality_gate), quality_gate)

    gen_command = None
    gen_log_path = Path(args.generation_log)
    if gen_log_path.exists():
        try:
            gen_command = json.loads(gen_log_path.read_text(encoding="utf-8")).get("command")
        except (json.JSONDecodeError, OSError):
            gen_command = None

    write_report(
        Path(args.report),
        sample_df,
        synth_df,
        schema,
        constraints_df,
        quality_gate,
        recommended_df=recommended_df,
        gen_command=gen_command,
    )

    print(f"[evaluate] wrote {args.report}")
    print(f"[evaluate] wrote {args.constraints}")
    print(f"[evaluate] wrote {args.quality_gate}")
    print(f"[evaluate] total violations: {int(constraints_df['violations'].sum())}")
    print(f"[evaluate] quality gate: {quality_gate['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
