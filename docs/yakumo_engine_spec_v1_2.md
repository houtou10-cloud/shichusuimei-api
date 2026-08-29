# 八雲式 四柱推命鑑定エンジン v1.2 完成版仕様書

-   文書ID: `yakumo_engine_spec_v1_2`
-   対象バージョン: Yakumo Engine v1.2
-   基準仕様: `yakumo_engine_spec_v1_1`
-   ステータス: Development Specification / v1.2 Release Target
-   作成日: 2026-08-22
-   目的: v1.1 を壊さず、精度・透明性・説明可能性・回帰安全性を高める

> **最重要原則**
>
> v1.2 は「新機能を大量に足す版」ではない。 v1.1
> で完成した一連の鑑定パイプラインを基礎として、
> **なぜその判定になったかを追跡できるエンジン**へ進化させる。
>
> 決定論的計算はエンジンが行う。 AI
> は計算結果を再計算・改変せず、人間が理解できる文章へ翻訳する。
> 最終判断は人間が行う。

------------------------------------------------------------------------

## 1. v1.2 のゴール

v1.2 の完成条件を次の5点とする。

1.  **計算精度**
    -   暦・四柱・蔵干・通変星・十二運・五行・月令・通根・身強身弱・干支関係・格局・用神・大運・歳運・現在運を一貫して算出できる。
2.  **説明可能性**
    -   身強身弱、格局、用神、運勢等の主要判定について、結論だけでなく
        `evidence` を返す。
3.  **バージョン追跡**
    -   API・エンジン・ルール・schema のバージョンを出力から追跡できる。
4.  **AI整合性**
    -   AI鑑定文を「事実 → 解釈 →
        助言」の順で生成し、エンジン確定値との矛盾を Quality Gate
        で検査する。
5.  **回帰安全性**
    -   v1.1 の代表命式・PDFを Golden Artifact
        として固定し、意図しない結果変更を検出する。

------------------------------------------------------------------------

## 2. v1.2 の対象範囲

### 2.1 v1.1 から継承する機能

-   四柱算出
-   蔵干
-   通変星
-   十二運
-   加重五行
-   月令・季節評価
-   通根
-   身強身弱
-   干支関係
-   格局
-   用神
-   大運
-   歳運
-   現在運・統合運
-   出生時刻不明の三柱モード
-   `reading_context`
-   AI鑑定
-   Quality Gate
-   Auto-Repair
-   ReadingProduct
-   PDF鑑定書

### 2.2 v1.2 の中心改良

-   暦・節入り境界の精密化
-   全主要判定の evidence 共通化
-   身強身弱の根拠構造化
-   干支関係強度の構造化
-   格局候補・成立判定の説明可能化
-   用神候補の理論別分離と統合
-   大運・歳運・現在運の evidence 強化
-   `reading_context` schema v2
-   AI鑑定の「事実・解釈・助言」分離
-   Quality Gate V2
-   PDF V2
-   バージョン・warning・uncertainty 管理
-   Golden / Contract / E2E テスト強化

### 2.3 v1.2 の対象外

以下は v1.2 本体の必須完成条件には含めない。

-   顧客CRM
-   会員課金
-   アカデミー受講管理
-   アカデミーとの双方向連動
-   真太陽時補正の全面導入（正式ルール確定までは別機能）
-   海外出生の無条件対応
-   AIによる占術ルール自動変更

これらは v1.3 / Pro / SaaS レイヤー候補とする。

------------------------------------------------------------------------

## 3. 全体アーキテクチャ

``` text
Input
  ↓
Calendar / Solar Terms
  ↓
Four Pillars
  ↓
Hidden Stems
  ↓
Ten Gods
  ↓
Twelve Stages
  ↓
Five Elements
  ↓
Month Command / Seasonal Strength
  ↓
Root Strength
  ↓
Final Day-Master Strength
  ↓
Stem / Branch Relations
  ↓
Pattern Candidates
  ↓
Pattern Judgment
  ↓
Useful Gods
  ↓
Luck Pillars
  ↓
Current Luck / Annual Luck / Integrated Luck
  ↓
Reading Context v2
  ↓
AI Reading
  ↓
Quality Gate v2
  ↓
Auto-Repair
  ↓
ReadingProduct v2
  ↓
PDF v2
```

### 3.1 責務分離

**Engine** - 命式計算 - 占術ルール判定 - evidence 構造化 - warnings /
uncertainty 出力

**AI** - エンジン結果を文章へ翻訳 - 複数根拠を人間向けに整理 -
助言を自然言語化

**Human** - 相談内容と現実を重ねる - 境界例・例外を確認する -
最終判断を行う

------------------------------------------------------------------------

## 4. 共通 Judgment Schema

v1.2 の主要判定は、可能な限り次の共通形式へ寄せる。

``` json
{
  "value": "...",
  "technical_value": "...",
  "score": 0.0,
  "confidence": {
    "level": "high|medium|low",
    "ratio": 0.0
  },
  "method": "rule_name_vN",
  "version": "N",
  "status": "resolved|provisional|uncertain|unsupported",
  "evidence": [],
  "supporting_factors": [],
  "opposing_factors": [],
  "warnings": [],
  "uncertainty": []
}
```

### 4.1 必須思想

-   `value` と `evidence` を分離する。
-   `status=provisional` を隠さない。
-   境界値では `uncertainty` を返せる。
-   AIに渡す前に、エンジン側で判定根拠を構造化する。
-   method 名だけでなく rule version を追跡可能にする。

------------------------------------------------------------------------

## 5. 入力仕様

### 5.1 基本入力

``` text
name
birth_date
birth_time
birth_place
gender
consultation_text
target_datetime
```

### 5.2 出生時刻

-   既知: 四柱モード
-   不明: 三柱モード
-   不明時に時柱を推測して確定値として扱わない。
-   時柱依存判定は `warnings` / `uncertainty` に伝播する。

### 5.3 出生地

v1.2 では出生地情報を保持する。

ただし、出生地補正・真太陽時補正は、正式ルールとテストが確定するまで「入力を持つこと」と「計算に補正を適用すること」を分離する。

------------------------------------------------------------------------

## 6. 暦・節入り仕様 V2

### 6.1 年柱

-   立春基準を維持する。
-   立春境界の直前・直後を Boundary Test で固定する。

### 6.2 月柱

-   節入り基準を維持する。
-   固定日近似ではなく、採用する節入り計算方式を明示する。

### 6.3 日柱

-   v1.1 の日境界仕様を Golden Test で固定したうえで変更する。
-   変更が必要な場合は breaking rule change として記録する。

### 6.4 時柱

-   時刻区分を完全マトリクス化する。
-   子刻境界を重点テストする。

### 6.5 必須出力

``` json
{
  "calendar_method": "...",
  "solar_term_method": "...",
  "boundary_warning": false,
  "warnings": []
}
```

------------------------------------------------------------------------

## 7. 蔵干仕様 V2

地支ごとに以下を保持する。

-   本気
-   中気
-   余気
-   各蔵干の五行
-   通変星
-   weight
-   五行集計への寄与
-   通根への寄与

v1.2
では蔵干重みを定数表として一元管理し、同じ値を複数モジュールへ重複定義しない。

------------------------------------------------------------------------

## 8. 通変星仕様

日主10干 × 対象10干 = **100組を完全テスト**する。

出力:

``` json
{
  "stem": "辛",
  "ten_god": "正官",
  "method": "ten_gods_v1",
  "status": "resolved"
}
```

AIは通変星を再計算しない。

------------------------------------------------------------------------

## 9. 十二運仕様

日主10干 × 地支12支の全組合せを Rule Matrix Test 対象とする。

対象:

長生 / 沐浴 / 冠帯 / 建禄 / 帝旺 / 衰 / 病 / 死 / 墓 / 絶 / 胎 / 養

原命式、大運、歳運で同じ基礎ルールを再利用する。

------------------------------------------------------------------------

## 10. 五行評価 V2

### 10.1 出力

``` json
{
  "raw_scores": {},
  "weighted_scores": {},
  "strongest_element": "...",
  "weakest_element": "...",
  "method": "weighted_five_elements_v2",
  "status": "...",
  "evidence": []
}
```

### 10.2 evidence に含めるもの

-   天干寄与
-   地支寄与
-   蔵干寄与
-   月令・季節寄与
-   採用した補正
-   丸め前値
-   丸め後値

### 10.3 禁止

-   月令の同一効果を複数レイヤーで二重加算しない。
-   「不足五行 = 用神」と短絡しない。

------------------------------------------------------------------------

## 11. 月令・季節評価 V2

旺・相・休・囚・死等の季節状態を構造化する。

``` json
{
  "seasonal_state": "...",
  "seasonal_score": 0.0,
  "month_branch": "...",
  "evidence": [],
  "method": "seasonal_strength_v2"
}
```

身強身弱へ渡す値と、五行表示用の値を混同しない。

------------------------------------------------------------------------

## 12. 通根 V2

### 12.1 判定要素

-   根として認める条件
-   月支か否か
-   本気・中気・余気
-   地支位置
-   複数根
-   合・冲・刑・害等による影響
-   上限

### 12.2 出力

``` json
{
  "has_root": true,
  "roots": [],
  "total_root_score": 0.0,
  "weighted_root_bonus": 0.0,
  "evidence": [],
  "method": "root_strength_v2"
}
```

------------------------------------------------------------------------

## 13. 身強身弱 V2

現行系統の `final_strength_judgment_v2` を v1.2
の中心判定として扱い、provisional を解消できる状態を目標とする。

### 13.1 入力要素

-   生助
-   剋洩耗
-   月令
-   通根
-   季節補正
-   五行バランス
-   必要に応じて干支関係による補正

### 13.2 出力

``` json
{
  "technical_label": "balanced",
  "label": "中和",
  "final_score": 50.0,
  "confidence": {
    "level": "medium",
    "ratio": 0.75
  },
  "adjustments": [],
  "evidence": [],
  "method": "final_strength_judgment_v2",
  "status": "resolved"
}
```

### 13.3 完成条件

-   ラベル境界値を定数化
-   中和域を固定
-   上限・下限を固定
-   全境界の ±ε テスト
-   極端命式テスト
-   三柱モードの confidence 低下ルール
-   v1.1 差分の説明

#### 極端命式 fixture 承認 policy

-   `extreme chart` は、`calculation_scope == "four_pillars"` かつ `final_strength_judgment.technical_label` が `very_strong` または `very_weak` となる実命式とする。
-   分類には既存境界のみを使用し、`very_strong` は `final_score >= 70.0`、`very_weak` は `final_score < 30.0` とする。新しい閾値は追加しない。
-   「極端命式テスト」の完成には、承認済み strong-side fixture 1件以上と承認済み weak-side fixture 1件以上の両方を必要とし、片側だけでは完成扱いにしない。
-   0/100 clamp test は数値安全性の unit test、extreme chart test は承認済み four-pillar 実命式の regression test として分離する。`final_score == 0` または `final_score == 100` は extreme chart の必須条件としない。

extreme chart fixture の正式採用には、次の3条件をすべて必要とする。これらは fixture 承認プロセス上の概念であり、production API の status または schema には追加しない。

1.  `calendar_verified`: birth data と四柱が、Yakumo Engine とは独立した暦資料で確認済みである。
2.  `strength_verified`: Yakumo Engine v1.2 の採用済みルールによる upstream components、raw score、final score、technical label、label が、現行 Yakumo Engine とは独立した経路で確認済みである。
3.  `golden_regression`: `calendar_verified` および `strength_verified` で承認された期待値を Golden として保存し、regression test で固定済みである。

expected final score は、四柱推命上の普遍的な唯一解ではなく、Yakumo Engine v1.2 の採用済みルールに対する独立検証済み期待値として扱う。

現行 Yakumo Engine へ候補を入力し、extreme label が出たことを根拠に、その出力を expected 値として保存し、同じエンジンの regression test が通ることで正しいと判断する手順は、strength verification として認めない。Golden regression は再現性と変更検出を保証するが、独立した strength verification を保証しない。

承認記録には最低限、fixture ID、birth data、location、timezone、gender、four pillars、calculation scope、calendar verification source、calendar reviewer/date、strength verification method、strength reviewer/date、expected raw score、expected final score、expected technical label、expected label、method/version、known uncertainty を保持する。既存 metadata で表現できる項目は既存形式を再利用し、production API schema には追加しない。

extreme chart の判定および承認は、confidence、status、uncertainty、three-pillar confidence policy、`season_transition_adjustment_not_applied` から独立させる。極端命式テストが完成しても、それだけを理由に `final_strength_judgment.status` を `provisional` から `resolved` へ変更しない。

現在の実装・承認状態は次のとおりとする。

-   strong-side: GC03（fixture ID: `1984_fukuoka_male_afternoon_v2`）は、`calculation_scope == "four_pillars"`、`final_score == 71.5`、`technical_label == "very_strong"`、`label == "極身強"` の承認済み fixture である。`calendar_verified`、`strength_verified`、`golden_regression` はすべて confirmed であり、承認済み strong-side regression test は実装済みかつ passing とする。strength approval record は `tests/verification/extreme_fixtures/GC03_1984_fukuoka_male_afternoon_strength_v1.json`（commit `4f9ed1712a582796a0dc4dc1c42a3cdde66725f4`）、regression test は commit `fe5c49497d30e89efb062dbf85d292cbb7585322` で固定する。この承認は Yakumo Engine v1.2 compatibility rules に対する独立検証・承認であり、普遍的な四柱推命上の真理を証明するものではない。
-   weak-side: 承認済み fixture は未発見・未承認であり、calendar verification、strength verification、approval record および regression test は未完了とする。
-   overall: strong-side は approved / regression-fixed、weak-side は pending であるため、「極端命式テスト」の完成条件は未達であり、13.3 全体も complete としない。新しい命式の作成・探索および新しい status/schema 語彙の追加は行わない。

#### 三柱モードの confidence policy

-   出生時刻が既知の `four_pillars` では、既存の confidence 算出結果を変更しない。
-   出生時刻不明の `three_pillars` では、`final_strength_judgment` の confidence 上限を `medium` とする。
-   変換は `high -> medium`、`medium -> medium`、`low -> low` とする。
-   このルールは四柱推命理論上の追加ルールではなく、出生時刻不明という input uncertainty に対する confidence policy とする。
-   `three_pillars` によって confidence が実際に低下した場合だけ、次の structured uncertainty を重複なく追加する。

``` json
{
  "code": "birth_time_unknown_strength_confidence_reduced",
  "category": "input_uncertainty",
  "status": "uncertain",
  "severity": "warning",
  "scope": ["strength"],
  "message": "出生時間が不明なため、身強身弱判定のconfidence上限をmediumとして扱います。"
}
```

#### v1.1との差分

v1.1 tag（`c743f464ffa7afa2c1061a61f0d5479959a66f8f`）の時点で、`weighted_provisional_strength_v3` の `final_score` を base score とする `final_strength_judgment_v2` は既に production に存在していた。v1.2 は新しい身強身弱理論へ置き換えるものではなく、次の既存 production behavior を維持する。

-   weighted five elements を supporting / draining に分類し、weighted roots、seasonal strength および weighted month integration を含む `weighted_provisional_strength_v3` の `final_score` を base score とする。
-   root と month は base score に含まれているため、final layer では再加算しない。
-   branch relation の `total_score` は日主強弱への方向を直接示す値として扱わず、方向が明示された adjustment だけを final score に適用する。
-   transformation adjustment は既存の限定補正として扱い、adjustment total、raw final score、rounding、0–100 clamp および final label classification の計算順序を維持する。

13.4 に定める weighted five elements、supporting / draining、weighted roots、seasonal strength、weighted month integration、branch adjustment、transformation adjustment、double-count prevention、rounding、clamp および final label thresholds の rule、table、weight、formula は、原則として v1.1 production behavior を変更せず、Yakumo Engine v1.2 の versioned compatibility rules として正式化したものである。

v1.1 仕様書は root を「日主と同一または支持関係」と概括的に記載していたが、v1.1 production 実装の weighted root eligibility は、day master と同一 element の hidden stem だけを採用していた。v1.2 はこの root behavior を変更せず、実装済みの限定された互換条件を 13.4 に明文化する。

final label thresholds は v1.1 から変更しない。

-   `very_strong`: `final_score >= 70.0`
-   `strong`: `58.0 <= final_score < 70.0`
-   `balanced`: `43.0 <= final_score < 58.0`
-   `weak`: `30.0 <= final_score < 43.0`
-   `very_weak`: `final_score < 30.0`

neutral / balanced zone は `43.0 <= final_score < 58.0` とする。

v1.2 で実際に追加または変更した strength behavior および metadata は次のとおりとする。

-   出生時刻不明の three-pillar mode では、final strength confidence の上限を `medium` とする。出生時刻が既知の four-pillar mode では、v1.1 からの既存 confidence 算出結果を変更しない。
-   適用していない季節細分補正、および three-pillar policy によって confidence が実際に低下した場合の input uncertainty を structured uncertainty として返す。
-   status を `provisional_final_strength_judgment_v2` から共通語彙 `provisional` へ正規化する。判定は引き続き provisional であり、本差分の明文化だけを理由に `resolved` へ変更しない。

v1.2 では、全 final label 境界の `-epsilon / boundary / +epsilon` test と approved extreme fixture regression を追加する。これらは score calculation、weight または threshold の変更ではなく、境界挙動および承認済み実命式からの逸脱を検出する test coverage improvement である。

v1.1 Golden baseline は参照値として維持し、Golden のみを fixture の承認根拠とする circular validation は行わない。v1.2 で意図的に変更した status、confidence および structured uncertainty 等の metadata difference と、既存 score / label の compatibility は分離して扱う。

### 13.4 Strength Calculation Rules

#### 13.4.1 Scope and compatibility policy

-   本節は、`final_strength_judgment_v2` へ至る身強身弱計算を再現するための Yakumo Engine v1.2 compatibility rules を定義する。
-   本節の rule、table、weight、formula は、現行 production behavior の再現性、独立検証可能性および後方互換性のために versioned rule として固定するものであり、普遍的な四柱推命理論上の唯一解を主張しない。
-   本節は production code、API schema、score、label、confidence、status、uncertainty および three-pillar confidence policy を変更しない。
-   本節の strength calculation rules は、confidence、status、uncertainty、three-pillar confidence policy および `season_transition_adjustment_not_applied` から独立させる。
-   将来、本節の値または計算式を変更する場合は v1.2 の silent change とせず、別 version または明示的な rule change として記録する。

#### 13.4.2 Supporting and draining classification

日主の五行を基準に、weighted element score を次の2群へ分類する。

-   supporting: 日主と同じ五行、および日主を生じる五行
-   draining: 日主が生じる五行、日主が剋す五行、および日主を剋す五行

``` text
supporting_score = supporting五行のweighted score合計
draining_score = draining五行のweighted score合計
total = supporting_score + draining_score
supporting_ratio = supporting_score / total * 100
draining_ratio = draining_score / total * 100
```

`total == 0` の場合、`supporting_ratio` と `draining_ratio` は `0.0` とする。

#### 13.4.3 Weighted element contribution

-   各天干の寄与を `1.0` とする。
-   各地支は、蔵干全体の weight 合計を `1.0` として寄与させる。
-   蔵干は既存データの並び順を主気・中気・余気の順として扱い、蔵干数に応じて次の weight を使用する。

  蔵干数   weights
  -------- -----------------
  1        `1.0`
  2        `0.7 / 0.3`
  3        `0.6 / 0.3 / 0.1`

各天干および各蔵干の五行へ寄与値を加算し、五行ごとの weighted score を求める。

#### 13.4.4 Weighted roots

-   地支蔵干のうち、日主と同一五行の蔵干だけを weighted root として採用する。
-   v1.1 文書には root を「日主と同一または支持関係」とする概括的説明があるが、v1.2 compatibility rule では現行 production behavior との互換性を優先し、日主と同一五行の蔵干だけを採用する。
-   `weighted_root_strength_v1` では次の position weight を使用する。

  position   weight
  ---------- ------
  year       `0.8`
  month      `1.5`
  day        `1.3`
  hour       `1.0`

``` text
root_score = position_weight * hidden_stem_weight
total_root_score = 各root_scoreの合計
weighted_root_bonus = total_root_score * 10
```

この position weight は `weighted_root_strength_v1` 専用であり、`transformation_root` または `transformation_exposure` に存在する同名の `POSITION_WEIGHTS` へ適用せず、それらと統合しない。

#### 13.4.5 Seasonal strength

月支と日主五行から、次の table で旺・相・休・囚・死を決定する。

  month branch    旺   相   休   囚   死
  --------------- ---- ---- ---- ---- ----
  寅・卯           木   火   水   金   土
  辰・未・戌・丑   土   金   火   木   水
  巳・午           火   土   木   水   金
  申・酉           金   水   土   火   木
  亥・子           水   木   金   土   火

seasonal score は次の値とする。

  state   score
  ------- -------
  旺      `12.0`
  相      `8.0`
  休      `2.0`
  囚      `-6.0`
  死      `-10.0`

#### 13.4.6 Weighted month integration

月支蔵干を 13.4.2 と同じ supporting / draining 分類で集計する。

``` text
month_total = month_supporting_score + month_draining_score
month_supporting_ratio = month_supporting_score / month_total * 100
month_draining_ratio = month_draining_score / month_total * 100
```

`month_total == 0` の場合、両 ratio は `0.0` とする。

``` text
hidden_stem_balance =
    (month_supporting_ratio - month_draining_ratio) / 100
hidden_stem_adjustment = hidden_stem_balance * 4
integrated_month_score = seasonal_score + hidden_stem_adjustment
```

ratio の定義により、`hidden_stem_adjustment` の範囲は `-4.0` から `4.0` となる。production ではこの値に別の明示 clamp を適用しない。

#### 13.4.7 Weighted base score

``` text
weighted_base_score =
    supporting_ratio
    + weighted_root_bonus
    + integrated_month_score
```

`weighted_strength_judgment.final_score` は、上式を `0.0` から `100.0` へ clamp した weighted base score とする。

この layer は既存の `weighted_provisional_strength_v3` による base score 生成経路を固定するものである。旧 provisional strength layer の表示 label と、`final_strength_judgment_v2` の final label を混同しない。final V2 の分類には13.3で固定した final thresholdだけを使用する。

#### 13.4.8 Final adjustments

`final_strength_judgment_v2` は、clamp済みの `weighted_strength_judgment.final_score` を base score として使用する。

地支関係については、日主強弱への方向が明示された補正だけを使用し、地支関係全体の強度を示す `total_score` は自動加算しない。directional adjustment は次の優先順で最初に見つかった数値を使用する。

1.  `strength_adjustment`
2.  `day_master_adjustment`
3.  `adjustment`

directional adjustment は `-6.0` から `6.0` へ clamp する。対象となる数値がない場合は `0.0` とする。

干合化候補の base adjustment は次の値とする。

  judgment             adjustment
  -------------------- ----------
  `strong_candidate`   `3.0`
  `possible`           `1.5`
  `weak`               `0.5`
  `unsupported`        `0.0`
  未知の値             `0.0`

conflict severity multiplier は次の値とする。

  severity   multiplier
  ---------- ----------
  `none`     `1.00`
  `low`      `0.80`
  `medium`   `0.50`
  `high`     `0.25`

``` text
candidate_adjustment = base_adjustment * conflict_multiplier
transformation_adjustment = 全candidate_adjustmentの合計
```

production は `transformation_adjustment` を `-5.0` から `5.0` へ clamp する。現行の base adjustment はすべて非負であるため、通常の実効範囲は `0.0` から `5.0` となる。

``` text
adjustment_total = branch_adjustment + transformation_adjustment
raw_final_score = final_v2_base_score + adjustment_total
final_score = clamp(raw_final_score, 0.0, 100.0)
```

#### 13.4.9 Double-count prevention

-   `weighted_base_score` には supporting ratio、weighted root bonus および integrated month score が含まれる。
-   final V2 では通根と月令を再加算せず、`root_adjustment = 0.0`、`month_adjustment = 0.0` とする。
-   final V2 で追加できるのは、13.4.8の明示的な branch adjustment と限定的な transformation adjustmentだけとする。

#### 13.4.10 Rounding and clamp

本節では、言語非依存の `round2` を次のように定義する。

``` text
round2(x):
    xを最も近い0.01単位の値へ丸める。
    隣接する2つの0.01単位値から正確に等距離の場合は、
    小数第2位を整数として見た値が偶数となる側を選ぶ。
```

production と同じ境界結果を再現する場合、計算値は IEEE 754 binary64 として扱ったうえで `round2` を適用する。各計算 layer では次の順序で丸める。

1.  Weighted five elements
    -   各五行の全柱合計を `round2` する。
    -   丸め済み五行値の合計を `round2` する。
    -   各 percentage を `round2` する。
2.  Weighted supporting / draining
    -   supporting score と draining score をそれぞれ `round2` する。
    -   両者の合計を `round2` する。
    -   supporting ratio と draining ratio をそれぞれ `round2` する。
3.  Weighted month command
    -   month supporting score と month draining score をそれぞれ `round2` する。
    -   両者の合計を `round2` する。
    -   month supporting ratio と month draining ratio をそれぞれ `round2` する。
4.  Weighted roots
    -   各 `position_weight * hidden_stem_weight` を `round2` する。
    -   丸め済み root score の合計を `round2` する。
5.  Integrated month
    -   `hidden_stem_balance` を `round2` する。
    -   `hidden_stem_balance * 4` を `round2` する。
    -   `seasonal_score + hidden_stem_adjustment` を `round2` する。
6.  Weighted base
    -   `total_root_score * 10` を `round2` する。
    -   supporting ratio、丸め済み weighted root bonus、丸め済み integrated month score を加算する。
    -   `0.0` から `100.0` へ clamp した後に `round2` する。
7.  Branch adjustment
    -   directional adjustment を `-6.0` から `6.0` へ clamp した後に `round2` する。
8.  Transformation adjustment
    -   各 base adjustment と multiplier の積を加算する。
    -   合計を `-5.0` から `5.0` へ clamp した後に `round2` する。
9.  Final V2
    -   入力 base score を `0.0` から `100.0` へ clamp した後に `round2` する。
    -   branch adjustment と transformation adjustment の合計を `round2` し、`adjustment_total` とする。
    -   base score と `adjustment_total` の合計を `round2` し、`raw_final_score` とする。
    -   `raw_final_score` を `0.0` から `100.0` へ clamp した後に `round2` し、`final_score` とする。
    -   final labelの分類前にも同じ clamp と `round2` を適用する。

#### 13.4.11 Final labels

final label は、13.3で固定した既存の final threshold と technical label / label mapping を使用する。本節では別の threshold または mapping を定義しない。旧 provisional strength layer の threshold および表示 label は final V2 の分類に使用しない。

#### 13.4.12 Limitations

-   hidden-stem weight には流派差があるが、v1.2では compatibility rule として13.4.3の値を固定する。
-   土用期間による補正は未反映とする。
-   節入り後日数による補正は未反映とする。
-   branch relationの総合scoreは日主への扶助・剋洩耗方向を直接表さず、directional adjustmentが明示されない場合は final scoreへ加算しない。
-   transformation judgment は provisional な判定を含む。
-   root eligibility および `weighted_root_strength_v1` の position weight は、普遍的理論ではなく v1.2 compatibility rule とする。
-   本節のlimitationsは、confidence、status、uncertainty または three-pillar confidence policy を変更する根拠としない。
-   本節のruleを将来変更する場合は silent change とせず、別 version または明示的な rule changeとして管理する。

------------------------------------------------------------------------

## 14. 干支関係 V2

対象:

-   天干五合
-   六合
-   三合
-   方合
-   冲
-   刑
-   害
-   破

### 14.1 Relation Object

``` json
{
  "type": "clash",
  "members": ["子", "午"],
  "pillars": ["year", "day"],
  "established": true,
  "strength": 0.0,
  "conditions": [],
  "effects": {
    "strength": [],
    "pattern": [],
    "useful_gods": [],
    "luck": []
  },
  "evidence": [],
  "warnings": []
}
```

「関係がある」ことと「命式全体へ強く作用する」ことを分離する。

------------------------------------------------------------------------

## 15. 格局 V2

候補生成と成立判定を分離する。

-   Candidate Layer: `pattern_candidates_v1` 系
-   Judgment Layer: `pattern_judgment_v2` 系

### 15.1 原則

-   月令・月支を重視
-   月支蔵干を参照
-   透干を重要視
-   複数候補を保持
-   成格条件と破格条件を分離
-   救済条件を保持

### 15.2 Candidate Schema

``` json
{
  "pattern": "食神格",
  "technical_pattern": "eating_god",
  "score": 70.0,
  "is_exposed": true,
  "supporting_conditions": [],
  "breaking_conditions": [],
  "rescue_factors": [],
  "confidence": "medium",
  "evidence": []
}
```

### 15.3 Final Judgment

``` json
{
  "primary_pattern": "食神格",
  "candidates": [],
  "overall_judgment": "...",
  "establishment_status": "established",
  "method": "pattern_judgment_v2",
  "status": "resolved"
}
```

特殊格局・例外命式は、未検証の場合に無理に resolved にしない。

------------------------------------------------------------------------

## 16. 用神 V3

現行系統の `useful_gods_v3` を基礎とする。

### 16.1 用神を決める材料

-   身強身弱
-   扶抑
-   調候
-   格局
-   五行バランス
-   干支関係
-   必要に応じて候補間の一致度

### 16.2 理論別候補を保持

``` json
{
  "support_balance_candidates": [],
  "climate_candidates": [],
  "pattern_candidates": [],
  "final_candidates": [],
  "primary_useful_element": "...",
  "secondary_useful_elements": [],
  "unfavorable_elements": [],
  "agreement_level": "...",
  "conflicted_elements": [],
  "reasoning": [],
  "method": "useful_gods_v3",
  "status": "resolved"
}
```

### 16.3 原則

-   五行不足だけで決めない。
-   主用神だけを返して途中根拠を捨てない。
-   理論間で衝突した場合は `conflicted_elements` と理由を保持する。
-   AIに用神を再決定させない。

------------------------------------------------------------------------

## 17. 大運 V2

現行 `luck_pillars_v2` 系を基礎とする。

必須:

-   順行・逆行
-   開始年齢
-   開始年齢算出根拠
-   10年単位の大運列
-   干支
-   通変星
-   十二運
-   用神との関係
-   原命式との干支関係
-   現在大運

開始年齢は結果だけでなく計算根拠を保持する。

------------------------------------------------------------------------

## 18. 歳運・現在運・統合運 V2

基礎となる現行 method:

-   `current_luck_v1`
-   `annual_luck_v1`
-   `integrated_luck_v1`

### 18.1 三層評価

``` text
原命式
  ×
現在大運
  ×
対象歳運
```

### 18.2 年別 evidence

各年について最低限、

-   歳運干支
-   通変星
-   十二運
-   用神・忌神との関係
-   原命式との関係
-   大運との関係
-   supporting factors
-   caution factors
-   confidence

を保持する。

「良い年／悪い年」だけの単純ラベルへ縮約しない。

------------------------------------------------------------------------

## 19. 三柱モード V2

出生時刻不明時:

-   時柱を生成しない。
-   時柱依存ロジックを明示的に skip / uncertain とする。
-   `birth_time_unknown=true`
-   `uncertainty` を reading_context まで伝播する。
-   AI文章でも出生時刻不明を明示する。
-   四柱モードと同一 confidence を返さない。

------------------------------------------------------------------------

## 20. Reading Context Schema v2

### 20.1 目的

AIへ「生データ」ではなく「鑑定可能な構造」を渡す。

### 20.2 推奨トップレベル

``` json
{
  "schema_version": "reading_context_v2",
  "engine_version": "1.2",
  "subject": {},
  "chart": {},
  "day_master": {},
  "five_elements": {},
  "month_command": {},
  "roots": {},
  "strength": {},
  "relations": {},
  "pattern": {},
  "useful_gods": {},
  "luck": {},
  "consultation": {},
  "facts": [],
  "interpretation_hints": [],
  "warnings": [],
  "uncertainty": [],
  "source_metadata": {}
}
```

### 20.3 source_metadata

主要判定ごとに、

``` json
{
  "method": "...",
  "version": "...",
  "status": "..."
}
```

を保持する。

### 20.4 禁止

-   AI用 prompt 内で命式を再計算させない。
-   schema にない値を AI が「確定値」として追加しない。
-   provisional を resolved のように見せない。

------------------------------------------------------------------------

## 21. Consultation Context

相談内容を占術計算と分離して保持する。

例:

``` json
{
  "topic": "career",
  "raw_text": "...",
  "questions": [],
  "time_horizon": null,
  "constraints": [],
  "safety_notes": []
}
```

相談内容は「計算ルールを変える入力」ではなく、「どの計算結果を重点的に説明するか」を決めるコンテキストとする。

------------------------------------------------------------------------

## 22. AI鑑定 V2

### 22.1 8セクション基本構成

-   `core_personality`
-   `career`
-   `wealth`
-   `relationships`
-   `health`
-   `current_luck`
-   `future_flow`
-   `advice`

### 22.2 各セクション

``` json
{
  "title": "...",
  "facts": [],
  "summary": "...",
  "detail": "...",
  "evidence": [],
  "interpretation": [],
  "advice": [],
  "uncertainty": []
}
```

### 22.3 文章生成原則

``` text
事実
↓
根拠
↓
解釈
↓
現実への翻訳
↓
助言
```

### 22.4 禁止事項

-   エンジン確定値の変更
-   AI独自の格局・用神再計算
-   一要素だけからの人物断定
-   将来の保証
-   医療・法律・投資等の断定
-   不安を煽る表現
-   「必ず」「絶対」等の根拠なき決定表現

------------------------------------------------------------------------

## 23. Quality Gate V2

### 23.1 検査対象

1.  JSON/schema
2.  必須セクション
3.  エンジン確定値との一致
4.  身強身弱表現
5.  格局表現
6.  用神表現
7.  大運・歳運表現
8.  出生時刻不明の反映
9.  過度な断定
10. 医療・法律・投資等の危険表現
11. evidence の存在
12. facts / interpretation / advice の混同
13. unsupported な情報の断定

### 23.2 Severity

``` text
ERROR   PDF生成停止
WARNING 記録・必要に応じAuto-Repair
INFO    記録のみ
```

### 23.3 占術整合 warning

v1.1 では warning が PDF 停止条件ではないケースがある。 v1.2
では、**占術上の事実整合性に関わる warning** を分類し、Auto-Repair
対象化できるようにする。

------------------------------------------------------------------------

## 24. Auto-Repair V2

### 原則

-   エンジン計算値を変更しない。
-   問題箇所だけを修正する。
-   修正理由を記録する。
-   修正後に Quality Gate を再実行する。
-   無限修正を防止する。
-   最大試行回数を設定する。

### Repair Log

``` json
{
  "attempt": 1,
  "issue_codes": [],
  "before_hash": "...",
  "after_hash": "...",
  "result": "repaired|failed"
}
```

------------------------------------------------------------------------

## 25. ReadingProduct V2

ReadingProduct は、

``` text
Engine Result
+
Reading Context
+
AI Reading
+
Quality Report
```

を PDF 商品へ渡す統合オブジェクトとする。

必須 metadata:

-   product version
-   engine version
-   reading context schema
-   AI generation method
-   quality status
-   generated_at
-   recalculates_astrology = false
-   rewrites_ai_reading の状態

------------------------------------------------------------------------

## 26. PDF鑑定書 V2

### 26.1 基本セクション

-   表紙
-   基本情報
-   命式
-   日主
-   五行
-   月令・通根
-   身強身弱
-   干支関係
-   格局
-   用神
-   本質・性格
-   仕事・適職
-   金運
-   恋愛・人間関係
-   健康傾向
-   現在大運
-   現在歳運
-   今後の流れ
-   長期大運
-   総合アドバイス
-   注意事項・免責

### 26.2 PDF原則

-   計算値とAI文章を混同しない。
-   engine / schema / product version を内部metadataへ保持する。
-   三柱モード等の warning を落とさない。
-   Golden PDF を回帰比較できる。
-   レイアウト変更と占術ルール変更を同一PRで大量に混ぜない。

------------------------------------------------------------------------

## 27. API V2

### 27.1 Metadata

``` json
{
  "api_version": "v2",
  "engine_version": "1.2",
  "schema_versions": {
    "reading_context": "v2",
    "reading_product": "v2"
  },
  "rule_versions": {},
  "warnings": [],
  "uncertainty": []
}
```

### 27.2 原則

-   API response だけで、どのルールで算出されたか追跡できる。
-   breaking change は API version を分離する。
-   v1.1 互換が必要な場合は adapter を設ける。
-   内部例外をそのまま個人情報付きで外部へ返さない。

------------------------------------------------------------------------

## 28. バージョン管理

管理対象:

-   API version
-   engine version
-   calendar rule
-   hidden stems rule
-   five elements rule
-   strength rule
-   relation rule
-   pattern rule
-   useful gods rule
-   luck rule
-   reading_context schema
-   prompt version
-   Quality Gate version
-   ReadingProduct version
-   PDF template version

結果差分が出るルール変更では、必ず Change ID を発行する。

------------------------------------------------------------------------

## 29. Warning / Uncertainty

### 29.1 Warning 例

-   節入り境界付近
-   出生時刻不明
-   出生地補正未適用
-   海外出生未対応
-   特殊格局未確定
-   用神理論間の衝突
-   confidence 低
-   AI出力修復済み

### 29.2 原則

「わからない」をエラーとして隠さない。

判定不能・低確信度・未対応は、明示的な状態として返す。

------------------------------------------------------------------------

## 30. テスト戦略

### 30.1 必須テスト層

1.  Unit Test
2.  Rule Matrix Test
3.  Boundary Test
4.  Golden Chart Test
5.  Integration Test
6.  AI Contract Test
7.  Quality Gate Test
8.  Auto-Repair Test
9.  PDF End-to-End Test
10. Security / Privacy Test

### 30.2 Golden Chart

代表命式について固定:

-   四柱
-   蔵干
-   通変星
-   十二運
-   五行
-   月令
-   通根
-   身強身弱
-   干支関係
-   格局
-   用神
-   大運
-   歳運
-   現在運

### 30.3 Golden Artifact

-   reading_context JSON
-   AI Contract fixture
-   ReadingProduct JSON
-   PDF

### 30.4 ルール変更時

``` text
Change ID
↓
仕様変更
↓
期待差分
↓
Unit/Boundary追加
↓
Golden差分確認
↓
AI Contract確認
↓
PDF E2E確認
↓
仕様書更新
```

------------------------------------------------------------------------

## 31. セキュリティ・個人情報

対象データ:

-   氏名
-   生年月日
-   出生時刻
-   出生地
-   性別
-   相談内容
-   鑑定結果
-   PDF

v1.2 エンジン単体では CRM を必須化しない。

将来の顧客保存機能では別途、

-   認証
-   認可
-   暗号化
-   保存期間
-   削除
-   アクセスログ
-   PDFアクセス制御

を正式仕様化する。

AI APIへ送信するデータは必要最小限とする。

------------------------------------------------------------------------

## 32. エラー処理

エラーを次の4群に分ける。

### A. Input Error

入力形式不正、存在しない日時等。

### B. Unsupported

海外出生等、正式対応していない条件。

### C. Calculation Error

内部計算失敗。

### D. Generation Error

AI / Quality Gate / PDF生成失敗。

「未対応」を推測計算で埋めない。

------------------------------------------------------------------------

## 33. ロギング

個人情報を過剰にログへ残さない。

記録すべきもの:

-   request id
-   engine version
-   rule versions
-   processing stage
-   warning codes
-   error codes
-   quality result
-   repair attempts
-   execution time

氏名・相談全文・API key 等は通常ログへ直接出さない。

------------------------------------------------------------------------

## 34. v1.2 開発優先順位

### Phase 0 --- Baseline Freeze

-   v1.1 tag / commit 固定
-   pytest結果保存
-   Golden Chart 固定
-   Golden PDF 固定
-   現行 method/status/version 抽出
-   定数・閾値一覧化

### Phase 1 --- P0 精度・基盤

-   engine / rule version 管理
-   暦・節入り境界
-   基礎 Rule Matrix
-   provisional 棚卸し
-   warning / uncertainty 共通仕様

### Phase 2 --- P1 鑑定ロジック

-   五行 evidence
-   通根 V2
-   身強身弱 V2
-   干支関係 V2
-   格局 V2
-   用神 V3 固定
-   大運・歳運 evidence

### Phase 3 --- P2 AI接続

-   reading_context v2
-   consultation_context
-   AI facts / interpretation / advice 分離
-   Quality Gate V2
-   Auto-Repair V2

### Phase 4 --- Product

-   ReadingProduct V2
-   PDF V2
-   API V2 metadata
-   E2E / Golden Artifact

### Phase 5 --- Release

-   全回帰テスト
-   v1.1差分レビュー
-   代表実命式レビュー
-   PDF目視確認
-   version固定
-   `v1.2.0` release tag

------------------------------------------------------------------------

## 35. v1.2 完成判定 Definition of Done

以下をすべて満たした時点で v1.2 完成とする。

-   [ ] v1.1 baseline が固定されている
-   [ ] 全主要ルールに method/version/status がある
-   [ ] 主要判断に evidence がある
-   [ ] warning / uncertainty が共通形式で出る
-   [ ] 節入り境界テストが通る
-   [ ] 通変星100組テストが通る
-   [ ] 十二運完全マトリクスが通る
-   [ ] 身強身弱境界テストが通る
-   [ ] 格局候補と最終判定が分離されている
-   [ ] 用神の採用・不採用理由が追跡できる
-   [ ] 大運・歳運の根拠が構造化されている
-   [ ] 三柱モードの不確実性がAI/PDFまで伝播する
-   [ ] reading_context v2 が固定されている
-   [ ] AIが占術を再計算しない
-   [ ] facts / interpretation / advice が分離されている
-   [ ] Quality Gate V2 が通る
-   [ ] Auto-Repair後に再検査される
-   [ ] ReadingProduct V2 が固定されている
-   [ ] PDF V2 E2E が通る
-   [ ] Golden Chart 差分が説明済み
-   [ ] Golden PDF 差分が説明済み
-   [ ] 重大な未説明 regression が0件
-   [ ] v1.2 の既知制約が文書化されている

------------------------------------------------------------------------

## 36. v1.2 で意図的にやらないこと

-   AIに命式計算を任せる
-   AIの文章を占術上の正解として採用する
-   テストなしで閾値を変更する
-   v1.1との差分を記録せず結果を変える
-   UI・占術ロジック・PDFを同時に大改修する
-   アカデミー教材に合わせるために占術ルールを歪める
-   不明なケースを無理に断定する
-   CRM・課金をエンジンv1.2の必須条件へ混ぜる

------------------------------------------------------------------------

## 37. アカデミーとの関係

v1.2 では双方向連動そのものは必須実装にしない。

ただし evidence の構造化は、将来の学習モードを可能にする。

``` text
講義
↓
自分で命式を読む
↓
エンジンで判定
↓
evidence を確認
↓
自分の判断との差を見る
↓
復習講義へ戻る
```

エンジンは「答えを押しつける機械」ではなく、
**鑑定士が根拠を確認するための道具**として設計する。

------------------------------------------------------------------------

## 38. v1.3 / Pro への引き継ぎ候補

v1.2 完成後の候補:

-   顧客別保存
-   鑑定履歴
-   PDF履歴管理
-   再鑑定
-   AI鑑定文編集
-   大運・歳運比較
-   ケーススタディ保存
-   アカデミー講義リンク
-   学習モード
-   会員認証
-   月額課金
-   利用回数制御
-   管理画面
-   API利用量管理

v1.2 はこれらを載せるための**鑑定コア基盤**を完成させる版とする。

------------------------------------------------------------------------

# 付録A: v1.2 主要 method の現行基準

現時点で確認されている代表的 method 名を、移行時の照合基準とする。

``` text
final_strength_judgment_v2
pattern_candidates_v1
pattern_judgment_v2
useful_gods_v3
luck_pillars_v2
current_luck_v1
annual_luck_v1
integrated_luck_v1
reading_context_v1
reading_product_v1
```

これらは「v1.2完成時にも必ず同じ名前にする」という意味ではない。
変更する場合は migration と期待差分を記録する。

------------------------------------------------------------------------

# 付録B: Change Record Template

``` text
Change ID:
Date:
Author:

対象モジュール:
対象method:

v1.1仕様:
v1.2仕様:

変更理由:
占術上の根拠:
技術上の理由:

影響範囲:
期待される結果差分:
既知の非互換:

追加Unit Test:
追加Boundary Test:
Golden Chart更新:
AI Contract更新:
PDF E2E更新:

migration:
review:
status:
```

------------------------------------------------------------------------

# 付録C: 判定オブジェクト設計原則

主要な判断は最低でも次を答えられること。

1.  **何を判定したか**
2.  **結論は何か**
3.  **どのルールを使ったか**
4.  **何が根拠か**
5.  **反対要因は何か**
6.  **確信度はどの程度か**
7.  **警告はあるか**
8.  **未確定部分は何か**

これが v1.2 の中心思想である。

------------------------------------------------------------------------

# 付録D: リリース直前チェック

``` text
[ ] git status clean
[ ] v1.1 baseline tag exists
[ ] v1.2 changelog complete
[ ] all tests green
[ ] no unexplained xfail/xpass increase
[ ] Golden Chart reviewed
[ ] Golden PDF reviewed
[ ] API schema frozen
[ ] reading_context_v2 frozen
[ ] rule versions frozen
[ ] warnings documented
[ ] known limitations documented
[ ] sample customer reading generated
[ ] Quality Gate passed
[ ] Auto-Repair path tested
[ ] PDF generated successfully
[ ] release tag v1.2.0
```

------------------------------------------------------------------------

## 最終定義

**Yakumo Engine v1.2
=「計算できるエンジン」から「根拠を説明でき、AIと安全に連携できる鑑定エンジン」への完成版アップグレード。**

v1.1 で成立した、

`命式 → 判定 → AI → Quality Gate → PDF`

の一周を壊さず、

`命式 → 判定 + evidence + version + uncertainty → AI翻訳 → 整合性検査 → PDF`

へ進化させる。
