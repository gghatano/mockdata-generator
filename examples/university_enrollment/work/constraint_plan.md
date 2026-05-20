# constraint_plan.md（ケース3: 大学履修）

3 テーブル（student / course / enrollment）構成。reference_year = 2025。
constraints.md の S1〜S6, CR1〜CR4, E1〜E9, EV1〜EV4 を以下に分類する。

## generation_constraint（生成時に直接保証）

| ID | 制約 | 反映方法 |
|----|------|----------|
| S1 | student_id は全行で一意 | sequential_id（入学年度別の連番でゼロ埋め） |
| S2 | enrollment_year ∈ [2018, 2025] | 入学年度を区間内の重み付きサンプル |
| S4 | gpa ∈ [0.0, 4.0] | 学部別 truncated normal で生成 |
| S5 | コード値（department, gender, status）は許容値のみ | weighted_category で許容値からサンプル |
| S6 | student_id 先頭4桁 = enrollment_year | id 生成式で連結（`f"S{year:04d}{seq:04d}"`） |
| CR1 | course_code は全行で一意 | sequential_id（C+4桁） |
| CR2 | コード値（department, semester）は許容値のみ | weighted_category |
| CR3 | credits ∈ [1,4]、level ∈ [1,4]、max_students ∈ [20,300] | 区間内サンプル/clip |
| E1 | enrollment_id は全行で一意 | sequential_id（E+10桁） |
| E2 (FK1) | enrollment.student_id ∈ student.student_id | 学生集合からサンプル |
| E3 (FK2) | enrollment.course_code ∈ course.course_code | 講義集合からサンプル |
| E4 | academic_year >= student.enrollment_year | 学生ごとの在学期間から academic_year をサンプル |
| E6 | academic_year <= reference_year (2025) | 区間上限を 2025 にクリップ |
| E8 | final_grade ∈ {S,A,B,C,D,F,W} | 許容値カテゴリからサンプル（attendance_rate に応じた条件付き） |
| E9 | attendance_rate ∈ [0.0, 100.0] | truncated normal を `clip(0,100)` |

## post_sampling_constraint（生成後に補正・上書き）

| ID | 制約 | 対応 |
|----|------|------|
| S3 | grade 上限は学部依存（MEDICAL=6, その他=4） | `grade = min(reference_year - enrollment_year + 1, 修業年限)` を派生計算して上書き |
| CR4 | FULL_YEAR の credits は 3〜4 推奨（必須ではない） | 生成時に FULL_YEAR → credits ∈ {3,4} の重み付け、違反は生成側で発生しない設計 |
| E5 | GRADUATED/WITHDRAWN の在学期間打ち切り | 学生 status から在籍最終年度を派生し、academic_year をその範囲内に制限 |
| E7 | (student_id, course_code, academic_year) 一意 | 履修生成時に重複組合せが出たら reject sampling（同じ年度・同じ講義はスキップ） |

## validation_only_constraint（評価のみ）

| ID | 内容 |
|----|------|
| EV1 | 成績と出席率の整合: S は出席率90以上が90%以上、W は30以下が80%以上、F は50未満が70%以上 |
| EV2 | 学部別 GPA 平均の順序: MEDICAL の GPA 平均が最も高い |
| EV3 | 各講義の年間履修者数が概ね max_students を超えない（違反率を計測） |
| EV4 | 履修時の学生学年と course.level の差が ±1 以内である比率を計測 |

## relationships / 派生規則（補足）

- `grade` は生成後に学生の `enrollment_year` と `department` から導出（休学・留年は除外）。
- `student.status` は経過年数 (reference_year - enrollment_year) と 修業年限 (MEDICAL=6 / その他=4) に基づき分岐。
  - 経過年数 >= 修業年限 → GRADUATED 80% / WITHDRAWN 8% / LEAVE 2% / ENROLLED 10%
  - 経過年数 <  修業年限 → ENROLLED 92% / LEAVE 5% / WITHDRAWN 3%
- `enrollment.academic_year` の上限:
  - GRADUATED → 卒業年度（=enrollment_year + 修業年限 - 1）
  - WITHDRAWN → 在籍最終年度（仮に enrollment_year + 修業年限 - 1 を超えない範囲でサンプル）
  - ENROLLED / LEAVE → min(reference_year, enrollment_year + 修業年限 - 1)
- `final_grade` は `attendance_rate` の階層で条件付き分布:
  - attendance_rate >= 90 → 主に S/A、S は90以上の中から
  - 80 <= attendance_rate < 90 → 主に A/B
  - 60 <= attendance_rate < 80 → B/C 中心
  - 40 <= attendance_rate < 60 → C/D 中心
  - attendance_rate < 40 → F または W、W は30以下中心
- MEDICAL 学生は FULL_YEAR 講義を優先サンプル、学年 1〜2 は COMMON、3〜4 は所属学部講義を優先する重み付け。
- 1 学生の年間履修件数は Poisson(λ=10) でサンプル。

## oversampling

- student: 1.0 倍（学生数は与件として固定）。
- course: 1.0 倍。
- enrollment: 期待値ベースで生成、(student, course, year) 一意制約に当たって除外された分は再サンプル（reject）で補う。最終件数は決定論的に固定しない。
- E5 / E7 違反はゼロを目標とするため、両者は生成パイプラインで保証する。
