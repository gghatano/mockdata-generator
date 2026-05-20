# 制約条件（ケース2: 顧客×取引）

## customer 側（ケース1から継承）

- **C1**: member_id 一意。
- **C2**: leave_date が非null の場合、leave_date >= join_date。
- **C3**: age < 18 の行は has_spouse = 0。
- **C4**: member_rank = 'PLATINUM' の行は annual_spend >= 500000。
- **C5**: 値域 (age ∈ [0,110], annual_spend ∈ [0, 3,000,000])。
- **C6**: コード値 (gender, member_rank, registration_channel, prefecture_code) は許容値のみ。

## transaction 側

- **T1**: transaction_id は全行で一意。
- **T2 (FK)**: 各 transaction.member_id は customer.member_id に存在する。
- **T3 (在籍期間内)**: customer.join_date ≤ transaction_date。退会会員は transaction_date ≤ leave_date。すべて transaction_date ≤ 基準日(2026-05-20)。
- **T4 (金額正)**: amount >= 1。
- **T5 (数量正)**: quantity >= 1。
- **T6 (コード値)**: store_code ∈ S001..S050、product_category ∈ 許容値、payment_method ∈ 許容値。
- **T7 (値域)**: amount ∈ [1, 500000], quantity ∈ [1, 30]。

## 評価のみ

- **T8 (年間合計の整合)**: 各会員の直近1年（基準日から遡る1年）の amount 合計は、会員の annual_spend と ±25% 以内で整合（評価のみ；モンテカルロ性のため厳密一致は求めない）。
- **T9 (rank別1年取引件数)**: 平均件数の順序 BRONZE < SILVER < GOLD < PLATINUM。
- **T10 (高額時の支払方法)**: amount >= 50,000 の取引は CREDIT または DEBIT が 90% 以上を占める。
