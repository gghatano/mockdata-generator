"""ケース3: 大学履修 合成データ評価器（student / course / enrollment）。

仕様の根拠:
- examples/university_enrollment/work/inferred_schema.json
- examples/university_enrollment/work/constraint_plan.md
- examples/university_enrollment/input/constraints.md / data_spec.md
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

# --- 定数（generator.py と整合） -------------------------------------------------

REFERENCE_YEAR = 2025
ENROLLMENT_YEAR_MIN = 2018
ENROLLMENT_YEAR_MAX = 2025

ALLOWED_STUDENT_DEPT = {"LITERATURE", "SCIENCE", "ENGINEERING", "ECONOMICS", "MEDICAL"}
ALLOWED_COURSE_DEPT = {"LITERATURE", "SCIENCE", "ENGINEERING", "ECONOMICS", "MEDICAL", "COMMON"}
ALLOWED_GENDER = {1, 2, 9}
ALLOWED_STATUS = {"ENROLLED", "LEAVE", "GRADUATED", "WITHDRAWN"}
ALLOWED_SEMESTER = {"SPRING", "FALL", "FULL_YEAR"}
ALLOWED_GRADE_CODE = {"S", "A", "B", "C", "D", "F", "W"}

DEPT_MAX_GRADE = {
    "ENGINEERING": 4,
    "LITERATURE": 4,
    "SCIENCE": 4,
    "ECONOMICS": 4,
    "MEDICAL": 6,
}

STUDENT_ID_RE = re.compile(r"^S\d{8}$")
COURSE_CODE_RE = re.compile(r"^C\d{4}$")
ENROLLMENT_ID_RE = re.compile(r"^E\d{10}$")


# --- ユーティリティ ---------------------------------------------------------


def _mk_row(
    table: str,
    cid: str,
    name: str,
    violations: int,
    total: int,
    sample: str = "",
) -> dict:
    return {
        "table": table,
        "constraint_id": cid,
        "constraint": name,
        "violations": int(violations),
        "total": int(total),
        "violation_rate": round(violations / total, 6) if total else 0.0,
        "sample_violation": sample,
    }


def _head_sample(s: pd.Series, n: int = 1) -> str:
    if s.empty:
        return ""
    return str(s.head(n).tolist())


# --- student 制約チェック -----------------------------------------------------


def check_student_constraints(df: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    n = len(df)

    # S1: student_id 一意
    dup = df["student_id"].duplicated()
    rows.append(_mk_row(
        "student", "S1", "student_id 一意", int(dup.sum()), n,
        _head_sample(df.loc[dup, "student_id"]),
    ))

    # S2: enrollment_year ∈ [2018, 2025]
    s2_mask = (df["enrollment_year"] < ENROLLMENT_YEAR_MIN) | (df["enrollment_year"] > ENROLLMENT_YEAR_MAX)
    rows.append(_mk_row(
        "student", "S2",
        f"enrollment_year ∈ [{ENROLLMENT_YEAR_MIN},{ENROLLMENT_YEAR_MAX}]",
        int(s2_mask.sum()), n,
        _head_sample(df.loc[s2_mask, "enrollment_year"]),
    ))

    # S3: grade 上限は学部依存（MEDICAL=6, その他=4）
    max_grade_arr = df["department"].map(DEPT_MAX_GRADE)
    s3_mask = (df["grade"] < 1) | (df["grade"] > max_grade_arr.fillna(4))
    rows.append(_mk_row(
        "student", "S3", "grade 上限は学部依存（MEDICAL=6, その他=4）",
        int(s3_mask.sum()), n,
        str(df.loc[s3_mask, ["student_id", "department", "grade"]].head(1).to_dict(orient="records"))
        if s3_mask.any() else "",
    ))

    # S4: gpa ∈ [0, 4]
    s4_mask = (df["gpa"] < 0.0) | (df["gpa"] > 4.0)
    rows.append(_mk_row(
        "student", "S4", "gpa ∈ [0.0, 4.0]", int(s4_mask.sum()), n,
        _head_sample(df.loc[s4_mask, "gpa"]),
    ))

    # S5: コード値（department / gender / status）
    s5a = (~df["department"].isin(ALLOWED_STUDENT_DEPT)).sum()
    rows.append(_mk_row("student", "S5a", "department 許容値", int(s5a), n))
    s5b = (~df["gender"].isin(ALLOWED_GENDER)).sum()
    rows.append(_mk_row("student", "S5b", "gender ∈ {1,2,9}", int(s5b), n))
    s5c = (~df["status"].isin(ALLOWED_STATUS)).sum()
    rows.append(_mk_row("student", "S5c", "status 許容値", int(s5c), n))

    # S6: student_id 先頭4桁 = enrollment_year
    fmt_ok = df["student_id"].astype(str).str.match(STUDENT_ID_RE)
    head_year = df["student_id"].astype(str).str.slice(1, 5)
    s6_mask = (~fmt_ok) | (head_year != df["enrollment_year"].astype(int).astype(str).str.zfill(4))
    rows.append(_mk_row(
        "student", "S6", "student_id 先頭4桁 = enrollment_year",
        int(s6_mask.sum()), n,
        _head_sample(df.loc[s6_mask, "student_id"]),
    ))

    return rows


# --- course 制約チェック -----------------------------------------------------


def check_course_constraints(df: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    n = len(df)

    # CR1: course_code 一意
    dup = df["course_code"].duplicated()
    rows.append(_mk_row(
        "course", "CR1", "course_code 一意", int(dup.sum()), n,
        _head_sample(df.loc[dup, "course_code"]),
    ))

    # CR2: department / semester 許容値
    cr2a = (~df["department"].isin(ALLOWED_COURSE_DEPT)).sum()
    rows.append(_mk_row("course", "CR2a", "department 許容値（含む COMMON）", int(cr2a), n))
    cr2b = (~df["semester"].isin(ALLOWED_SEMESTER)).sum()
    rows.append(_mk_row("course", "CR2b", "semester 許容値", int(cr2b), n))

    # CR3: 値域
    cr3a = ((df["credits"] < 1) | (df["credits"] > 4)).sum()
    rows.append(_mk_row("course", "CR3a", "credits ∈ [1,4]", int(cr3a), n))
    cr3b = ((df["level"] < 1) | (df["level"] > 4)).sum()
    rows.append(_mk_row("course", "CR3b", "level ∈ [1,4]", int(cr3b), n))
    cr3c = ((df["max_students"] < 20) | (df["max_students"] > 300)).sum()
    rows.append(_mk_row("course", "CR3c", "max_students ∈ [20,300]", int(cr3c), n))

    # CR4: FULL_YEAR の credits 推奨 (3〜4)。必須ではないので参考のみ。
    is_full = df["semester"] == "FULL_YEAR"
    cr4 = (is_full & ((df["credits"] < 3) | (df["credits"] > 4))).sum()
    rows.append(_mk_row(
        "course", "CR4", "FULL_YEAR の credits は 3〜4 推奨（参考）",
        int(cr4), int(is_full.sum()),
    ))

    # 形式: course_code が C\d{4}
    fmt_ng = (~df["course_code"].astype(str).str.match(COURSE_CODE_RE)).sum()
    rows.append(_mk_row("course", "CR1f", "course_code 形式 C\\d{4}", int(fmt_ng), n))

    return rows


# --- enrollment 制約チェック -------------------------------------------------


def check_enrollment_constraints(
    enr: pd.DataFrame,
    stu: pd.DataFrame,
    crs: pd.DataFrame,
) -> list[dict]:
    rows: list[dict] = []
    n = len(enr)

    # E1: enrollment_id 一意
    dup = enr["enrollment_id"].duplicated()
    rows.append(_mk_row(
        "enrollment", "E1", "enrollment_id 一意", int(dup.sum()), n,
        _head_sample(enr.loc[dup, "enrollment_id"]),
    ))

    # 形式: enrollment_id が E\d{10}
    fmt_ng = (~enr["enrollment_id"].astype(str).str.match(ENROLLMENT_ID_RE)).sum()
    rows.append(_mk_row("enrollment", "E1f", "enrollment_id 形式 E\\d{10}", int(fmt_ng), n))

    # E2: FK student_id
    sid_set = set(stu["student_id"].astype(str))
    fk_missing_s = (~enr["student_id"].astype(str).isin(sid_set)).sum()
    rows.append(_mk_row(
        "enrollment", "E2", "student_id ∈ student.student_id", int(fk_missing_s), n,
    ))

    # E3: FK course_code
    cid_set = set(crs["course_code"].astype(str))
    fk_missing_c = (~enr["course_code"].astype(str).isin(cid_set)).sum()
    rows.append(_mk_row(
        "enrollment", "E3", "course_code ∈ course.course_code", int(fk_missing_c), n,
    ))

    # E4: academic_year >= student.enrollment_year
    merged = enr.merge(
        stu[["student_id", "enrollment_year", "department", "status"]],
        on="student_id", how="left",
    )
    mask_e4 = merged["academic_year"] < merged["enrollment_year"]
    rows.append(_mk_row(
        "enrollment", "E4", "academic_year >= student.enrollment_year",
        int(mask_e4.sum()), n,
        str(merged.loc[mask_e4, ["student_id", "academic_year", "enrollment_year"]]
            .head(1).to_dict(orient="records")) if mask_e4.any() else "",
    ))

    # E5: 在学期間内（GRADUATED/WITHDRAWN は卒業年度=入学年度+修業年限-1 以下）
    max_grade = merged["department"].map(DEPT_MAX_GRADE).fillna(4).astype(int)
    grad_last = merged["enrollment_year"] + max_grade - 1
    target_mask = merged["status"].isin(["GRADUATED", "WITHDRAWN"])
    mask_e5 = target_mask & (merged["academic_year"] > grad_last)
    rows.append(_mk_row(
        "enrollment", "E5",
        "GRADUATED/WITHDRAWN: academic_year <= 入学年度+修業年限-1",
        int(mask_e5.sum()), int(target_mask.sum()),
        str(merged.loc[mask_e5, ["student_id", "status", "academic_year"]]
            .head(1).to_dict(orient="records")) if mask_e5.any() else "",
    ))

    # E6: academic_year <= REFERENCE_YEAR
    mask_e6 = enr["academic_year"] > REFERENCE_YEAR
    rows.append(_mk_row(
        "enrollment", "E6", f"academic_year <= {REFERENCE_YEAR}",
        int(mask_e6.sum()), n,
    ))

    # E7: (student_id, course_code, academic_year) 一意
    dup3 = enr.duplicated(subset=["student_id", "course_code", "academic_year"])
    rows.append(_mk_row(
        "enrollment", "E7",
        "(student_id, course_code, academic_year) 一意",
        int(dup3.sum()), n,
        str(enr.loc[dup3, ["student_id", "course_code", "academic_year"]]
            .head(1).to_dict(orient="records")) if dup3.any() else "",
    ))

    # E8: final_grade 許容値（null は許容だが本データでは付与済）
    valid_grade = enr["final_grade"].isin(ALLOWED_GRADE_CODE) | enr["final_grade"].isna()
    rows.append(_mk_row(
        "enrollment", "E8", "final_grade ∈ {S,A,B,C,D,F,W} or null",
        int((~valid_grade).sum()), n,
    ))

    # E9: attendance_rate ∈ [0, 100]
    mask_e9 = (enr["attendance_rate"] < 0.0) | (enr["attendance_rate"] > 100.0)
    rows.append(_mk_row(
        "enrollment", "E9", "attendance_rate ∈ [0.0, 100.0]",
        int(mask_e9.sum()), n,
    ))

    return rows


# --- スキーマ整合 -----------------------------------------------------------


def check_schema(df: pd.DataFrame, table_schema: dict) -> list[str]:
    notes = []
    declared = [c["column_name"] for c in table_schema["columns"]]
    actual = list(df.columns)
    if declared != actual:
        missing = set(declared) - set(actual)
        extra = set(actual) - set(declared)
        notes.append(f"列順または列名が不一致 (missing={sorted(missing)}, extra={sorted(extra)})")
    else:
        notes.append("列名・列順ともに inferred_schema.json と一致")
    return notes


# --- 分布ヘルパ -----------------------------------------------------------


def numeric_describe(s: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({
        "value": [
            float(s.min()), float(s.max()), float(s.mean()),
            float(s.std()), float(s.median()),
        ],
    }, index=["min", "max", "mean", "std", "median"]).round(3)


def categorical_freq(s: pd.Series) -> pd.DataFrame:
    cnt = s.value_counts(dropna=False)
    rate = s.value_counts(dropna=False, normalize=True).round(4)
    return pd.concat([cnt.rename("count"), rate.rename("ratio")], axis=1)


# --- EV1〜EV4 評価 ----------------------------------------------------------


def evaluate_ev1(enr: pd.DataFrame) -> dict:
    """final_grade × attendance_rate 整合。
    S: ar>=90 が90%以上、W: ar<=30 が80%以上、F: ar<50 が70%以上。
    """
    out = {}
    for grade, cond_fn, thresh, label in [
        ("S", lambda ar: ar >= 90, 0.90, "ar>=90"),
        ("W", lambda ar: ar <= 30, 0.80, "ar<=30"),
        ("F", lambda ar: ar < 50, 0.70, "ar<50"),
    ]:
        sub = enr.loc[enr["final_grade"] == grade, "attendance_rate"]
        n_sub = len(sub)
        ratio = float(cond_fn(sub).mean()) if n_sub else 0.0
        out[grade] = {
            "n": int(n_sub),
            "label": label,
            "ratio": round(ratio, 4),
            "threshold": thresh,
            "ok": bool(n_sub > 0 and ratio >= thresh),
        }
    out["overall_ok"] = all(out[g]["ok"] for g in ["S", "W", "F"])
    return out


def evaluate_ev2(stu: pd.DataFrame) -> dict:
    means = stu.groupby("department")["gpa"].mean().round(4)
    top_dept = means.idxmax() if not means.empty else None
    return {
        "by_department": means.to_dict(),
        "top_dept": top_dept,
        "ok": bool(top_dept == "MEDICAL"),
    }


def evaluate_ev3(enr: pd.DataFrame, crs: pd.DataFrame) -> dict:
    counts = enr.groupby(["course_code", "academic_year"]).size().reset_index(name="n")
    counts = counts.merge(crs[["course_code", "max_students"]], on="course_code", how="left")
    over = counts["n"] > counts["max_students"]
    n_pairs = len(counts)
    n_over = int(over.sum())
    excess = (counts.loc[over, "n"] - counts.loc[over, "max_students"]).tolist()
    return {
        "n_pairs": int(n_pairs),
        "n_over": n_over,
        "violation_rate": round(n_over / n_pairs, 6) if n_pairs else 0.0,
        "max_excess": int(max(excess)) if excess else 0,
        "ok": bool(n_over == 0),
    }


def evaluate_ev4(enr: pd.DataFrame, stu: pd.DataFrame, crs: pd.DataFrame) -> dict:
    m = enr.merge(
        stu[["student_id", "enrollment_year"]], on="student_id", how="left"
    ).merge(
        crs[["course_code", "level"]], on="course_code", how="left"
    )
    grade_at_year = (m["academic_year"] - m["enrollment_year"] + 1).clip(lower=1)
    diff = (grade_at_year - m["level"]).abs()
    within = (diff <= 1).mean() if len(m) else 0.0
    return {
        "n": int(len(m)),
        "within_1_ratio": round(float(within), 4),
        "ok": bool(within >= 0.7),  # 緩い閾値 (目標値)。報告のみ
    }


# --- レポート出力 -----------------------------------------------------------


def write_report(
    out_path: Path,
    stu: pd.DataFrame,
    crs: pd.DataFrame,
    enr: pd.DataFrame,
    stu_sample: pd.DataFrame,
    crs_sample: pd.DataFrame,
    enr_sample: pd.DataFrame,
    schema: dict,
    violations: pd.DataFrame,
    ev1: dict,
    ev2: dict,
    ev3: dict,
    ev4: dict,
) -> None:
    lines: list[str] = []
    lines.append("# 合成データ評価レポート（ケース3: 大学履修）")
    lines.append("")
    lines.append("## 入力概要")
    lines.append(f"- 学生件数 (synthetic / sample): {len(stu)} / {len(stu_sample)}")
    lines.append(f"- 講義件数 (synthetic / sample): {len(crs)} / {len(crs_sample)}")
    lines.append(f"- 履修件数 (synthetic / sample): {len(enr)} / {len(enr_sample)}")
    lines.append(f"- 基準年度 (reference_year): {REFERENCE_YEAR}")
    lines.append("")

    # --- スキーマ評価 ---
    lines.append("## スキーマ評価")
    for tname, df in [("student", stu), ("course", crs), ("enrollment", enr)]:
        lines.append(f"### {tname}")
        for note in check_schema(df, schema["tables"][tname]):
            lines.append(f"- {note}")
        lines.append("")
        # dtypes
        dtype_rows = [
            f"| {c} | {str(df[c].dtype)} |" for c in df.columns
        ]
        lines.append("| 列 | dtype |")
        lines.append("|----|-------|")
        lines.extend(dtype_rows)
        lines.append("")

    # --- 分布: student ---
    lines.append("## student 分布")
    lines.append("### 数値列")
    for col in ["enrollment_year", "grade", "gpa"]:
        lines.append(f"#### {col}")
        lines.append(numeric_describe(stu[col]).to_markdown())
        lines.append("")
    lines.append("### カテゴリ列")
    for col in ["department", "gender", "status"]:
        lines.append(f"#### {col}")
        lines.append(categorical_freq(stu[col]).to_markdown())
        lines.append("")

    # --- 分布: course ---
    lines.append("## course 分布")
    lines.append("### 数値列")
    for col in ["credits", "level", "max_students"]:
        lines.append(f"#### {col}")
        lines.append(numeric_describe(crs[col]).to_markdown())
        lines.append("")
    lines.append("### カテゴリ列")
    for col in ["department", "semester"]:
        lines.append(f"#### {col}")
        lines.append(categorical_freq(crs[col]).to_markdown())
        lines.append("")

    # --- 分布: enrollment ---
    lines.append("## enrollment 分布")
    lines.append("### 数値列")
    for col in ["academic_year", "attendance_rate"]:
        lines.append(f"#### {col}")
        lines.append(numeric_describe(enr[col]).to_markdown())
        lines.append("")
    lines.append("### カテゴリ列")
    for col in ["final_grade"]:
        lines.append(f"#### {col}")
        lines.append(categorical_freq(enr[col]).to_markdown())
        lines.append("")

    # --- 制約評価 ---
    lines.append("## 制約評価")
    lines.append(violations.to_markdown(index=False))
    lines.append("")

    mandatory_ids = {
        "S1", "S2", "S3", "S4", "S5a", "S5b", "S5c", "S6",
        "CR1", "CR1f", "CR2a", "CR2b", "CR3a", "CR3b", "CR3c",
        "E1", "E1f", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9",
    }
    mand = violations[violations["constraint_id"].isin(mandatory_ids)]
    mand_violations = int(mand["violations"].sum())

    # --- EV 評価 ---
    lines.append("## 評価のみ制約 EV1〜EV4")
    lines.append("### EV1: final_grade × attendance_rate")
    lines.append("| 成績 | n | 条件 | 比率 | 閾値 | 判定 |")
    lines.append("|------|---:|------|-----:|-----:|------|")
    for g in ["S", "W", "F"]:
        v = ev1[g]
        lines.append(
            f"| {g} | {v['n']} | {v['label']} | {v['ratio']} | "
            f"{v['threshold']} | {'OK' if v['ok'] else 'NG'} |"
        )
    lines.append(f"- 総合判定: **{'OK' if ev1['overall_ok'] else 'NG'}**")
    lines.append("")

    lines.append("### EV2: 学部別 GPA 平均（MEDICAL が最大か）")
    ev2_df = pd.Series(ev2["by_department"]).rename("mean_gpa").to_frame()
    lines.append(ev2_df.to_markdown())
    lines.append(f"- top_dept = **{ev2['top_dept']}**: {'OK' if ev2['ok'] else 'NG'}")
    lines.append("")

    lines.append("### EV3: 各講義の年間履修者数 ≤ max_students")
    lines.append(f"- (course_code, academic_year) ペア数: {ev3['n_pairs']}")
    lines.append(f"- 定員超過ペア数: {ev3['n_over']} (rate={ev3['violation_rate']})")
    lines.append(f"- 最大超過人数: {ev3['max_excess']}")
    lines.append(f"- 判定: **{'OK' if ev3['ok'] else 'NG'}**")
    lines.append("")

    lines.append("### EV4: 学生学年と講義 level の差が ±1 以内の比率")
    lines.append(f"- n={ev4['n']}, within_1_ratio={ev4['within_1_ratio']}")
    lines.append(f"- 判定 (>=0.7): **{'OK' if ev4['ok'] else 'NG'}**")
    lines.append("")

    # --- 所見 ---
    lines.append("## 主な所見")
    if mand_violations == 0:
        lines.append("- 必須制約 S1〜S6 / CR1〜CR3 / E1〜E9 の違反は **0件**。")
    else:
        lines.append(f"- 必須制約に **{mand_violations}件** の違反あり。constraints_check.csv 参照。")
    lines.append(f"- EV1 (final_grade × attendance_rate): {'OK' if ev1['overall_ok'] else 'NG'}")
    lines.append(f"- EV2 (MEDICAL の GPA 平均が最大): {'OK' if ev2['ok'] else 'NG'}")
    lines.append(f"- EV3 (定員超過): {'OK' if ev3['ok'] else 'NG'} (超過ペア={ev3['n_over']})")
    lines.append(f"- EV4 (学年×level ±1 比率): within={ev4['within_1_ratio']}")
    lines.append("")

    lines.append("## 既知の限界 / 注意事項")
    lines.append("- 本データは仕様駆動の合成データであり、匿名加工情報ではない。")
    lines.append("- サンプル件数 (student=22, course=20, enrollment=36) が少ないため、")
    lines.append("  サンプルとの統計的差異は data_spec.md / inferred_schema.json の指定を優先している。")
    lines.append("- 休学・留年は除外し、grade は理論値 (enrollment_year + 修業年限) で算出している。")
    lines.append("- 想定利用範囲は PoC・画面モック・分析仮説検討用途。実データの統計的再現性は保証しない。")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


# --- CLI --------------------------------------------------------------------


def main() -> int:
    here = Path(__file__).resolve().parent.parent  # examples/university_enrollment
    parser = argparse.ArgumentParser(description="大学履修 評価器")
    parser.add_argument("--students", default=str(here / "output" / "students.csv"))
    parser.add_argument("--courses", default=str(here / "output" / "courses.csv"))
    parser.add_argument("--enrollments", default=str(here / "output" / "enrollments.csv"))
    parser.add_argument("--students-sample", default=str(here / "input" / "student_sample_data.csv"))
    parser.add_argument("--courses-sample", default=str(here / "input" / "course_sample_data.csv"))
    parser.add_argument("--enrollments-sample", default=str(here / "input" / "enrollment_sample_data.csv"))
    parser.add_argument("--schema", default=str(here / "work" / "inferred_schema.json"))
    parser.add_argument("--report", default=str(here / "output" / "evaluation_report.md"))
    parser.add_argument("--constraints", default=str(here / "output" / "constraints_check.csv"))
    args = parser.parse_args()

    stu = pd.read_csv(args.students, dtype={"student_id": str}, keep_default_na=False)
    crs = pd.read_csv(args.courses, dtype={"course_code": str}, keep_default_na=False)
    enr = pd.read_csv(
        args.enrollments,
        dtype={"enrollment_id": str, "student_id": str, "course_code": str},
        keep_default_na=False,
    )

    # 数値カラムの型整備
    for col in ["enrollment_year", "grade", "gender"]:
        stu[col] = pd.to_numeric(stu[col], errors="coerce")
    stu["gpa"] = pd.to_numeric(stu["gpa"], errors="coerce")
    for col in ["credits", "level", "max_students"]:
        crs[col] = pd.to_numeric(crs[col], errors="coerce")
    enr["academic_year"] = pd.to_numeric(enr["academic_year"], errors="coerce")
    enr["attendance_rate"] = pd.to_numeric(enr["attendance_rate"], errors="coerce")

    # サンプル（参考表示用）
    stu_sample = pd.read_csv(args.students_sample, keep_default_na=False)
    crs_sample = pd.read_csv(args.courses_sample, keep_default_na=False)
    enr_sample = pd.read_csv(args.enrollments_sample, keep_default_na=False)

    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))

    # 制約チェック
    rows: list[dict] = []
    rows.extend(check_student_constraints(stu))
    rows.extend(check_course_constraints(crs))
    rows.extend(check_enrollment_constraints(enr, stu, crs))
    violations = pd.DataFrame(rows)

    Path(args.constraints).parent.mkdir(parents=True, exist_ok=True)
    violations.to_csv(args.constraints, index=False, encoding="utf-8")

    # EV
    ev1 = evaluate_ev1(enr)
    ev2 = evaluate_ev2(stu)
    ev3 = evaluate_ev3(enr, crs)
    ev4 = evaluate_ev4(enr, stu, crs)

    write_report(
        Path(args.report), stu, crs, enr,
        stu_sample, crs_sample, enr_sample,
        schema, violations, ev1, ev2, ev3, ev4,
    )

    mandatory_ids = {
        "S1", "S2", "S3", "S4", "S5a", "S5b", "S5c", "S6",
        "CR1", "CR1f", "CR2a", "CR2b", "CR3a", "CR3b", "CR3c",
        "E1", "E1f", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9",
    }
    mand = violations[violations["constraint_id"].isin(mandatory_ids)]
    mand_violations = int(mand["violations"].sum())

    print(f"[evaluate] wrote {args.report}")
    print(f"[evaluate] wrote {args.constraints}")
    print(
        f"[evaluate] mandatory_violations={mand_violations} "
        f"EV1={'OK' if ev1['overall_ok'] else 'NG'} "
        f"EV2={'OK' if ev2['ok'] else 'NG'} "
        f"EV3={'OK' if ev3['ok'] else 'NG'} "
        f"EV4_ratio={ev4['within_1_ratio']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
