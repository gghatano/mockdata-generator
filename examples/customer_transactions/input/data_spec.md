# 顧客マスタ × 取引履歴 データ仕様メモ

## 概要

小売チェーンの会員マスタ（customer）と、その会員が行った取引履歴（transaction）の2テーブル構成。
分析・画面モック・テストデータ用途を想定。
取引日 = 2026-05-20（基準日）以前。

## customer 仕様

ケース1（顧客マスタ単体）と同一。詳細は `input/customer_table_definition.csv` を参照。要点のみ再掲：

- gender 構成比: 男:女:不明 = 45:50:5
- age: 切断正規 N(40, 17)、[0, 110]
- 都道府県上位9: 13, 27, 14, 40, 11, 23, 28, 01, 12
- join_date: 2010-01-01〜2025-12-31
- leave_date: 約 15% に設定
- member_rank: BRONZE:SILVER:GOLD:PLATINUM = 45:30:18:7
- annual_spend は **直近1年（基準日2026-05-20から遡る1年間）の購入合計（円）** とする
- has_spouse は age<18 で必ず 0

## transaction 仕様

### transaction_id
- `T` + 10桁ゼロ埋め連番。重複不可。

### member_id
- customer.member_id への外部キー。customer に存在しない member_id は禁止。

### transaction_date
- 取引日。**会員の在籍期間内**（join_date ≤ transaction_date、退会会員は ≤ leave_date）。
- 基準日 2026-05-20 を超えない。

### store_code
- `S001`〜`S050` の 50 店舗。
- 概ね均等分布。

### product_category
- `FOOD`, `DAILY`, `APPAREL`, `HOME`, `BOOKS`, `ELECTRONICS`。
- 構成比は概ね FOOD:DAILY:APPAREL:HOME:BOOKS:ELECTRONICS = 35:18:20:12:8:7。

### quantity
- 1〜30 点。categoryによって分布が異なる（FOOD/DAILYは平均高め、ELECTRONICSは1〜2が中心）。

### amount
- 1〜500,000 円。category と rank に依存する。

### payment_method
- `CASH`, `CREDIT`, `DEBIT`, `EMONEY`, `POINT`。
- 構成比は概ね CREDIT:EMONEY:CASH:DEBIT:POINT = 40:25:15:15:5。
- 高額（>=50,000円）は概ね CREDIT または DEBIT。

## 列間関係（顧客 × 取引）

- 1会員の直近1年の `amount` 合計が、会員の `annual_spend` と概ね一致する（±20% 程度の誤差を許容）。
- 会員の在籍期間（年数）にわたって取引が生成される。各年の合計取引額は annual_spend の 0.7〜1.3 倍の範囲でばらつく。
- 会員ランク別 1年あたり取引件数（中央値）：
  - BRONZE: 8 件
  - SILVER: 18 件
  - GOLD: 35 件
  - PLATINUM: 55 件
- 1取引の amount 中央値は rank と category に依存：
  - rank 別ベース: BRONZE 3,000円 / SILVER 6,000円 / GOLD 10,000円 / PLATINUM 18,000円
  - category 係数: FOOD 0.5, DAILY 0.4, APPAREL 1.3, HOME 1.8, BOOKS 0.6, ELECTRONICS 3.0
