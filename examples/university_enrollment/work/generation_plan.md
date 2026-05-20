# generation_plan.md（ケース3: university_enrollment）

`inferred_schema.json` と `constraint_plan.md` に基づき、3 テーブル（student / course / enrollment）の各列の生成方式を定義する。
`reference_year = 2025`。乱数は `numpy.random.default_rng(seed)` を全体で共有して再現可能にする。

---

## 全体フロー

1. **student** を所定件数生成（`--students` で指定。デフォルト 500）。
2. **course** を所定件数生成（`--courses` で指定。デフォルト 200）。
3. **enrollment** を student の在学期間と履修件数 Poisson(λ=10) に基づき生成。
4. 生成後に post sampling で `(student_id, course_code, academic_year)` の重複除去・在学期間外の除外を行う。
5. enrollment_id を最後に連番で振り直す。

生成順序: **student → course → enrollment**（FK 制約を満たすため親 → 子の順）。

---

## テーブル 1: student（学生マスタ）

### 列ごとの生成方式

| 列 | 方式 | 概要 |
|----|------|------|
| student_id | sequential_id | `f"S{enrollment_year:04d}{seq:04d}"`。入学年度別に連番（seq は学部・全体通しの任意連番でなく、年度内通し）。S6 を満たす |
| enrollment_year | weighted_category | 2018〜2025 を概ね均等（各 12.5%）で抽選。data_spec.md 指定。S2 を満たす |
| department | weighted_category | `ENGINEERING:LITERATURE:SCIENCE:ECONOMICS:MEDICAL = 30:20:18:22:10`（data_spec.md 指定） |
| grade | derived_column | `min(reference_year - enrollment_year + 1, 修業年限)`（MEDICAL=6, それ以外=4）で派生計算。S3 を満たす |
| gender | weighted_category | 全体 `1:2:9 = 50:48:2`。`department=MEDICAL` のみ `1:2:9 = 40:58:2` に切替 |
| status | rule_based | 経過年数 `(reference_year - enrollment_year)` と修業年限の比較で分岐:<br>　・経過年数 ≥ 修業年限 → `GRADUATED:WITHDRAWN:LEAVE:ENROLLED = 80:8:2:10`<br>　・経過年数 < 修業年限 → `ENROLLED:LEAVE:WITHDRAWN = 92:5:3` |
| gpa | numeric_distribution | 学部別 truncated normal を `[0.0, 4.0]` にクリップ:<br>　・MEDICAL: N(3.60, 0.30)<br>　・SCIENCE: N(3.20, 0.45)<br>　・ECONOMICS: N(3.10, 0.45)<br>　・ENGINEERING: N(2.95, 0.50)<br>　・LITERATURE: N(2.85, 0.50) |

### 統計量の利用方針

- 構成比はすべて data_spec.md の指定値を優先（サンプル件数 22 は少ないため）。
- GPA の学部別平均はサンプル統計を参考に MEDICAL >> その他 となる順序を保つ（EV2 評価のため）。

### 列間関係

- `student_id` 先頭 4 桁 ⇔ `enrollment_year`（id 生成式で連結）。
- `grade` ⇔ `enrollment_year`, `department`（派生）。
- `status` ⇔ `enrollment_year`, `department`（修業年限ベースで分岐）。
- `gender` ⇔ `department`（MEDICAL のみ女性比率増）。
- `gpa` ⇔ `department`（学部別正規分布）。

---

## テーブル 2: course（講義マスタ）

### 列ごとの生成方式

| 列 | 方式 | 概要 |
|----|------|------|
| course_code | sequential_id | `f"C{seq:04d}"`。`C0001` から連番。CR1 を満たす |
| department | weighted_category | `COMMON:ENGINEERING:ECONOMICS:LITERATURE:SCIENCE:MEDICAL = 25:20:15:15:13:12` |
| semester | weighted_category | `SPRING:FALL:FULL_YEAR = 40:40:20` |
| credits | rule_based | semester で分岐:<br>　・FULL_YEAR → `{3, 4}` を `30:70` で抽選<br>　・SPRING / FALL → `{1, 2, 3}` を `10:65:25` で抽選 |
| level | weighted_category | `1:2:3:4 = 30:30:25:15` |
| max_students | numeric_distribution | department で分岐した一様分布:<br>　・COMMON → Uniform(100, 300) を 10 単位に丸め<br>　・MEDICAL → Uniform(80, 120) を 10 単位に丸め<br>　・その他学部専門 → Uniform(40, 150) を 10 単位に丸め |

### 列間関係

- `credits` ⇔ `semester`（FULL_YEAR は単位数が多い）。
- `max_students` ⇔ `department`（COMMON は大教室、MEDICAL は中規模）。

### 統計量の利用方針

- 構成比はサンプル件数が少ないため data_spec.md を優先。
- credits の中心は 2、max_students の平均はサンプル統計（mean=107）と整合する分布設計。

---

## テーブル 3: enrollment（履修）

### 履修件数決定

- 各 student について、在学期間 `Y_i = max(1, last_year_i - enrollment_year_i + 1)` を計算する。
  - `last_year_i = min(reference_year, enrollment_year_i + 修業年限 - 1)`
  - GRADUATED は `enrollment_year + 修業年限 - 1` を上限。
  - WITHDRAWN は `enrollment_year + Uniform_int(1, 修業年限) - 1` を在籍最終年度として個別決定（再現的）。
  - LEAVE / ENROLLED は `min(reference_year, enrollment_year + 修業年限 - 1)` を上限。
- 年間履修件数 `n_iy ~ Poisson(λ=10)`、上限 `min(30, 履修可能講義数)` にクリップ。
- 学生×年で `n_iy` 件の (course_code) を重み付き抽選（後述）。

### 列ごとの生成方式

| 列 | 方式 | 概要 |
|----|------|------|
| enrollment_id | sequential_id | `f"E{seq:010d}"`。最終件数確定後に 1 から連番で振り直し。E1 を満たす |
| student_id | rule_based (FK) | 親 student テーブルからサンプル。学生ごとに年×講義の組合せを生成するため、学生イテレーションで決定 |
| course_code | weighted_category (FK) | 学生の学年・学部と course.level / department に応じた重み付き抽選:<br>　・学年 1〜2 → COMMON 60% / 所属学部 30% / 他学部 10%<br>　・学年 3〜4(6) → 所属学部 60% / COMMON 20% / 他学部 20%<br>　・MEDICAL 学生は FULL_YEAR 比率を +20%<br>　・`abs(履修時学年 - course.level) <= 1` を満たす講義の重みを 2 倍（EV4 対応） |
| academic_year | date_range | 学生ごとの `[enrollment_year, last_year_i]` から重み付きサンプル（学年経過に伴い均等もしくは上位学年寄り）。E4, E5, E6 を満たす |
| attendance_rate | numeric_distribution | Truncated normal N(82, 18) を `[0.0, 100.0]` に clip。10% 程度は N(30, 15) の低出席混入で双峰化（EV1 の F/W 比率確保） |
| final_grade | correlated_numeric (条件付きカテゴリ) | `attendance_rate` の階層別に条件付き多項分布で抽選:<br>　・ar ≥ 90 → S:A:B = 55:35:10<br>　・80 ≤ ar < 90 → A:B:C = 50:35:15<br>　・60 ≤ ar < 80 → B:C:D = 35:45:20<br>　・40 ≤ ar < 60 → C:D:F = 25:50:25<br>　・ar < 40 → F:W = 60:40（W は ar ≤ 30 のとき主に発生するよう ar ≤ 30 では W:F = 70:30 に切替）<br>　EV1（S は ar≥90 由来、W は ar≤30 由来）を満たす |

### 列間関係

- `student_id` ⇔ `academic_year`（学生の在学期間で制限）。
- `student_id` × `course_code` ⇔ `academic_year` の組合せ一意（post sampling で保証）。
- `attendance_rate` ⇔ `final_grade`（条件付き分布で相関）。
- `course_code` の選択は `student.department`, `履修時学年(=academic_year - enrollment_year + 1)`, `course.level`, `course.department`, `course.semester` の組み合わせに依存。

### 統計量の利用方針

- attendance_rate のサンプル mean=81.1, std=17.9 を参考に N(82,18) を採用。
- final_grade 構成比（A 最多, S/B 多め）は条件付き分布の集計で再現される設計。

---

## post sampling（生成後の補正・除外）

| ID | 対応 |
|----|------|
| E5 | `academic_year` が学生 status 由来の在籍最終年度を超える行を除外（生成時に上限を設定済だが念のため最終チェック） |
| E7 | `(student_id, course_code, academic_year)` の組合せを `drop_duplicates(keep='first')`。重複は reject sampling で再生成し直し、最終的に件数が不足してもそのまま採用（enrollment は与件で固定しない） |
| E4 | `academic_year < enrollment_year` 行を除外（生成時に保証済） |
| E6 | `academic_year > 2025` 行を除外（生成時に保証済） |
| S3 | grade を再計算で上書きし、`grade > 修業年限上限` を完全排除 |
| EV3 | `max_students` 超過は警告対象（評価フェーズで違反率を計測）。生成側では補正しない |

post sampling 完了後に `enrollment_id` を 1 から振り直して E1 を保証する。

---

## oversampling 倍率

| テーブル | 倍率 | 理由 |
|----------|-----:|------|
| student | 1.00 | 与件として固定。post sampling での除外なし |
| course | 1.00 | 与件として固定。post sampling での除外なし |
| enrollment | 1.10 | `(student_id, course_code, academic_year)` の reject による減少を補う安全マージン。最終件数は決定論的に固定しない |

---

## 再現性

- `numpy.random.default_rng(seed)` を 1 つ生成し、student → course → enrollment の順に共有して使用する。
- 既定 seed は `42`（CLI から上書き可能）。

---

## 注意

- サンプルデータ（22/20/36 行）の特定レコードを再現しない。
- 個人を特定する氏名・住所等は生成しない。
- 出力は合成データであり匿名加工情報ではない。
