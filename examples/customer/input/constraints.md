# 制約条件

## 必須制約（仕様違反は許容しない）

1. **C1: member_id 一意性** — `member_id` は全行で一意。
2. **C2: 退会日順序** — `leave_date` が非null の場合、`leave_date >= join_date`。
3. **C3: 未成年に配偶者なし** — `age < 18` の行は `has_spouse = 0`。
4. **C4: PLATINUMの最低購入額** — `member_rank = 'PLATINUM'` の行は `annual_spend >= 500000`。
5. **C5: 値域** — `age` は 0〜110、`annual_spend` は 0〜3,000,000。
6. **C6: コード値** — `gender`, `member_rank`, `registration_channel`, `prefecture_code` は許容値のみ。

## 推奨制約（評価で確認する）

7. **C7: gender構成比** — 男性:女性:不明 ≒ 45:50:5（±5pt 程度）。
8. **C8: 年代別 has_spouse 比率** — 20代未満は10%以下、30代は40〜70%、40代以上は60〜85%。
9. **C9: rankとannual_spendの関係** — 平均値が BRONZE < SILVER < GOLD < PLATINUM の順。
