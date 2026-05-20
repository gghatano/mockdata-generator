# constraint_plan.md（ケース2）

## generation_constraint（生成時に直接保証）

| ID | 制約 | 反映方法 |
|----|------|----------|
| C1 / T1 | 一意ID | sequential_id |
| C5 / T7 | 値域 | 分布生成時に clip |
| C6 / T6 | コード値 | weighted_category で許容値からサンプル |
| T2 | FK 整合 | 取引生成時、対象会員を customer 側からサンプル |
| T3 | 在籍期間内 | 取引日は `[join_date, min(leave_date, reference_date)]` から一様サンプル |
| T4 | 金額 >= 1 | log-normal の結果を max(1, ⋅) で保証 |
| T5 | 数量 >= 1 | 離散分布で 1 を最小値とする |

## post_sampling_constraint

| ID | 制約 | 対応 |
|----|------|------|
| C2 | leave_date >= join_date | 派生計算で違反は出ない想定。最終確認して違反は除外。 |
| C3 | age<18 → has_spouse=0 | 強制上書き |
| C4 | PLATINUM → annual_spend >= 500_000 | reject sampling |
| T3' | 取引日 ≤ reference_date | 生成時に max() で clip。違反検査のみ。 |

## validation_only_constraint

| ID | 内容 |
|----|------|
| C7〜C9 | 顧客側の構成比・列間関係（ケース1と同等） |
| T8 | 直近1年の amount 合計 ≒ annual_spend（±25%以内の会員比率を計測） |
| T9 | rank別 1年取引件数 平均の順序 |
| T10 | amount >= 50,000 における CREDIT/DEBIT 比率 >= 90% |

## oversampling

- 顧客側: 1.05倍
- 取引側: 各顧客あたりの件数決定は Poisson で年あたり期待値を rank 別に設定するため、過不足は許容（合計件数は決定論的に固定しない）。
- T3 違反はゼロを目標とするため oversampling 不要。
