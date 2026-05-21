# 合成データ評価レポート（ケース2: 顧客×取引）

## 入力概要
- 顧客件数: 300
- 取引件数: 40400
- 基準日: 2026-05-20

## customer 側 制約評価
| table    | constraint_id   | constraint                                   |   violations |   total |   violation_rate | sample_violation   |
|:---------|:----------------|:---------------------------------------------|-------------:|--------:|-----------------:|:-------------------|
| customer | C1              | member_id 一意性                                |            0 |     300 |                0 |                    |
| customer | C2              | leave_date >= join_date                      |            0 |      51 |                0 |                    |
| customer | C3              | age<18 → has_spouse=0                        |            0 |      29 |                0 |                    |
| customer | C4              | PLATINUM → annual_spend >= 500_000           |            0 |      20 |                0 |                    |
| customer | C5a             | age ∈ [0,110]                                |            0 |     300 |                0 |                    |
| customer | C5b             | annual_spend ∈ [0,3000000]                   |            0 |     300 |                0 |                    |
| customer | C6a             | gender ∈ {1,2,9}                             |            0 |     300 |                0 |                    |
| customer | C6b             | member_rank ∈ {BRONZE,SILVER,GOLD,PLATINUM}  |            0 |     300 |                0 |                    |
| customer | C6c             | registration_channel ∈ {WEB,STORE,APP,PHONE} |            0 |     300 |                0 |                    |
| customer | C6d             | prefecture_code ∈ 01..47                     |            0 |     300 |                0 |                    |

## transaction 側 制約評価
| table       | constraint_id   | constraint                          |   violations |   total |   violation_rate |
|:------------|:----------------|:------------------------------------|-------------:|--------:|-----------------:|
| transaction | T1              | transaction_id 一意                   |            0 |   40400 |                0 |
| transaction | T2              | member_id FK 整合                     |            0 |   40400 |                0 |
| transaction | T3a             | transaction_date >= join_date       |            0 |   40400 |                0 |
| transaction | T3b             | transaction_date <= leave_date（退会者） |            0 |    5928 |                0 |
| transaction | T3c             | transaction_date <= 2026-05-20      |            0 |   40400 |                0 |
| transaction | T4              | amount >= 1                         |            0 |   40400 |                0 |
| transaction | T5              | quantity >= 1                       |            0 |   40400 |                0 |
| transaction | T6a             | store_code ∈ S001..S050             |            0 |   40400 |                0 |
| transaction | T6b             | product_category 許容値                |            0 |   40400 |                0 |
| transaction | T6c             | payment_method 許容値                  |            0 |   40400 |                0 |
| transaction | T7a             | amount ∈ [1, 500000]                |            0 |   40400 |                0 |
| transaction | T7b             | quantity ∈ [1, 30]                  |            0 |   40400 |                0 |

## 取引：列分布
### product_category
| product_category   |   ratio |
|:-------------------|--------:|
| FOOD               |  0.3481 |
| APPAREL            |  0.2015 |
| DAILY              |  0.1786 |
| HOME               |  0.1193 |
| BOOKS              |  0.0818 |
| ELECTRONICS        |  0.0706 |

### payment_method
| payment_method   |   ratio |
|:-----------------|--------:|
| CREDIT           |  0.4116 |
| EMONEY           |  0.2395 |
| DEBIT            |  0.1574 |
| CASH             |  0.1425 |
| POINT            |  0.049  |

### store_code
| store_code   |   ratio |
|:-------------|--------:|
| S046         |  0.0214 |
| S008         |  0.0211 |
| S004         |  0.021  |
| S049         |  0.0209 |
| S023         |  0.0209 |
| S003         |  0.0208 |
| S007         |  0.0208 |
| S038         |  0.0207 |
| S026         |  0.0206 |
| S033         |  0.0206 |
| S001         |  0.0204 |
| S002         |  0.0204 |
| S021         |  0.0204 |
| S048         |  0.0204 |
| S030         |  0.0203 |

### amount 統計
|       |    amount |
|:------|----------:|
| count |  40400    |
| mean  |  13590.1  |
| std   |  21609.4  |
| min   |      2    |
| 25%   |   2966.75 |
| 50%   |   6867    |
| 75%   |  15265.8  |
| max   | 500000    |

### quantity 統計
|       |   quantity |
|:------|-----------:|
| count |   40400    |
| mean  |       2.9  |
| std   |       1.67 |
| min   |       1    |
| 25%   |       2    |
| 50%   |       3    |
| 75%   |       4    |
| max   |      12    |

## T8: 直近1年の amount 合計 ≒ annual_spend
- 対象（直近1年在籍）顧客: 267
- 除外（直近1年より前に退会）: 33
- ratio (actual / annual_spend): mean=0.991, median=0.975, std=0.289
- ±25% 以内の顧客率: **0.682**

## T9: rank別 直近1年取引件数
| member_rank   |   count |   mean |   median |
|:--------------|--------:|-------:|---------:|
| BRONZE        |     114 |   8.05 |        8 |
| GOLD          |      52 |  33.12 |       33 |
| PLATINUM      |      16 |  49.25 |       47 |
| SILVER        |      83 |  17.04 |       17 |

## T10: 高額（>= 50,000円）取引の支払方法
- 対象件数: 1884
- CREDIT/DEBIT 比率: **1.0**

## 主な所見
- 必須制約 C1〜C6 / T1〜T7 すべて違反 **0件**。
- T9 (rank別件数の順序): OK
- T10 (高額CREDIT/DEBIT >= 0.9): OK
- T8 (±25%以内 >= 0.6): OK (0.682)

## 品質ゲート
- status: **pass**
- requires_refinement: **false**
- blocking_issues: 0
- warnings: 0
- 機械可読な判定は `quality_gate.json` を参照。

## 注意事項
- 本データは仕様駆動の合成データであり、匿名加工情報ではない。
- 実データの統計的再現性は保証しない。PoC・画面モック・分析仮説検討用途を想定。