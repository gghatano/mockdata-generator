# 合成データ評価レポート

## 生成条件
- 生成コマンド: `uv run python examples/customer/src/generator.py --rows 10000 --seed 42`
- rows: 10000 / seed: 42

## 入力概要
- サンプル件数: 40
- 合成件数: 10000
- 列数: 11

## スキーマ評価
- 列名・列順ともに inferred_schema.json と一致
- data_type は全列で整合
- nullable=false 列の欠損なし

### 欠損率比較
| 列 | sample | synthetic |
|----|-------:|----------:|
| member_id | 0.000 | 0.000 |
| gender | 0.000 | 0.000 |
| age | 0.000 | 0.000 |
| prefecture_code | 0.000 | 0.000 |
| join_date | 0.000 | 0.000 |
| leave_date | 0.875 | 0.847 |
| member_rank | 0.000 | 0.000 |
| annual_spend | 0.000 | 0.000 |
| has_spouse | 0.000 | 0.000 |
| email_optin | 0.000 | 0.000 |
| registration_channel | 0.000 | 0.000 |

## 数値列の分布
### age

|        |   synthetic |   sample |
|:-------|------------:|---------:|
| min    |       15    |     16   |
| max    |      100    |     73   |
| mean   |       42.66 |     40.4 |
| std    |       15.08 |     16.2 |
| median |       42    |     38.5 |

### annual_spend

|        |        synthetic |        sample |
|:-------|-----------------:|--------------:|
| min    |   4250           |   9000        |
| max    |      2.25428e+06 |      1.24e+06 |
| mean   | 236630           | 331600        |
| std    | 261620           | 312329        |
| median | 137265           | 217500        |

## カテゴリ列の頻度
### gender
|   gender |   synthetic |   sample |   diff_pt |
|---------:|------------:|---------:|----------:|
|        2 |      0.4955 |    0.475 |    0.0205 |
|        1 |      0.4544 |    0.45  |    0.0044 |
|        9 |      0.0501 |    0.075 |   -0.0249 |

### member_rank
| member_rank   |   synthetic |   sample |   diff_pt |
|:--------------|------------:|---------:|----------:|
| BRONZE        |      0.4508 |    0.325 |    0.1258 |
| SILVER        |      0.2953 |    0.25  |    0.0453 |
| GOLD          |      0.1836 |    0.25  |   -0.0664 |
| PLATINUM      |      0.0703 |    0.175 |   -0.1047 |

### registration_channel
| registration_channel   |   synthetic |   sample |   diff_pt |
|:-----------------------|------------:|---------:|----------:|
| WEB                    |      0.3961 |    0.35  |    0.0461 |
| APP                    |      0.2505 |    0.325 |   -0.0745 |
| STORE                  |      0.2498 |    0.225 |    0.0248 |
| PHONE                  |      0.1036 |    0.1   |    0.0036 |

### has_spouse
|   has_spouse |   synthetic |   sample |   diff_pt |
|-------------:|------------:|---------:|----------:|
|            1 |      0.5849 |     0.65 |   -0.0651 |
|            0 |      0.4151 |     0.35 |    0.0651 |

### email_optin
|   email_optin |   synthetic |   sample |   diff_pt |
|--------------:|------------:|---------:|----------:|
|             1 |      0.7024 |    0.675 |    0.0274 |
|             0 |      0.2976 |    0.325 |   -0.0274 |

## 列間関係
### member_rank × annual_spend 平均
| member_rank   |   mean_annual_spend |
|:--------------|--------------------:|
| BRONZE        |               61436 |
| GOLD          |              458317 |
| PLATINUM      |              862747 |
| SILVER        |              217191 |

### 年代別 has_spouse=1 比率
| age_bin   |   count |   mean |
|:----------|--------:|-------:|
| <18       |     278 |  0     |
| 18-29     |    1847 |  0.238 |
| 30-39     |    2354 |  0.557 |
| 40-59     |    4078 |  0.726 |
| 60+       |    1443 |  0.788 |

## 制約評価（必須 C1〜C6）
| constraint_id   | constraint                                   |   violations |   total |   violation_rate | sample_violation   |
|:----------------|:---------------------------------------------|-------------:|--------:|-----------------:|:-------------------|
| C1              | member_id 一意性                                |            0 |   10000 |                0 |                    |
| C2              | leave_date >= join_date                      |            0 |    1531 |                0 |                    |
| C3              | age<18 → has_spouse=0                        |            0 |     278 |                0 |                    |
| C4              | PLATINUM → annual_spend >= 500_000           |            0 |     703 |                0 |                    |
| C5a             | age ∈ [0,110]                                |            0 |   10000 |                0 |                    |
| C5b             | annual_spend ∈ [0,3000000]                   |            0 |   10000 |                0 |                    |
| C6a             | gender ∈ {1,2,9}                             |            0 |   10000 |                0 |                    |
| C6b             | member_rank ∈ {BRONZE,SILVER,GOLD,PLATINUM}  |            0 |   10000 |                0 |                    |
| C6c             | registration_channel ∈ {WEB,STORE,APP,PHONE} |            0 |   10000 |                0 |                    |
| C6d             | prefecture_code ∈ 01..47                     |            0 |   10000 |                0 |                    |

## 推奨制約の機械判定（C7/C8: warning 扱い）
| constraint_id   | constraint                | result   | detail                                                                                                                                                                                                                                                                        |
|:----------------|:--------------------------|:---------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| C7              | gender 構成比 45:50:5 (±5pt) | OK       | [{'gender': 1, 'actual': 0.4544, 'target': 0.45, 'diff_pt': 0.0044}, {'gender': 2, 'actual': 0.4955, 'target': 0.5, 'diff_pt': -0.0045}, {'gender': 9, 'actual': 0.0501, 'target': 0.05, 'diff_pt': 0.0001}]                                                                  |
| C8              | 年代別 has_spouse 比率レンジ      | OK       | [{'band': '<20', 'count': 503, 'spouse_ratio': 0.0974, 'range': [0.0, 0.1], 'ok': True}, {'band': '30-39', 'count': 2354, 'spouse_ratio': 0.5573, 'range': [0.4, 0.7], 'ok': True}, {'band': '40+', 'count': 5521, 'spouse_ratio': 0.7421, 'range': [0.6, 0.85], 'ok': True}] |

## 主な差異と所見
- 必須制約 C1〜C6 の違反は **0件**。
- C9 (rank × annual_spend の平均順序): OK
- C7 (gender 構成比 45:50:5 (±5pt)): OK
- C8 (年代別 has_spouse 比率レンジ): OK

## 品質ゲート
- status: **pass**
- requires_refinement: **false**
- blocking_issues: 0
- warnings: 0
- 機械可読な判定は `quality_gate.json` を参照。

## 注意事項
- 本データは仕様駆動の合成データであり、匿名加工情報ではない。
- 実データの統計的再現性は保証しない。PoC・画面モック・分析仮説検討用途を想定。
- サンプル件数が少ない (n=40) ため、サンプルとの差異は仕様優先で評価している。