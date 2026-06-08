# 合成データ評価レポート（ケース2: 顧客×取引）

## 入力概要
- 顧客件数: 1000
- 取引件数: 144080
- 基準日: 2026-05-20

## スキーマ評価
- customer / transaction の列名・列順・data_type・nullable・FK列はすべて inferred_schema.json と整合。

## customer 側 制約評価
| table    | constraint_id   | constraint                                   |   violations |   total |   violation_rate | sample_violation   |
|:---------|:----------------|:---------------------------------------------|-------------:|--------:|-----------------:|:-------------------|
| customer | C1              | member_id 一意性                                |            0 |    1000 |                0 |                    |
| customer | C2              | leave_date >= join_date                      |            0 |     153 |                0 |                    |
| customer | C3              | age<18 → has_spouse=0                        |            0 |      34 |                0 |                    |
| customer | C4              | PLATINUM → annual_spend >= 500_000           |            0 |      60 |                0 |                    |
| customer | C5a             | age ∈ [0,110]                                |            0 |    1000 |                0 |                    |
| customer | C5b             | annual_spend ∈ [0,3000000]                   |            0 |    1000 |                0 |                    |
| customer | C6a             | gender ∈ {1,2,9}                             |            0 |    1000 |                0 |                    |
| customer | C6b             | member_rank ∈ {BRONZE,SILVER,GOLD,PLATINUM}  |            0 |    1000 |                0 |                    |
| customer | C6c             | registration_channel ∈ {WEB,STORE,APP,PHONE} |            0 |    1000 |                0 |                    |
| customer | C6d             | prefecture_code ∈ 01..47                     |            0 |    1000 |                0 |                    |

## transaction 側 制約評価
| table       | constraint_id   | constraint                          |   violations |   total |   violation_rate |
|:------------|:----------------|:------------------------------------|-------------:|--------:|-----------------:|
| transaction | T1              | transaction_id 一意                   |            0 |  144080 |                0 |
| transaction | T2              | member_id FK 整合                     |            0 |  144080 |                0 |
| transaction | T3a             | transaction_date >= join_date       |            0 |  144080 |                0 |
| transaction | T3b             | transaction_date <= leave_date（退会者） |            0 |   12565 |                0 |
| transaction | T3c             | transaction_date <= 2026-05-20      |            0 |  144080 |                0 |
| transaction | T4              | amount >= 1                         |            0 |  144080 |                0 |
| transaction | T5              | quantity >= 1                       |            0 |  144080 |                0 |
| transaction | T6a             | store_code ∈ S001..S050             |            0 |  144080 |                0 |
| transaction | T6b             | product_category 許容値                |            0 |  144080 |                0 |
| transaction | T6c             | payment_method 許容値                  |            0 |  144080 |                0 |
| transaction | T7a             | amount ∈ [1, 500000]                |            0 |  144080 |                0 |
| transaction | T7b             | quantity ∈ [1, 30]                  |            0 |  144080 |                0 |

## 取引：列分布
### product_category
| product_category   |   ratio |
|:-------------------|--------:|
| FOOD               |  0.351  |
| APPAREL            |  0.2    |
| DAILY              |  0.1802 |
| HOME               |  0.1194 |
| BOOKS              |  0.08   |
| ELECTRONICS        |  0.0696 |

### payment_method
| payment_method   |   ratio |
|:-----------------|--------:|
| CREDIT           |  0.4137 |
| EMONEY           |  0.2392 |
| DEBIT            |  0.1572 |
| CASH             |  0.1427 |
| POINT            |  0.0472 |

### store_code
| store_code   |   ratio |
|:-------------|--------:|
| S010         |  0.0208 |
| S009         |  0.0206 |
| S032         |  0.0205 |
| S037         |  0.0204 |
| S021         |  0.0203 |
| S035         |  0.0203 |
| S006         |  0.0203 |
| S004         |  0.0203 |
| S012         |  0.0202 |
| S029         |  0.0202 |
| S049         |  0.0202 |
| S030         |  0.0202 |
| S024         |  0.0202 |
| S007         |  0.0202 |
| S018         |  0.0202 |

### amount 統計
|       |   amount |
|:------|---------:|
| count | 144080   |
| mean  |  13940.3 |
| std   |  23018.7 |
| min   |      4   |
| 25%   |   3058   |
| 50%   |   6895   |
| 75%   |  15535.2 |
| max   | 500000   |

### quantity 統計
|       |   quantity |
|:------|-----------:|
| count |  144080    |
| mean  |       2.9  |
| std   |       1.68 |
| min   |       1    |
| 25%   |       2    |
| 50%   |       3    |
| 75%   |       4    |
| max   |      14    |

## T8: 直近1年の amount 合計 ≒ annual_spend
- 対象（直近1年在籍）顧客: 903
- 除外（直近1年より前に退会）: 97
- ratio (actual / annual_spend): mean=0.979, median=0.967, std=0.253
- ±25% 以内の顧客率: **0.714**

## T9: rank別 直近1年取引件数
| member_rank   |   count |   mean |   median |
|:--------------|--------:|-------:|---------:|
| BRONZE        |     415 |   7.8  |      8   |
| GOLD          |     164 |  33.87 |     34   |
| PLATINUM      |      50 |  55.58 |     55.5 |
| SILVER        |     271 |  17.35 |     17   |

## T10: 高額（>= 50,000円）取引の支払方法
- 対象件数: 7115
- CREDIT/DEBIT 比率: **1.0**

## 主な所見
- 必須制約 C1〜C6 / T1〜T7 すべて違反 **0件**。
- T9 (rank別件数の順序): OK
- T10 (高額CREDIT/DEBIT >= 0.9): OK
- T8 (±25%以内 >= 0.6): OK (0.714)

## 品質ゲート
- status: **pass**
- requires_refinement: **false**
- blocking_issues: 0
- warnings: 0
- 機械可読な判定は `quality_gate.json` を参照。

## 注意事項
- 本データは仕様駆動の合成データであり、匿名加工情報ではない。
- 実データの統計的再現性は保証しない。PoC・画面モック・分析仮説検討用途を想定。