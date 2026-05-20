# constraint_plan.md

constraints.md および data_spec.md から抽出した制約を、生成方式別に分類する。

## generation_constraint（生成時に直接反映）

| ID | 制約 | 反映方法 |
|----|------|----------|
| C1 | member_id 一意性 | sequential_id で `M` + 連番付与 |
| C5 | age ∈ [0,110] / annual_spend ∈ [0,3_000_000] | 分布生成時に clip |
| C6 | gender/member_rank/registration_channel/prefecture_code は許容値のみ | weighted_category で許容値リストからのみサンプリング |

## post_sampling_constraint（生成後にフィルタリングする）

| ID | 制約 | 検出方法 |
|----|------|----------|
| C2 | leave_date が非null の場合、leave_date >= join_date | 行単位で日付比較し違反行を除外 |
| C3 | age < 18 の場合、has_spouse = 0 | 違反行は has_spouse を 0 に上書き（仕様修正）。除外ではない。 |
| C4 | member_rank = 'PLATINUM' の場合、annual_spend >= 500000 | 違反行を除外（または生成時に範囲調整） |

> 実装メモ：C3 は値域違反ではなくクロス制約。生成後に強制上書きしても情報量はほぼ失われないため、削除でなく上書きにする。除外件数=0 になることを期待する。

## validation_only_constraint（評価のみ）

| ID | 制約 | 評価方法 |
|----|------|----------|
| C7 | gender構成比 ≒ 45:50:5 | 評価レポートで頻度比較 |
| C8 | 年代別 has_spouse 比率 | 評価レポートで年代×平均値テーブルを比較 |
| C9 | rank × annual_spend の平均順序 | 評価レポートで mean(annual_spend) by rank を比較 |

## oversampling倍率の設計

post_sampling で除外されるのは C2/C4 のみ。
- C2: leave_date 非null が 15% → そのうち順序違反の発生確率は生成方式で抑制すれば 0% に近い（leave_date を `join_date + ランダム日数` で生成する）
- C4: PLATINUM の生成時に annual_spend のロジック内で下限 500000 を保証すれば除外不要

→ 実質的に除外はほぼ発生しないが、安全のため **oversampling = 1.05倍** で生成する。

## 不明・仮定

- `prefecture_code` の上位以外（残り 38 都道府県）の比率はサンプルから推定できないため、上位 9 都道府県以外は人口比に近い均等弱め分布で生成する仮定を置く。
- `leave_date` を持つ会員の `leave_date` は `join_date + 1〜10年` の範囲から一様にサンプル。仕様に明記がないための保守的な仮定。
