# 合成データ評価レポート

## 入力概要
- サンプル件数: 40
- 合成件数: 5000
- 列数: 11

## スキーマ評価
- 列名・列順ともに inferred_schema.json と一致

### 欠損率比較
| 列 | sample | synthetic |
|----|-------:|----------:|
| member_id | 0.000 | 0.000 |
| gender | 0.000 | 0.000 |
| age | 0.000 | 0.000 |
| prefecture_code | 0.000 | 0.000 |
| join_date | 0.000 | 0.000 |
| leave_date | 0.875 | 0.849 |
| member_rank | 0.000 | 0.000 |
| annual_spend | 0.000 | 0.000 |
| has_spouse | 0.000 | 0.000 |
| email_optin | 0.000 | 0.000 |
| registration_channel | 0.000 | 0.000 |

## 数値列の分布
### age

|        |   synthetic |   sample |
|:-------|------------:|---------:|
| min    |        0    |     16   |
| max    |      108    |     73   |
| mean   |       40.42 |     40.4 |
| std    |       16.67 |     16.2 |
| median |       40    |     38.5 |

### annual_spend

|        |        synthetic |        sample |
|:-------|-----------------:|--------------:|
| min    |   2540           |   9000        |
| max    |      1.86276e+06 |      1.24e+06 |
| mean   | 233580           | 331600        |
| std    | 261333           | 312329        |
| median | 136772           | 217500        |

## カテゴリ列の頻度
### gender
|   gender |   synthetic |   sample |   diff_pt |
|---------:|------------:|---------:|----------:|
|        2 |      0.4946 |    0.475 |    0.0196 |
|        1 |      0.4568 |    0.45  |    0.0068 |
|        9 |      0.0486 |    0.075 |   -0.0264 |

### member_rank
| member_rank   |   synthetic |   sample |   diff_pt |
|:--------------|------------:|---------:|----------:|
| BRONZE        |      0.4388 |    0.325 |    0.1138 |
| SILVER        |      0.313  |    0.25  |    0.063  |
| GOLD          |      0.179  |    0.25  |   -0.071  |
| PLATINUM      |      0.0692 |    0.175 |   -0.1058 |

### registration_channel
| registration_channel   |   synthetic |   sample |   diff_pt |
|:-----------------------|------------:|---------:|----------:|
| WEB                    |      0.394  |    0.35  |    0.044  |
| STORE                  |      0.2596 |    0.225 |    0.0346 |
| APP                    |      0.247  |    0.325 |   -0.078  |
| PHONE                  |      0.0994 |    0.1   |   -0.0006 |

### has_spouse
|   has_spouse |   synthetic |   sample |   diff_pt |
|-------------:|------------:|---------:|----------:|
|            1 |      0.5336 |     0.65 |   -0.1164 |
|            0 |      0.4664 |     0.35 |    0.1164 |

### email_optin
|   email_optin |   synthetic |   sample |   diff_pt |
|--------------:|------------:|---------:|----------:|
|             1 |      0.6996 |    0.675 |    0.0246 |
|             0 |      0.3004 |    0.325 |   -0.0246 |

## 列間関係
### member_rank × annual_spend 平均
| member_rank   |   mean_annual_spend |
|:--------------|--------------------:|
| BRONZE        |               59669 |
| GOLD          |              455418 |
| PLATINUM      |              873387 |
| SILVER        |              209070 |

### 年代別 has_spouse=1 比率
| age_bin   |   count |   mean |
|:----------|--------:|-------:|
| <18       |     451 |  0     |
| 18-29     |     840 |  0.212 |
| 30-39     |    1171 |  0.553 |
| 40-59     |    1877 |  0.706 |
| 60+       |     661 |  0.782 |

## 制約評価
| constraint_id   | constraint                                   |   violations |   total |   violation_rate | sample_violation   |
|:----------------|:---------------------------------------------|-------------:|--------:|-----------------:|:-------------------|
| C1              | member_id 一意性                                |            0 |    5000 |                0 |                    |
| C2              | leave_date >= join_date                      |            0 |     754 |                0 |                    |
| C3              | age<18 → has_spouse=0                        |            0 |     451 |                0 |                    |
| C4              | PLATINUM → annual_spend >= 500_000           |            0 |     346 |                0 |                    |
| C5a             | age ∈ [0,110]                                |            0 |    5000 |                0 |                    |
| C5b             | annual_spend ∈ [0,3000000]                   |            0 |    5000 |                0 |                    |
| C6a             | gender ∈ {1,2,9}                             |            0 |    5000 |                0 |                    |
| C6b             | member_rank ∈ {BRONZE,SILVER,GOLD,PLATINUM}  |            0 |    5000 |                0 |                    |
| C6c             | registration_channel ∈ {WEB,STORE,APP,PHONE} |            0 |    5000 |                0 |                    |
| C6d             | prefecture_code ∈ 01..47                     |            0 |    5000 |                0 |                    |

## 主な差異と所見
- 必須制約 C1〜C6 の違反は **0件**。
- C9 (rank × annual_spend の平均順序): OK

## 注意事項
- 本データは仕様駆動の合成データであり、匿名加工情報ではない。
- 実データの統計的再現性は保証しない。PoC・画面モック・分析仮説検討用途を想定。
- サンプル件数が少ない (n=40) ため、サンプルとの差異は仕様優先で評価している。