# 制約条件（ケース3: 大学履修）

## student 側

- **S1**: student_id は全行で一意。
- **S2**: `enrollment_year` は 2018〜2025（reference_year=2025）。
- **S3**: `grade` の上限は学部依存。MEDICAL は 6、それ以外は 4。
- **S4**: `gpa` ∈ [0.0, 4.0]。
- **S5**: コード値（department, gender, status）は許容値のみ。
- **S6**: `student_id` の先頭4桁は `enrollment_year` と一致。

## course 側

- **CR1**: course_code は全行で一意。
- **CR2**: コード値（department, semester）は許容値のみ。
- **CR3**: `credits` ∈ [1, 4]、`level` ∈ [1, 4]、`max_students` ∈ [20, 300]。
- **CR4**: `semester='FULL_YEAR'` の講義は通年扱い（credits は 3〜4 を推奨だが、必須制約ではない）。

## enrollment 側

- **E1**: enrollment_id は全行で一意。
- **E2 (FK1)**: enrollment.student_id は student.student_id に存在。
- **E3 (FK2)**: enrollment.course_code は course.course_code に存在。
- **E4 (履修期間)**: `academic_year >= student.enrollment_year`。
- **E5 (在学期間内)**: `student.status='GRADUATED'` の場合、その学生の academic_year は卒業年度以前（=enrollment_year + 修業年限 - 1 以下）。`status='WITHDRAWN'` 学生も同様に「在籍最終年度」までで打ち切る。
- **E6 (年度上限)**: `academic_year <= reference_year (2025)`。
- **E7 (一意組合せ)**: (student_id, course_code, academic_year) は一意（同一年度に同じ講義を重複登録しない）。
- **E8 (成績コード値)**: `final_grade ∈ {S, A, B, C, D, F, W}` または null（履修中の場合 null 可、本データでは付与済みとする）。
- **E9 (出席率値域)**: `attendance_rate ∈ [0.0, 100.0]`。

## 評価のみ（必須ではない）

- **EV1 (成績と出席率の整合)**:
  - `final_grade='S'` の出席率は 90以上が 90%以上を占める
  - `final_grade='W'` の出席率は 30以下が 80%以上を占める
  - `final_grade='F'` の出席率は 50未満が 70%以上を占める
- **EV2 (学部別 GPA 平均順序)**: MEDICAL の GPA 平均が最も高い。
- **EV3 (定員)**: 各講義の年間履修者数は概ね `max_students` を超えない（評価で違反率を確認）。
- **EV4 (学年と level の整合)**: 履修時の学生学年と講義 level の差が ±1 以内である比率を計測。
