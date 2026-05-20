# 合成データ評価レポート（ケース3: 大学履修）

## 入力概要
- 学生件数 (synthetic / sample): 1000 / 22
- 講義件数 (synthetic / sample): 200 / 20
- 履修件数 (synthetic / sample): 33017 / 36
- 基準年度 (reference_year): 2025

## スキーマ評価
### student
- 列名・列順ともに inferred_schema.json と一致

| 列 | dtype |
|----|-------|
| student_id | str |
| enrollment_year | int64 |
| department | str |
| grade | int64 |
| gender | int64 |
| status | str |
| gpa | float64 |

### course
- 列名・列順ともに inferred_schema.json と一致

| 列 | dtype |
|----|-------|
| course_code | str |
| department | str |
| credits | int64 |
| semester | str |
| level | int64 |
| max_students | int64 |

### enrollment
- 列名・列順ともに inferred_schema.json と一致

| 列 | dtype |
|----|-------|
| enrollment_id | str |
| student_id | str |
| course_code | str |
| academic_year | int64 |
| final_grade | str |
| attendance_rate | float64 |

## student 分布
### 数値列
#### enrollment_year
|        |    value |
|:-------|---------:|
| min    | 2018     |
| max    | 2025     |
| mean   | 2021.48  |
| std    |    2.317 |
| median | 2021     |

#### grade
|        |   value |
|:-------|--------:|
| min    |   1     |
| max    |   6     |
| mean   |   3.342 |
| std    |   1.224 |
| median |   4     |

#### gpa
|        |   value |
|:-------|--------:|
| min    |   1.29  |
| max    |   3.99  |
| mean   |   3.04  |
| std    |   0.489 |
| median |   3.08  |

### カテゴリ列
#### department
| department   |   count |   ratio |
|:-------------|--------:|--------:|
| ENGINEERING  |     292 |   0.292 |
| ECONOMICS    |     214 |   0.214 |
| LITERATURE   |     213 |   0.213 |
| SCIENCE      |     170 |   0.17  |
| MEDICAL      |     111 |   0.111 |

#### gender
|   gender |   count |   ratio |
|---------:|--------:|--------:|
|        1 |     500 |   0.5   |
|        2 |     474 |   0.474 |
|        9 |      26 |   0.026 |

#### status
| status    |   count |   ratio |
|:----------|--------:|--------:|
| ENROLLED  |     531 |   0.531 |
| GRADUATED |     386 |   0.386 |
| WITHDRAWN |      47 |   0.047 |
| LEAVE     |      36 |   0.036 |

## course 分布
### 数値列
#### credits
|        |   value |
|:-------|--------:|
| min    |   1     |
| max    |   4     |
| mean   |   2.515 |
| std    |   0.856 |
| median |   2     |

#### level
|        |   value |
|:-------|--------:|
| min    |   1     |
| max    |   4     |
| mean   |   2.16  |
| std    |   1.015 |
| median |   2     |

#### max_students
|        |   value |
|:-------|--------:|
| min    |  40     |
| max    | 300     |
| mean   | 125.25  |
| std    |  58.832 |
| median | 110     |

### カテゴリ列
#### department
| department   |   count |   ratio |
|:-------------|--------:|--------:|
| COMMON       |      58 |   0.29  |
| ENGINEERING  |      44 |   0.22  |
| ECONOMICS    |      35 |   0.175 |
| LITERATURE   |      24 |   0.12  |
| MEDICAL      |      21 |   0.105 |
| SCIENCE      |      18 |   0.09  |

#### semester
| semester   |   count |   ratio |
|:-----------|--------:|--------:|
| SPRING     |      81 |   0.405 |
| FALL       |      76 |   0.38  |
| FULL_YEAR  |      43 |   0.215 |

## enrollment 分布
### 数値列
#### academic_year
|        |    value |
|:-------|---------:|
| min    | 2018     |
| max    | 2025     |
| mean   | 2022.18  |
| std    |    2.032 |
| median | 2022     |

#### attendance_rate
|        |   value |
|:-------|--------:|
| min    |   0.3   |
| max    | 100     |
| mean   |  72.163 |
| std    |  19.838 |
| median |  76.1   |

### カテゴリ列
#### final_grade
| final_grade   |   count |   ratio |
|:--------------|--------:|--------:|
| C             |    8023 |  0.243  |
| B             |    7585 |  0.2297 |
| A             |    5833 |  0.1767 |
| D             |    4507 |  0.1365 |
| S             |    3295 |  0.0998 |
| F             |    2298 |  0.0696 |
| W             |    1476 |  0.0447 |

## 制約評価
| table      | constraint_id   | constraint                                        |   violations |   total |   violation_rate | sample_violation   |
|:-----------|:----------------|:--------------------------------------------------|-------------:|--------:|-----------------:|:-------------------|
| student    | S1              | student_id 一意                                     |            0 |    1000 |                0 |                    |
| student    | S2              | enrollment_year ∈ [2018,2025]                     |            0 |    1000 |                0 |                    |
| student    | S3              | grade 上限は学部依存（MEDICAL=6, その他=4）                   |            0 |    1000 |                0 |                    |
| student    | S4              | gpa ∈ [0.0, 4.0]                                  |            0 |    1000 |                0 |                    |
| student    | S5a             | department 許容値                                    |            0 |    1000 |                0 |                    |
| student    | S5b             | gender ∈ {1,2,9}                                  |            0 |    1000 |                0 |                    |
| student    | S5c             | status 許容値                                        |            0 |    1000 |                0 |                    |
| student    | S6              | student_id 先頭4桁 = enrollment_year                 |            0 |    1000 |                0 |                    |
| course     | CR1             | course_code 一意                                    |            0 |     200 |                0 |                    |
| course     | CR2a            | department 許容値（含む COMMON）                         |            0 |     200 |                0 |                    |
| course     | CR2b            | semester 許容値                                      |            0 |     200 |                0 |                    |
| course     | CR3a            | credits ∈ [1,4]                                   |            0 |     200 |                0 |                    |
| course     | CR3b            | level ∈ [1,4]                                     |            0 |     200 |                0 |                    |
| course     | CR3c            | max_students ∈ [20,300]                           |            0 |     200 |                0 |                    |
| course     | CR4             | FULL_YEAR の credits は 3〜4 推奨（参考）                  |            0 |      43 |                0 |                    |
| course     | CR1f            | course_code 形式 C\d{4}                             |            0 |     200 |                0 |                    |
| enrollment | E1              | enrollment_id 一意                                  |            0 |   33017 |                0 |                    |
| enrollment | E1f             | enrollment_id 形式 E\d{10}                          |            0 |   33017 |                0 |                    |
| enrollment | E2              | student_id ∈ student.student_id                   |            0 |   33017 |                0 |                    |
| enrollment | E3              | course_code ∈ course.course_code                  |            0 |   33017 |                0 |                    |
| enrollment | E4              | academic_year >= student.enrollment_year          |            0 |   33017 |                0 |                    |
| enrollment | E5              | GRADUATED/WITHDRAWN: academic_year <= 入学年度+修業年限-1 |            0 |   16984 |                0 |                    |
| enrollment | E6              | academic_year <= 2025                             |            0 |   33017 |                0 |                    |
| enrollment | E7              | (student_id, course_code, academic_year) 一意       |            0 |   33017 |                0 |                    |
| enrollment | E8              | final_grade ∈ {S,A,B,C,D,F,W} or null             |            0 |   33017 |                0 |                    |
| enrollment | E9              | attendance_rate ∈ [0.0, 100.0]                    |            0 |   33017 |                0 |                    |

## 評価のみ制約 EV1〜EV4
### EV1: final_grade × attendance_rate
| 成績 | n | 条件 | 比率 | 閾値 | 判定 |
|------|---:|------|-----:|-----:|------|
| S | 3295 | ar>=90 | 1.0 | 0.9 | OK |
| W | 1476 | ar<=30 | 1.0 | 0.8 | OK |
| F | 2298 | ar<50 | 1.0 | 0.7 | OK |
- 総合判定: **OK**

### EV2: 学部別 GPA 平均（MEDICAL が最大か）
|             |   mean_gpa |
|:------------|-----------:|
| ECONOMICS   |     3.093  |
| ENGINEERING |     2.9288 |
| LITERATURE  |     2.7929 |
| MEDICAL     |     3.5438 |
| SCIENCE     |     3.1456 |
- top_dept = **MEDICAL**: OK

### EV3: 各講義の年間履修者数 ≤ max_students
- (course_code, academic_year) ペア数: 1590
- 定員超過ペア数: 0 (rate=0.0)
- 最大超過人数: 0
- 判定: **OK**

### EV4: 学生学年と講義 level の差が ±1 以内の比率
- n=33017, within_1_ratio=0.7618
- 判定 (>=0.7): **OK**

## 主な所見
- 必須制約 S1〜S6 / CR1〜CR3 / E1〜E9 の違反は **0件**。
- EV1 (final_grade × attendance_rate): OK
- EV2 (MEDICAL の GPA 平均が最大): OK
- EV3 (定員超過): OK (超過ペア=0)
- EV4 (学年×level ±1 比率): within=0.7618

## 既知の限界 / 注意事項
- 本データは仕様駆動の合成データであり、匿名加工情報ではない。
- サンプル件数 (student=22, course=20, enrollment=36) が少ないため、
  サンプルとの統計的差異は data_spec.md / inferred_schema.json の指定を優先している。
- 休学・留年は除外し、grade は理論値 (enrollment_year + 修業年限) で算出している。
- 想定利用範囲は PoC・画面モック・分析仮説検討用途。実データの統計的再現性は保証しない。