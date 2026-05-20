# generation_plan.md（ケース2）

## 全体フロー

1. 顧客マスタを `--customers` 件生成（ケース1の方式を流用）。
2. 各顧客の在籍期間 `[join_date, min(leave_date, reference_date=2026-05-20)]` を計算。
3. 各顧客について、年間取引件数の中央値と在籍年数から取引件数 `N_i` を Poisson でサンプル。
4. 各顧客の在籍期間にわたって `N_i` 件の取引日を一様サンプル。
5. 各顧客の年合計が `annual_spend` × (0.7〜1.3) になるよう年単位で目標額を決定。
6. その年の取引数で目標額を Dirichlet 配分（alpha=2）し、各取引の amount を確定。
7. category は重み付き抽選、quantity は category 別離散分布、payment_method は amount に応じて切り替え。

## 顧客側パラメータ

ケース1と同一。`reference_date = 2026-05-20`。

## 取引側パラメータ

### 1年あたり取引件数（Poisson の lambda）

| rank | lambda |
|------|-------:|
| BRONZE | 8 |
| SILVER | 18 |
| GOLD | 35 |
| PLATINUM | 55 |

### 年合計額のばらつき

- 直近1年: `annual_spend` ± 0.0%（後で Dirichlet 配分するため厳密にはばらつく）
- それ以前の年: `annual_spend × Uniform(0.7, 1.3)`

### product_category 重み

FOOD:DAILY:APPAREL:HOME:BOOKS:ELECTRONICS = 35:18:20:12:8:7

### category 別 quantity 分布

| category | 分布 |
|----------|------|
| FOOD | 1+Poisson(3) (1〜30 にclip) |
| DAILY | 1+Poisson(2) |
| APPAREL | 1+Poisson(1) |
| HOME | 1+Poisson(1) |
| BOOKS | 1+Poisson(2) |
| ELECTRONICS | 1（90%）/ 2（10%） |

### amount 配分

各顧客 × 各年の目標合計を Dirichlet(alpha=2) で件数分に配分。
category 係数を掛けて、最終的に `[1, 500_000]` に clip。
ゼロ・負値は 1 にクリップ（T4）。

### payment_method 抽選

- 全体: CREDIT:EMONEY:CASH:DEBIT:POINT = 40:25:15:15:5
- amount >= 50,000: CREDIT:DEBIT = 70:30 に切替（T10 を満たすため）

### store_code

S001〜S050 から一様抽選。

## post sampling

- T3 違反: 在籍期間外の取引は除外。
- T2 違反: 全取引は顧客リストから member_id を引くため、原理的に発生しない。

## 再現性

`numpy.random.default_rng(seed)` を顧客→取引で共有。
