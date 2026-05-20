# generation_plan.md

inferred_schema.json と constraint_plan.md に基づき、各列の生成方式を定義する。

## 列ごとの生成方式

| 列 | 方式 | 概要 |
|----|------|------|
| member_id | sequential_id | `M` + ゼロ埋め7桁の連番（開始は 0000001） |
| gender | weighted_category | 1:2:9 = 45:50:5 |
| age | numeric_distribution | 切断正規 N(40, 17) を 0..110 に clip。ただし15未満/85超は確率を下げる |
| prefecture_code | weighted_category | 上位9都道府県(13,27,14,40,11,23,28,01,12)を高頻度、残り38都道府県は均等弱め |
| join_date | date_range | 2010-01-01〜2025-12-31 から一様サンプル |
| leave_date | derived_column | 15%の確率で `join_date + uniform(365, 3650)日`、上限 2025-12-31。それ以外 null |
| member_rank | weighted_category | BRONZE:SILVER:GOLD:PLATINUM = 45:30:18:7 |
| annual_spend | correlated_numeric | rank別ベース額 × age係数 × log-normal ノイズ、PLATINUMは下限500_000で reject sampling |
| has_spouse | rule_based | 年齢別ベース確率（<18=0%, 18-29=25%, 30-39=55%, 40-59=72%, 60+=78%）→ Bernoulli |
| email_optin | weighted_category | 0:1 = 30:70 |
| registration_channel | weighted_category | WEB:STORE:APP:PHONE = 40:25:25:10 |

## 列間相関

1. **rank × annual_spend** — rank に応じてベース額を変える
   - BRONZE: 中央値 5万、対数正規 sigma=0.7
   - SILVER: 中央値 20万、sigma=0.5
   - GOLD: 中央値 45万、sigma=0.4
   - PLATINUM: 中央値 80万、sigma=0.35（下限 50万）

2. **age × annual_spend** — `age` に依存する係数（25〜60歳が 1.0、若年/高齢は 0.7〜0.85）を ベース額に乗じる

3. **age × has_spouse** — 上記 rule_based の年齢階層

4. **join_date × leave_date** — leave_date は join_date 以降に派生

## post sampling

- C2: 派生計算で違反は出ない想定だが、安全のため最後に `leave_date >= join_date` を再確認し違反は除外
- C3: `age < 18 & has_spouse=1` を `has_spouse=0` に強制上書き（除外でなく修正）
- C4: PLATINUM の生成内で `< 500000` を再サンプリング

最終件数が指定行数に足りない場合、不足分を再生成して結合する。

## 再現性

- seed は `numpy.random.default_rng(seed)` で固定。
- 全列を同一 RNG で順に生成。

## 注意

- サンプルデータの行をそのまま含めない。
- 個人氏名・住所などの直接的識別子は生成しない。
- 出力は合成データであり、匿名加工情報ではない。
