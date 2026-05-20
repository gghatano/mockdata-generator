"""ケース3: 大学履修 合成データ生成器（student / course / enrollment）。

仕様の根拠:
- examples/university_enrollment/work/inferred_schema.json
- examples/university_enrollment/work/generation_plan.md
- examples/university_enrollment/work/constraint_plan.md
- examples/university_enrollment/input/data_spec.md / constraints.md
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

# --- 定数 -------------------------------------------------------------------

REFERENCE_YEAR = 2025
ENROLLMENT_YEAR_MIN = 2018
ENROLLMENT_YEAR_MAX = 2025

DEPARTMENTS_STUDENT = ["ENGINEERING", "LITERATURE", "SCIENCE", "ECONOMICS", "MEDICAL"]
STUDENT_DEPT_WEIGHTS = np.array([30, 20, 18, 22, 10], dtype=float)
STUDENT_DEPT_WEIGHTS = STUDENT_DEPT_WEIGHTS / STUDENT_DEPT_WEIGHTS.sum()

# 修業年限
DEPT_MAX_GRADE = {
    "ENGINEERING": 4,
    "LITERATURE": 4,
    "SCIENCE": 4,
    "ECONOMICS": 4,
    "MEDICAL": 6,
}

GENDER_VALUES = [1, 2, 9]
GENDER_WEIGHTS_DEFAULT = np.array([50, 48, 2], dtype=float)
GENDER_WEIGHTS_DEFAULT = GENDER_WEIGHTS_DEFAULT / GENDER_WEIGHTS_DEFAULT.sum()
GENDER_WEIGHTS_MEDICAL = np.array([40, 58, 2], dtype=float)
GENDER_WEIGHTS_MEDICAL = GENDER_WEIGHTS_MEDICAL / GENDER_WEIGHTS_MEDICAL.sum()

# status (経過年数 >= 修業年限)
STATUS_DONE = ["GRADUATED", "WITHDRAWN", "LEAVE", "ENROLLED"]
STATUS_DONE_W = np.array([80, 8, 2, 10], dtype=float)
STATUS_DONE_W = STATUS_DONE_W / STATUS_DONE_W.sum()
# status (経過年数 < 修業年限)
STATUS_IN = ["ENROLLED", "LEAVE", "WITHDRAWN"]
STATUS_IN_W = np.array([92, 5, 3], dtype=float)
STATUS_IN_W = STATUS_IN_W / STATUS_IN_W.sum()

# GPA: 学部別 N(mean, std)
GPA_PARAMS = {
    "MEDICAL": (3.60, 0.30),
    "SCIENCE": (3.20, 0.45),
    "ECONOMICS": (3.10, 0.45),
    "ENGINEERING": (2.95, 0.50),
    "LITERATURE": (2.85, 0.50),
}

# Course
DEPARTMENTS_COURSE = ["COMMON", "ENGINEERING", "ECONOMICS", "LITERATURE", "SCIENCE", "MEDICAL"]
COURSE_DEPT_WEIGHTS = np.array([25, 20, 15, 15, 13, 12], dtype=float)
COURSE_DEPT_WEIGHTS = COURSE_DEPT_WEIGHTS / COURSE_DEPT_WEIGHTS.sum()

SEMESTERS = ["SPRING", "FALL", "FULL_YEAR"]
SEMESTER_WEIGHTS = np.array([40, 40, 20], dtype=float)
SEMESTER_WEIGHTS = SEMESTER_WEIGHTS / SEMESTER_WEIGHTS.sum()

LEVELS = [1, 2, 3, 4]
LEVEL_WEIGHTS = np.array([30, 30, 25, 15], dtype=float)
LEVEL_WEIGHTS = LEVEL_WEIGHTS / LEVEL_WEIGHTS.sum()

# Enrollment
ENROLLMENT_LAMBDA = 10  # Poisson 平均
ENROLLMENT_PER_YEAR_CAP = 30

GRADES = ["S", "A", "B", "C", "D", "F", "W"]


@dataclass
class GenerationLog:
    students: int = 0
    courses: int = 0
    enrollments_raw: int = 0
    enrollments_final: int = 0
    removed_e7_duplicates: int = 0
    overwritten_s3_grade: int = 0
    removed_e5_out_of_period: int = 0
    removed_e4_before_enroll: int = 0
    removed_e6_after_reference: int = 0
    rejected_in_loop: int = 0
    extras: dict = field(default_factory=dict)


# --- student 生成 -----------------------------------------------------------


def _truncated_normal(rng: np.random.Generator, n: int, mean: float, std: float,
                     lo: float, hi: float) -> np.ndarray:
    """[lo, hi] に切断した正規分布。値域外はリジェクト方式で再サンプル。"""
    out = rng.normal(mean, std, size=n)
    bad = (out < lo) | (out > hi)
    iters = 0
    while bad.any() and iters < 100:
        out[bad] = rng.normal(mean, std, size=int(bad.sum()))
        bad = (out < lo) | (out > hi)
        iters += 1
    return np.clip(out, lo, hi)


def generate_students(n_students: int, rng: np.random.Generator,
                      log: GenerationLog) -> pd.DataFrame:
    # enrollment_year を均等で抽選
    years = list(range(ENROLLMENT_YEAR_MIN, ENROLLMENT_YEAR_MAX + 1))
    year_weights = np.full(len(years), 1.0 / len(years))
    enrollment_year = rng.choice(years, size=n_students, p=year_weights)

    # department
    department = rng.choice(DEPARTMENTS_STUDENT, size=n_students, p=STUDENT_DEPT_WEIGHTS)

    # gender (department に応じて切替)
    gender = np.zeros(n_students, dtype=int)
    for dept in DEPARTMENTS_STUDENT:
        idx = department == dept
        if not idx.any():
            continue
        w = GENDER_WEIGHTS_MEDICAL if dept == "MEDICAL" else GENDER_WEIGHTS_DEFAULT
        gender[idx] = rng.choice(GENDER_VALUES, size=int(idx.sum()), p=w)

    # status
    status = np.empty(n_students, dtype=object)
    max_grade_arr = np.array([DEPT_MAX_GRADE[d] for d in department])
    elapsed = REFERENCE_YEAR - enrollment_year  # 0 = 入学初年度
    done_mask = elapsed >= max_grade_arr  # 修業年限以上経過
    if done_mask.any():
        status[done_mask] = rng.choice(STATUS_DONE, size=int(done_mask.sum()), p=STATUS_DONE_W)
    if (~done_mask).any():
        status[~done_mask] = rng.choice(STATUS_IN, size=int((~done_mask).sum()), p=STATUS_IN_W)

    # grade: 派生計算 (S3)
    raw_grade = REFERENCE_YEAR - enrollment_year + 1
    grade = np.minimum(raw_grade, max_grade_arr).astype(int)
    # GRADUATED は表示上 max_grade（既に min 適用済）
    # 念のため最小 1
    grade = np.maximum(grade, 1)
    log.overwritten_s3_grade = 0  # 生成時から派生のため違反なし

    # gpa: 学部別 truncated normal
    gpa = np.zeros(n_students, dtype=float)
    for dept, (mu, sigma) in GPA_PARAMS.items():
        idx = department == dept
        if not idx.any():
            continue
        gpa[idx] = _truncated_normal(rng, int(idx.sum()), mu, sigma, 0.0, 4.0)
    gpa = np.round(gpa, 2)

    # student_id: 年度別連番（年度内で 1 始まり）
    student_ids = np.empty(n_students, dtype=object)
    # 並び替えなしで、各年度ごとに seq を振る
    counters: dict[int, int] = {}
    for i in range(n_students):
        y = int(enrollment_year[i])
        counters[y] = counters.get(y, 0) + 1
        student_ids[i] = f"S{y:04d}{counters[y]:04d}"

    df = pd.DataFrame({
        "student_id": student_ids,
        "enrollment_year": enrollment_year.astype(int),
        "department": department,
        "grade": grade,
        "gender": gender.astype(int),
        "status": status.astype(str),
        "gpa": gpa,
    })
    log.students = len(df)
    return df


# --- course 生成 ------------------------------------------------------------


def generate_courses(n_courses: int, rng: np.random.Generator,
                     log: GenerationLog) -> pd.DataFrame:
    # course_code: 連番 C0001 ... (CR1)
    codes = [f"C{i + 1:04d}" for i in range(n_courses)]

    # department
    department = rng.choice(DEPARTMENTS_COURSE, size=n_courses, p=COURSE_DEPT_WEIGHTS)
    # semester
    semester = rng.choice(SEMESTERS, size=n_courses, p=SEMESTER_WEIGHTS)
    # level
    level = rng.choice(LEVELS, size=n_courses, p=LEVEL_WEIGHTS)

    # credits: semester 依存
    credits = np.empty(n_courses, dtype=int)
    full_mask = semester == "FULL_YEAR"
    if full_mask.any():
        credits[full_mask] = rng.choice([3, 4], size=int(full_mask.sum()), p=[0.3, 0.7])
    half_mask = ~full_mask
    if half_mask.any():
        credits[half_mask] = rng.choice([1, 2, 3], size=int(half_mask.sum()), p=[0.10, 0.65, 0.25])

    # max_students: department 依存（10 単位丸め）
    max_students = np.empty(n_courses, dtype=int)
    for dept in DEPARTMENTS_COURSE:
        idx = department == dept
        if not idx.any():
            continue
        if dept == "COMMON":
            raw = rng.integers(100, 301, size=int(idx.sum()))
        elif dept == "MEDICAL":
            raw = rng.integers(80, 121, size=int(idx.sum()))
        else:
            raw = rng.integers(40, 151, size=int(idx.sum()))
        # 10 単位に丸め
        raw = (raw / 10).round().astype(int) * 10
        # 20〜300 範囲
        raw = np.clip(raw, 20, 300)
        max_students[idx] = raw

    df = pd.DataFrame({
        "course_code": codes,
        "department": department,
        "credits": credits.astype(int),
        "semester": semester,
        "level": level.astype(int),
        "max_students": max_students.astype(int),
    })
    log.courses = len(df)
    return df


# --- enrollment 生成 --------------------------------------------------------


def _compute_period_for_student(
    rng: np.random.Generator,
    enrollment_year: int,
    department: str,
    status: str,
) -> tuple[int, int]:
    """学生の (start_year, end_year) を返す。両端含む在学期間。"""
    max_grade = DEPT_MAX_GRADE[department]
    natural_last = min(REFERENCE_YEAR, enrollment_year + max_grade - 1)
    if status == "GRADUATED":
        last = min(enrollment_year + max_grade - 1, REFERENCE_YEAR)
    elif status == "WITHDRAWN":
        # 在籍最終年度: 入学から修業年限-1 までの一様
        last_offset = int(rng.integers(0, max_grade))  # 0..max_grade-1
        last = min(enrollment_year + last_offset, REFERENCE_YEAR)
    else:  # ENROLLED / LEAVE
        last = natural_last
    last = min(last, REFERENCE_YEAR)
    if last < enrollment_year:
        last = enrollment_year
    return enrollment_year, last


def _build_course_weight_for_student(
    student_dept: str,
    enrollment_year: int,
    academic_year: int,
    courses_df: pd.DataFrame,
    course_idx_arrays: dict,
) -> np.ndarray:
    """ある学生のある履修年度における、各 course への重み配列を返す。"""
    grade_at_year = max(1, academic_year - enrollment_year + 1)

    dept_arr = course_idx_arrays["department"]
    semester_arr = course_idx_arrays["semester"]
    level_arr = course_idx_arrays["level"]

    n = len(courses_df)
    w = np.ones(n, dtype=float)

    # 1) 学年で COMMON 比率を変える
    if grade_at_year <= 2:
        # COMMON 60% / 所属 30% / 他 10%
        w_common = 6.0
        w_own = 3.0
        w_other = 1.0
    else:
        # 所属 60% / COMMON 20% / 他 20%
        w_common = 2.0
        w_own = 6.0
        w_other = 2.0

    base = np.where(dept_arr == "COMMON", w_common,
                    np.where(dept_arr == student_dept, w_own, w_other))

    # 2) MEDICAL の学生は FULL_YEAR を + 20%
    if student_dept == "MEDICAL":
        base = base * np.where(semester_arr == "FULL_YEAR", 1.2, 1.0)

    # 3) abs(grade_at_year - level) <= 1 を 2 倍 (EV4)
    diff = np.abs(level_arr - grade_at_year)
    base = base * np.where(diff <= 1, 2.0, 1.0)

    # 4) MEDICAL の学生でない場合は course.department=MEDICAL を弱める（医学講義は MEDICAL 学生中心）
    if student_dept != "MEDICAL":
        base = base * np.where(dept_arr == "MEDICAL", 0.1, 1.0)

    # 5) MEDICAL 学生は course.department=MEDICAL を強める
    if student_dept == "MEDICAL":
        base = base * np.where(dept_arr == "MEDICAL", 2.5, 1.0)

    return base


def _sample_final_grade(rng: np.random.Generator, attendance_rate: float) -> str:
    """attendance_rate に応じた条件付きカテゴリで final_grade を抽選。

    EV1 目標:
      S: ar>=90 が 90% 以上
      W: ar<=30 が 80% 以上
      F: ar<50 が 70% 以上
    そのため、S は ar>=90 のみで発生し、W は ar<=30 を中心に発生させる。
    """
    ar = attendance_rate
    if ar >= 90:
        # S は ar>=90 のみで発生（EV1-S 完全達成）
        return rng.choice(["S", "A", "B"], p=[0.55, 0.35, 0.10])
    elif ar >= 80:
        return rng.choice(["A", "B", "C"], p=[0.50, 0.35, 0.15])
    elif ar >= 60:
        return rng.choice(["B", "C", "D"], p=[0.35, 0.45, 0.20])
    elif ar >= 50:
        # F は ar<50 で発生させたいので、ar in [50,60) では F を出さない
        return rng.choice(["C", "D"], p=[0.45, 0.55])
    elif ar >= 40:
        # ar in [40,50): F 中心（EV1-F 強化）
        return rng.choice(["D", "F"], p=[0.30, 0.70])
    elif ar > 30:
        # ar in (30,40): F のみ
        return "F"
    else:
        # ar<=30: W 中心（EV1-W 強化）
        return rng.choice(["W", "F"], p=[0.85, 0.15])


def _sample_attendance_rate(rng: np.random.Generator, n: int) -> np.ndarray:
    """N(82, 18) 主体 + 10% 程度の低出席混合を双峰で生成。"""
    is_low = rng.random(n) < 0.10
    out = np.zeros(n, dtype=float)
    if (~is_low).any():
        out[~is_low] = _truncated_normal(rng, int((~is_low).sum()), 82.0, 18.0, 0.0, 100.0)
    if is_low.any():
        out[is_low] = _truncated_normal(rng, int(is_low.sum()), 30.0, 15.0, 0.0, 100.0)
    return np.round(out, 1)


def generate_enrollments(
    students_df: pd.DataFrame,
    courses_df: pd.DataFrame,
    rng: np.random.Generator,
    log: GenerationLog,
) -> pd.DataFrame:
    # 講義の事前配列
    course_codes = courses_df["course_code"].to_numpy()
    course_idx_arrays = {
        "department": courses_df["department"].to_numpy(),
        "semester": courses_df["semester"].to_numpy(),
        "level": courses_df["level"].to_numpy(),
        "max_students": courses_df["max_students"].to_numpy(),
    }
    n_courses = len(course_codes)

    rows: list[dict] = []

    for _, srow in students_df.iterrows():
        sid = srow["student_id"]
        sy = int(srow["enrollment_year"])
        sdept = srow["department"]
        sstatus = srow["status"]
        start_y, end_y = _compute_period_for_student(rng, sy, sdept, sstatus)
        # 学生ごとに (course_code, academic_year) のセットを管理
        seen: set[tuple[str, int]] = set()

        for ay in range(start_y, end_y + 1):
            n_take = int(rng.poisson(ENROLLMENT_LAMBDA))
            n_take = min(n_take, ENROLLMENT_PER_YEAR_CAP, n_courses)
            if n_take <= 0:
                continue
            # 重み構築（学生×年度ごと）
            weights = _build_course_weight_for_student(
                sdept, sy, ay, courses_df, course_idx_arrays
            )
            weights = weights / weights.sum()

            # 重複しない講義を n_take 件取る
            # numpy choice の replace=False で抽出
            picked = rng.choice(n_courses, size=n_take, replace=False, p=weights)

            for ci in picked:
                code = course_codes[ci]
                key = (code, ay)
                if key in seen:
                    log.rejected_in_loop += 1
                    continue
                seen.add(key)
                rows.append({
                    "student_id": sid,
                    "course_code": code,
                    "academic_year": int(ay),
                })

    log.enrollments_raw = len(rows)

    if not rows:
        df = pd.DataFrame(columns=[
            "enrollment_id", "student_id", "course_code",
            "academic_year", "final_grade", "attendance_rate",
        ])
        return df

    df = pd.DataFrame(rows)

    # post sampling: (student_id, course_code, academic_year) 一意（生成時に保証済だが念のため）
    before = len(df)
    df = df.drop_duplicates(subset=["student_id", "course_code", "academic_year"]).reset_index(drop=True)
    log.removed_e7_duplicates += before - len(df)

    # E4 / E6 / E5 のチェック（生成時に保証済だが念のため）
    # 学生の期間を辞書化
    sid_to_year = dict(zip(students_df["student_id"], students_df["enrollment_year"]))
    sid_to_dept = dict(zip(students_df["student_id"], students_df["department"]))
    sid_to_status = dict(zip(students_df["student_id"], students_df["status"]))

    # E4: academic_year >= enrollment_year
    mask_e4 = df["academic_year"] >= df["student_id"].map(sid_to_year)
    removed_e4 = int((~mask_e4).sum())
    log.removed_e4_before_enroll += removed_e4
    df = df.loc[mask_e4].reset_index(drop=True)

    # E6: academic_year <= REFERENCE_YEAR
    mask_e6 = df["academic_year"] <= REFERENCE_YEAR
    removed_e6 = int((~mask_e6).sum())
    log.removed_e6_after_reference += removed_e6
    df = df.loc[mask_e6].reset_index(drop=True)

    # E5: 在籍最終年度を超えていないか（WITHDRAWN/GRADUATED で打ち切り）
    # _compute_period_for_student で保証しているのでチェックのみ
    # （WITHDRAWN は学生ごとに乱数で last を決めているため再計算では一致しないが、
    # 既に生成時に範囲制限されているため、ここでは S3 ベースの上限のみで判定）
    def _max_allowed_year(sid):
        sy_ = sid_to_year[sid]
        dept_ = sid_to_dept[sid]
        return min(REFERENCE_YEAR, sy_ + DEPT_MAX_GRADE[dept_] - 1)

    max_y = df["student_id"].map(_max_allowed_year)
    mask_e5 = df["academic_year"] <= max_y
    removed_e5 = int((~mask_e5).sum())
    log.removed_e5_out_of_period += removed_e5
    df = df.loc[mask_e5].reset_index(drop=True)

    # attendance_rate
    df["attendance_rate"] = _sample_attendance_rate(rng, len(df))

    # final_grade
    df["final_grade"] = [
        _sample_final_grade(rng, ar) for ar in df["attendance_rate"].to_numpy()
    ]

    # enrollment_id を最後に振る (E1)
    # ソート: student_id, academic_year, course_code でわかりやすい順に
    df = df.sort_values(["student_id", "academic_year", "course_code"]).reset_index(drop=True)
    df.insert(0, "enrollment_id", [f"E{i + 1:010d}" for i in range(len(df))])

    # 列順
    df = df[["enrollment_id", "student_id", "course_code",
             "academic_year", "final_grade", "attendance_rate"]]
    log.enrollments_final = len(df)
    return df


# --- 上位 generate -----------------------------------------------------------


def generate(
    n_students: int, n_courses: int, seed: int
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, GenerationLog]:
    rng = np.random.default_rng(seed)
    log = GenerationLog()

    students_df = generate_students(n_students, rng, log)
    courses_df = generate_courses(n_courses, rng, log)
    enrollments_df = generate_enrollments(students_df, courses_df, rng, log)

    return students_df, courses_df, enrollments_df, log


# --- CLI --------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="大学履修 合成データ生成器")
    parser.add_argument("--students", type=int, default=1000)
    parser.add_argument("--courses", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)

    here = Path(__file__).resolve().parent.parent  # examples/university_enrollment
    parser.add_argument(
        "--students-output", type=str,
        default=str(here / "output" / "students.csv"),
    )
    parser.add_argument(
        "--courses-output", type=str,
        default=str(here / "output" / "courses.csv"),
    )
    parser.add_argument(
        "--enrollments-output", type=str,
        default=str(here / "output" / "enrollments.csv"),
    )
    args = parser.parse_args()

    students_df, courses_df, enrollments_df, log = generate(
        args.students, args.courses, args.seed
    )

    sp = Path(args.students_output)
    cp = Path(args.courses_output)
    ep = Path(args.enrollments_output)
    for p in [sp, cp, ep]:
        p.parent.mkdir(parents=True, exist_ok=True)
    students_df.to_csv(sp, index=False, encoding="utf-8")
    courses_df.to_csv(cp, index=False, encoding="utf-8")
    enrollments_df.to_csv(ep, index=False, encoding="utf-8")

    print(
        f"[generator] students={log.students} courses={log.courses} "
        f"enrollments_raw={log.enrollments_raw} enrollments_final={log.enrollments_final} "
        f"rejected_inloop_E7={log.rejected_in_loop} "
        f"removed_E7_dup={log.removed_e7_duplicates} "
        f"removed_E4={log.removed_e4_before_enroll} "
        f"removed_E5={log.removed_e5_out_of_period} "
        f"removed_E6={log.removed_e6_after_reference} "
        f"overwritten_S3_grade={log.overwritten_s3_grade}",
        file=sys.stderr,
    )
    print(f"[generator] wrote {sp}, {cp}, {ep}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
