# 大学履修データ 仕様メモ

3 テーブル構成の合成データを生成する。

```
student ──< enrollment >── course
   (1)         (N)         (1)
```

- 1 学生は 0 件以上の履修を持つ。
- 1 講義は 0 件以上の履修を持つ。
- enrollment は student × course の多対多関係を表す中間テーブル。

基準学年度（reference_year） = **2025年度**。

---

## student（学生マスタ）

学生個人の基本属性。個人を特定する氏名・住所等は持たない。

| 列 | 仕様 |
|----|------|
| student_id | `S` + 8桁。先頭4桁は入学年度。例: `S20230007`。 |
| enrollment_year | 入学年度。2018〜2025。 |
| department | 学部。`LITERATURE`, `SCIENCE`, `ENGINEERING`, `ECONOMICS`, `MEDICAL` の5つ。 |
| grade | 現在の学年。MEDICAL は 1〜6、それ以外は 1〜4。 |
| gender | 1=男性, 2=女性, 9=不明。構成比は 50:48:2。MEDICAL のみ女性比率がやや高い。 |
| status | `ENROLLED`（在籍）, `LEAVE`（休学）, `GRADUATED`（卒業）, `WITHDRAWN`（退学）。 |
| gpa | 通算GPA。0.0〜4.0。MEDICAL は平均が高め (≒ 3.6)、その他は ≒ 3.0。 |

### 構成比

- 学部比率: ENGINEERING:LITERATURE:SCIENCE:ECONOMICS:MEDICAL = 30:20:18:22:10
- status 比率: 入学からの経過年数で決まる
  - 4年経過（MEDICAL は 6年経過）以上 → GRADUATED 80% / WITHDRAWN 8% / LEAVE 2% / ENROLLED 10%
  - 経過年数 < 修業年限 → ENROLLED 92% / LEAVE 5% / WITHDRAWN 3%
- 入学年度の構成は概ね均等（2018〜2025）。ただし MEDICAL は 6年制のため、各年度に在籍数を持つ。

### 学年と入学年度の関係

- 通常: `grade = min(reference_year - enrollment_year + 1, 学部の修業年限)`
- 休学者・留年は稀にあるが、本仕様では除外する（grade は理論値で算出）。

---

## course（講義マスタ）

| 列 | 仕様 |
|----|------|
| course_code | `C` + 4桁。 |
| department | 開講学部。`LITERATURE`, `SCIENCE`, `ENGINEERING`, `ECONOMICS`, `MEDICAL`, `COMMON`（全学共通教養）の6つ。 |
| credits | 1〜4 単位。FULL_YEAR は通常4単位、SPRING/FALLは 2 単位中心。 |
| semester | `SPRING`（前期）, `FALL`（後期）, `FULL_YEAR`（通年）。 |
| level | 対象学年。1〜4。 |
| max_students | 定員。20〜300。学部専門は 40〜150、共通教養は 100〜300、医学専門は 80〜120。 |

### 構成比

- department 比率: COMMON:ENGINEERING:ECONOMICS:LITERATURE:SCIENCE:MEDICAL = 25:20:15:15:13:12
- level 比率: 1〜4 が概ね 30:30:25:15
- semester 比率: SPRING:FALL:FULL_YEAR = 40:40:20

---

## enrollment（履修）

| 列 | 仕様 |
|----|------|
| enrollment_id | `E` + 10桁。 |
| student_id | student.student_id への FK。 |
| course_code | course.course_code への FK。 |
| academic_year | 履修年度。学生の在学期間内。 |
| final_grade | `S, A, B, C, D, F, W`（W=履修取消で点数なし）。 |
| attendance_rate | 出席率（%）。0.0〜100.0。 |

### 履修件数の目安

- 1 学生の年間履修件数: 平均 10 件（Poisson(10)）。
- 学年 1〜2 は COMMON 中心、3〜4 は専門学部の講義が中心。
- MEDICAL は通年講義（FULL_YEAR）の比率が高い。

### 成績と出席率の関係

- attendance_rate >= 80 → S/A/B が中心
- 60 <= attendance_rate < 80 → B/C が中心
- 40 <= attendance_rate < 60 → C/D が中心
- attendance_rate < 40 → F または W が中心
- W は出席率 30 以下に概ね限られる
- S は出席率 90 以上の中から発生する

### 学生×講義×年度の一意性

同一学生が同一講義を同一年度に重複登録することはない。再履修は別年度で行う。
