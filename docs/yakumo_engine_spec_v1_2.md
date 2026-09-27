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

### 4.2 Common Judgment Metadata Contract

`common_judgment_metadata_v1`を、既存component outputを置換しないopt-in companion metadata contractとして定義する。本contractはReading Context v2の26-field schemaには追加しない。

adapterが返すcontract envelopeは`schema_version`と`components`をREQUIREDとする。

``` json
{
  "schema_version": "common_judgment_metadata_v1",
  "components": {
    "strength": {
      "source_path": "final_strength_judgment",
      "method": "final_strength_judgment_v2",
      "version": null,
      "status": "provisional",
      "component_status": null,
      "evidence": {},
      "warnings": [],
      "uncertainty": []
    }
  }
}
```

`schema_version`は固定文字列`common_judgment_metadata_v1`、`components`はregistered component名をkey、component recordをvalueとするobjectとする。各registered component recordは次のfieldをすべてREQUIREDとして持ち、fieldを省略してはならない。

| field | type | null | normative semantics |
|---|---|---|---|
| `source_path` | string \| null | source不存在時のみ可 | raw chart result上のprovenance path。present sourceではnon-null stringとし、Golden verification pathとして扱ってはならない |
| `method` | string \| null | source不存在時等に可 | registered calculation sourceが存在する場合はnon-null stringとし、raw sourceからexact projectionする。algorithm/rule identifierでありversion sourceではない |
| `version` | string \| null | 可 | component ownerが明示的に提供した独立versionだけを使用する |
| `status` | `resolved` \| `provisional` \| `uncertain` \| `unsupported` \| null | 可 | Judgment certainty専用namespace |
| `component_status` | string \| null | 可 | detection result、processing result、phase、lifecycle、その他component固有状態のraw value |
| `evidence` | object \| array \| null | 可 | raw sourceに存在するcalculation evidenceだけをexact deep copyする |
| `warnings` | array of string | 不可 | sourceのuser-visible non-structured noticeをexact projectionする |
| `uncertainty` | array of structured uncertainty object | 不可 | sourceのstructured uncertaintyをexact projectionする |

empty collectionは`[]`、missing nullable metadataは`null`とする。field omissionおよび`"unknown"`による代用は禁止する。

`method`は少なくとも、`weighted_five_elements`、month commandの`basic` / `weighted` / `seasonal` / `integrated`各component、`weighted_root_strength`、`final_strength_judgment`、`branch_relation_strength`、`pattern_judgment`、`useful_gods`、`luck_pillars`、`current_luck`、`annual_luck`、`integrated_luck`について、source objectが存在する場合にnon-null REQUIREDとする。

初期source registryは次のとおりとする。`month_command.*`は`components.month_command.components`配下のnested componentを表す。adapterはこのregistryにないsourceを推測または自動追加してはならない。

| component key | raw chart-result source path |
|---|---|
| `five_elements` | `weighted_five_elements` |
| `month_command.basic` | `month_command` |
| `month_command.weighted` | `weighted_month_command` |
| `month_command.seasonal` | `seasonal_strength` |
| `month_command.integrated` | `integrated_month_strength` |
| `roots` | `weighted_root_strength` |
| `strength` | `final_strength_judgment` |
| `relations` | `branch_relation_strength` |
| `pattern` | `pattern_judgment` |
| `useful_gods` | `useful_gods` |
| `luck_pillars` | `luck_pillars` |
| `current_luck` | `current_luck` |
| `annual_luck` | `annual_luck` |
| `integrated_luck` | `integrated_luck` |

source component自体が存在しない場合もregistered component keyと全REQUIRED fieldは保持し、`source_path`、`method`、`version`、`status`、`component_status`、`evidence`は`null`、`warnings`と`uncertainty`は`[]`とする。calculationではないengine lifecycle metadataでは`method: null`を許す。

単一の既存methodを持たないmonth command aggregateはgroup containerとし、8つのREQUIRED metadata fieldに加えて`components` objectを持つ。aggregateの`source_path`、`method`、`version`、`status`、`component_status`、`evidence`は`null`、`warnings`と`uncertainty`は`[]`とし、`basic`、`weighted`、`seasonal`、`integrated`の4 component recordを個別に保持する。

### 4.3 Status Namespace

canonical Judgment statusは次の4語だけとする。

``` text
resolved
provisional
uncertain
unsupported
```

-   `resolved`: 採用済みruleと現在のvalidation scope内で確定している。
-   `provisional`: calculationは成立しているが、ruleまたはvalidation上の保留が残る。
-   `uncertain`: input、boundary、calculation condition等により確信できない。
-   `unsupported`: 現行ruleでは評価対象外または判定不能である。

`status: null`はcanonical Judgment statusがsourceに存在しないことを意味する。`null`を`unsupported`の代用にしてはならない。

processing result、detection result、phase、lifecycle state、component固有状態は`component_status`へ分離し、canonical Judgment certaintyとして解釈してはならない。

legacy raw statusは次の手順だけで移行する。

1.  raw statusがcanonical 4語と完全一致する場合は、`status = raw status`、`component_status = null`とする。
2.  human-reviewed explicit mapping registryに存在する場合は、`status = mapped canonical value`、`component_status = raw status`とする。
3.  その他は、`status = null`、`component_status = raw status`とする。

substring、prefix、suffix、regexによるstatus推測は禁止する。

初期explicit mapping registryは次のとおりとする。

| raw status | canonical status |
|---|---|
| `provisional_weights` | `provisional` |
| `provisional_month_command` | `provisional` |
| `provisional_weighted_month_command` | `provisional` |
| `provisional_seasonal_strength` | `provisional` |
| `provisional_integrated_month_strength` | `provisional` |
| `provisional_weighted_roots` | `provisional` |
| `provisional_branch_relation_strength` | `provisional` |
| `provisional_pattern_judgment_v2` | `provisional` |
| `provisional_useful_gods_v3` | `provisional` |
| `provisional_luck_pillars_v2` | `provisional` |
| `provisional_annual_luck_v1` | `provisional` |
| `provisional_integrated_luck_v1` | `provisional` |

`current_luck_resolved`はcurrent-luckのcomponent-specific stateであり、canonical `resolved`へmappingしてはならない。

### 4.4 Evidence Semantics

evidenceは次の3種類を分離する。

1.  Calculation evidence: score、判定、候補、採否等の既存計算根拠。Common Judgment recordの`evidence`へ入れてよいのはこれだけとする。
2.  Provenance: `source_path`、`method`、`version`、raw component status等。calculation evidenceへ混入してはならない。
3.  Golden / Human Verification Evidence: approval record、Golden wrapper、manifest、SHA-256、commit history。runtime Common Judgmentへ入れてはならない。

Goldenの存在をastrology calculation evidenceとして扱ってはならない。sourceにcalculation evidenceが存在しない場合は`evidence: null`とし、新しいevidence、summary、interpretationまたはjudgmentを生成してはならない。

### 4.5 Warnings / Uncertainty / Notes

-   `warnings`はuser-visible non-structured noticeとする。sourceにない場合は`[]`とし、`notes`から生成、normalization、deduplicationをしてはならない。
-   `uncertainty`はstructured uncertaintyとする。sourceにない場合は`[]`とし、warningとの相互変換または推測生成をしてはならない。
-   `notes`はdeveloper explanation、scope、supplemental informationとし、warningへ昇格してはならない。

structured uncertaintyは既存の`code`、`category`、`status`、`severity`、`scope`、`message`を維持し、categoryおよびseverity vocabularyは`engine/judgment_schema.py`をsource of truthとする。

### 4.6 No-Astrology-Change Rule

Common Judgment Metadata adapterはmetadata projectionだけを行う。四柱、score、label、confidenceの再計算または変更、production statusの変更、warning / uncertaintyの生成、evidenceの再解釈をしてはならない。Astrology Logic Impactは`NONE`とする。

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

-   strong-side: GC03（fixture ID: `1984_fukuoka_male_afternoon_v2`）は、`calculation_scope == "four_pillars"`、`final_score == 71.5`、`technical_label == "very_strong"`、`label == "極身強"` の承認済み fixture である。`calendar_verified`、`strength_verified`、`golden_regression` はすべて confirmed であり、承認済み strong-side regression test は実装済みかつ passing とする。strength approval record は `tests/verification/extreme_fixtures/GC03_1984_fukuoka_male_afternoon_strength_v1.json`（commit `4f9ed1712a582796a0dc4dc1c42a3cdde66725f4`）、regression test は commit `fe5c49497d30e89efb062dbf85d292cbb7585322` で固定する。したがって strong-side requirement は complete とする。この承認は Yakumo Engine v1.2 compatibility rules に対する独立検証・承認であり、普遍的な四柱推命上の真理を証明するものではない。
-   weak-side: Michael Jordan（fixture ID: `1963_brooklyn_male_afternoon_v2`）は、`calculation_scope == "four_pillars"`、`final_score == 12.05`、`technical_label == "very_weak"`、`label == "極身弱"` の承認済み fixture である。`calendar_verified`、`strength_verified`、`golden_regression` はすべて confirmed であり、承認済み weak-side regression test は実装済みかつ passing とする。approval record は `tests/verification/extreme_fixtures/Michael_Jordan_1963_brooklyn_male_afternoon_strength_v1.json`、regression test は commit `e369a9f2bb7c2c1ee73c80a9e7e1179e7eb70c34`、v1.2 strength-only Golden は commit `705e8b7324cfb1105b020fec71474fbfa82a1e47` で固定する。したがって weak-side requirement は complete とする。この承認も Yakumo Engine v1.2 compatibility rules に対する独立検証・承認であり、普遍的な四柱推命上の真理を証明するものではない。
-   overall: approved strong-side fixture 1 件以上および approved weak-side fixture 1 件以上の両条件が揃ったため、「極端命式テスト」の requirement は complete とする。ただし、この完了は `final_strength_judgment.status` の `provisional` から `resolved` への変更を意味しない。provisional 解除には、残存する rule uncertainty、validation scope および別途定める status 完成条件の確認が必要である。

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

Reading Context v2 は既存の計算結果をAI向けにprojectionするschemaであり、占術計算を行わない。値の正本は既存のchart resultとし、Reading Context builderは四柱、五行、身強身弱、格局、用神、運勢その他の占術判断を再計算してはならない。

### 20.2 Normative top-level contract

以下のtop-level fieldはすべてREQUIREDとし、省略してはならない。

``` json
{
  "schema_version": "reading_context_v2",
  "engine_version": "1.2",
  "subject": {},
  "chart": {},
  "birth_time_status": {},
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
  "source_metadata": {},
  "evidence": [],
  "validation": {},
  "method": "reading_context_v2",
  "version": "reading_context_v2",
  "status": "ready_for_ai_reading",
  "notes": []
}
```

field typeは次のとおりとする。

| field | type |
|---|---|
| `schema_version` | string |
| `engine_version` | string \| null |
| `subject` | object |
| `chart` | object |
| `birth_time_status` | object |
| `day_master` | object \| null |
| `five_elements` | object \| null |
| `month_command` | object \| null |
| `roots` | object \| null |
| `strength` | object \| null |
| `relations` | object \| null |
| `pattern` | object \| null |
| `useful_gods` | object \| null |
| `luck` | object |
| `consultation` | object \| null |
| `facts` | array of object |
| `interpretation_hints` | array of object |
| `warnings` | array |
| `uncertainty` | array of object |
| `source_metadata` | object |
| `evidence` | array of object |
| `validation` | object |
| `method` | string |
| `version` | string |
| `status` | string |
| `notes` | array of string |

値を取得する既存sourceが存在しないREQUIRED objectまたはscalarは`null`とする。正当に結果が0件であるcollectionは`[]`とする。source不在を空objectや`"unknown"`で表現してはならない。REQUIRED fieldの省略も認めない。

`schema_version`、`method`、`version`、`status`は次の値に固定する。

``` text
schema_version = reading_context_v2
method         = reading_context_v2
version        = reading_context_v2
status         = ready_for_ai_reading
```

`version`を`"2"`または`"2.0"`へ変換してはならない。

### 20.3 subject / chart / birth time

`subject`は次のfieldをREQUIREDとして保持する。各値は既存inputからprojectionし、sourceが存在しない場合は`null`とする。

``` text
birth_date:  string | null
birth_time:  string | null
birth_place: string | null
gender:      string | null
timezone:    string | null
```

v1の`natal_chart`は変更しない。v2では同じ値を`chart`へprojectionする。

``` json
{
  "chart": {
    "pillars": {
      "year": {},
      "month": {},
      "day": {},
      "hour": {}
    },
    "pillar_sequence": []
  }
}
```

利用可能な各pillar objectは次のfieldをREQUIREDとして保持する。

``` text
position:                     string
pillar:                       string | null
stem:                         string | null
branch:                       string | null
stem_ten_god:                 string | null
twelve_stage:                 string | null
hidden_stems:                 array
main_hidden_stem:             string | null
main_hidden_stem_ten_god:     string | null
```

四柱モードでは`chart.pillars.hour`をobjectとし、`pillar_sequence`は年・月・日・時の4要素を保持する。三柱モードでは時柱を推測せず、次の形をMUSTとする。

``` json
{
  "chart": {
    "pillars": {
      "year": {},
      "month": {},
      "day": {},
      "hour": null
    },
    "pillar_sequence": ["...", "...", "...", null]
  }
}
```

`birth_time_status`は既存の出生時刻既知・未知、`calculation_scope`、interpretation scope、luck timing precision、provisional flagをprojectionする。三柱モードでは既存confidence、warning、uncertaintyを変更してはならない。hour-dependent sourceが存在しない場合は`null`とし、fieldを省略してはならない。

### 20.4 month command / roots / relations

これらは既存chart resultからdeep-copy projectionし、Reading Context builder内で再計算してはならない。

`month_command`が利用可能な場合は次のcomponentをすべてREQUIREDとする。各componentは対応sourceのobjectまたは`null`とする。

``` json
{
  "month_command": {
    "basic": {},
    "weighted": {},
    "seasonal": {},
    "integrated": {}
  }
}
```

| component | source path |
|---|---|
| `basic` | `month_command` |
| `weighted` | `weighted_month_command` |
| `seasonal` | `seasonal_strength` |
| `integrated` | `integrated_month_strength` |

`roots`が利用可能な場合は次のcomponentをすべてREQUIREDとする。

``` json
{
  "roots": {
    "basic": {},
    "weighted": {}
  }
}
```

| component | source path |
|---|---|
| `basic` | `root_strength` |
| `weighted` | `weighted_root_strength` |

`relations`が利用可能な場合は次のcomponentをすべてREQUIREDとする。

``` json
{
  "relations": {
    "clashes": {},
    "combinations": {},
    "trines": {},
    "punishments": {},
    "harms": {},
    "breaks": {},
    "strength": {}
  }
}
```

| component | source path |
|---|---|
| `clashes` | `branch_clashes` |
| `combinations` | `branch_combinations` |
| `trines` | `branch_trines` |
| `punishments` | `branch_punishments` |
| `harms` | `branch_harms` |
| `breaks` | `branch_breaks` |
| `strength` | `branch_relation_strength` |

地支関係の`total_score`を日主強弱へのdirectional adjustmentとして再解釈してはならない。

### 20.5 facts

`facts`はflat registryとし、各entryは次のfieldをREQUIREDとする。

``` json
{
  "code": "strength.final_score",
  "category": "strength",
  "value": 50.0,
  "context_path": "strength.final_score",
  "source_path": "final_strength_judgment.final_score",
  "confidence": null
}
```

``` text
code:         string
category:     string
value:        any JSON value
context_path: string
source_path:  string
confidence:   string | null
```

初回schema freezeで許可するfact codeは次のallowlistに限定する。

``` text
chart.pillar_sequence
day_master.stem
day_master.element
five_elements.weighted_scores
strength.final_score
strength.technical_label
strength.label
strength.confidence
pattern.primary_pattern
useful_gods.primary_useful_element
```

factは既存chart/contextから確実にprojectionできる値だけを保持する。`value`は`context_path`が指す値と一致しなければならない。sourceにconfidenceがなければ`null`とする。narrative、新しい解釈、新しい占術判断、sourceに存在しない値をfactとして生成してはならない。allowlist外のfact codeを追加する場合はschema changeとしてreview、test、Golden差分を記録する。

allowlistは許可範囲であり、全codeの出力を要求するものではない。対応source valueが存在しないfact entryは生成せず、`facts` arrayから省略する。

### 20.6 interpretation_hints / consultation

v1の`reading_sections`は変更しない。v2では同じ情報を`interpretation_hints`へprojectionし、`reading_sections`をv2 top-levelへ重複保持しない。

各hintは次のfieldをREQUIREDとする。

``` json
{
  "section": "career",
  "focus": ["day_master", "strength"],
  "instruction": "..."
}
```

``` text
section:     string
focus:       array of string
instruction: string
```

既存`reading_sections`に存在しないfocusまたはinstructionを生成してはならない。

`consultation`はREQUIREDかつnullableとする。相談内容がない場合は`null`とし、空objectまたはfield省略で表現してはならない。相談内容がある場合は既存`consultation_context`をprojectionする。Reading Context v2は相談内容なしでも生成可能でなければならない。

### 20.7 warnings / uncertainty

`warnings`はREQUIRED arrayとし、既存chart resultの`warnings`を順序・値・型を変更せずdeep copyする。新しいwarningの生成、文言変更、structured objectへの推測変換を行ってはならない。warningがなければ`[]`とする。

`uncertainty`はREQUIRED array of objectとし、既存chart resultのstructured uncertaintyを順序・値・型を変更せずdeep copyする。`code`、`category`、`status`、`severity`、`scope`、`message`を追加、削除、変更してはならない。uncertaintyがなければ`[]`とする。

warningとuncertaintyを相互変換してはならない。Reading Context builderはdeduplicationやnormalizationによってsource情報を変更してはならない。

### 20.8 source_metadata

主要判定ごとに、

``` json
{
  "source_path": "...",
  "method": "...",
  "version": null,
  "status": "..."
}
```

を保持する。各entryの`source_path`、`method`、`version`、`status`はREQUIREDであり、値のtypeはstringまたは`null`とする。sourceに独立したversion fieldが存在しない場合は`version: null`とし、method名のsuffixからversionを推測してはならない。fieldの省略や`"unknown"`による代用も認めない。

`source_metadata`は次のentryをREQUIREDとする。

``` text
engine
five_elements
month_command
roots
strength
relations
pattern
useful_gods
luck_pillars
current_luck
annual_luck
integrated_luck
```

source pathは次を使用する。

| entry | source path |
|---|---|
| `engine` | `engine_metadata` |
| `five_elements` | `weighted_five_elements` |
| `roots` | `weighted_root_strength` |
| `strength` | `final_strength_judgment` |
| `relations` | `branch_relation_strength` |
| `pattern` | `pattern_judgment` |
| `useful_gods` | `useful_gods` |
| `luck_pillars` | `luck_pillars` |
| `current_luck` | `current_luck` |
| `annual_luck` | `annual_luck` |
| `integrated_luck` | `integrated_luck` |

`month_command`全体には単一の既存method/statusが存在しないため、aggregate entryの`source_path`、`method`、`version`、`status`は`null`とし、`basic`、`weighted`、`seasonal`、`integrated`のcomponent metadataを保持する。aggregate methodを新しく作ってはならない。

### 20.9 evidence

`evidence`はREQUIRED arrayとし、full evidence treeではなく、既存evidenceへのsummary/referenceだけを保持する。

``` json
{
  "category": "strength",
  "available": true,
  "source_path": "final_strength_judgment.evidence",
  "summary": {
    "method": "final_strength_judgment_v2",
    "status": "provisional"
  }
}
```

各entryは`category`、`available`、`source_path`、`summary`をREQUIREDとする。`category`はstring、`available`はboolean、`source_path`はstringまたは`null`、`summary`はobjectまたは`null`とする。

sourceに存在しないevidence、summary、interpretation、judgmentを生成してはならない。Reading Context builderはevidenceを再解釈してはならない。evidenceが存在しない場合は`available: false`、`source_path: null`または確認済みsource path、`summary: null`として表現する。

### 20.10 validation contract

`validate_reading_context_v2()`はschemaとprojection整合性だけを検証し、占術的な正しさを再計算してはならない。`validation`は次のfieldをREQUIREDとする。

``` json
{
  "valid": true,
  "errors": [],
  "missing_required_fields": [],
  "unknown_fields": []
}
```

validatorは最低限、次を検証する。

-   `schema_version`、`method`、`version`、`status`の固定値。
-   REQUIRED top-level fieldの存在とfield type。
-   未定義top-level fieldおよびstrict core schema外fieldが存在しないこと。
-   `chart.pillars`と`pillar_sequence`の構造的整合。
-   四柱・三柱モードのhour規則。
-   `consultation`がobjectまたは`null`であること。
-   `warnings`と`uncertainty`のtype。
-   `source_metadata`のREQUIRED entryと共通field。
-   fact codeがallowlist内で重複していないこと。
-   factの`context_path`が解決でき、`value`と一致すること。
-   evidence entryのtypeとsource reference構造。

strict core schemaはv2のtop-level、wrapper、facts、interpretation hints、source metadata、evidence、validationに適用する。既存production resultをdeep copyするmonth command、roots、relationsの各component内部は、それぞれのsource schemaを維持し、Reading Context validatorが独自にfieldを追加または削除してはならない。

validatorは四柱、五行、score、label、格局、用神、運勢を再計算してはならない。confidence、warning、uncertainty、statusを変更してはならない。

### 20.11 backward compatibility

Reading Context v2はopt-in builderとして追加する。既存の`reading_context_v1` producer、schema、method、status、field名をin-placeで変更してはならない。

次をv2導入だけを理由に変更してはならない。

-   `tests/golden/v1_1/**`
-   `reading_api_v1`
-   `reading_product_v1`
-   v1の`natal_chart`および`reading_sections`

v2 builderは既存chart resultおよびv1 contextからのprojectionだけを行う。v1 consumerをv2へ一括切替してはならず、consumerごとに明示的なmigrationと互換testを必要とする。

`common_judgment_metadata_v1`はReading Context v2の26-field context外に置くopt-in companion contractとする。導入によって`source_metadata`のraw projection、missing versionの`null`、method suffixからのversion推測禁止、top-level warnings / uncertaintyのexact projection、承認済み5 categoryのevidenceを変更してはならない。将来のAI Reading v2は`reading_context_v2`と`common_judgment_metadata_v1`を別contractとして受け取ることができる設計とする。

### 20.12 禁止

-   AI用 prompt 内で命式を再計算させない。
-   schema にない値を AI が「確定値」として追加しない。
-   provisional を resolved のように見せない。
-   v2 builder内で占術計算を再実行しない。
-   sourceに存在しないfact、evidence、summary、interpretation、judgmentを生成しない。
-   v2導入を理由に占術rule、score、label、confidence、warning、uncertaintyを変更しない。
-   `final_strength_judgment.status`を`provisional`から`resolved`へ変更しない。

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

### 22.1 Contract identity

AI Reading v2 は、既存エンジン出力を検証・grounding・文章化するための
opt-in contract とする。

``` json
{
  "schema_version": "ai_reading_v2",
  "version": "ai_reading_v2"
}
```

-   `schema_version` は `ai_reading_v2` に固定する。
-   `version` は `ai_reading_v2` に固定する。`2` や `2.0` へ変換しない。
-   AI Reading v2 は v1 AI Reading とは別 contract とし、v1 の module、schema、
    Golden、consumer を置換しない。
-   AI Reading v2 の導入によって占術計算 rule を変更してはならない。

### 22.2 Input contract

AI Reading v2 は次の二つの独立した validated contract を REQUIRED input とする。

1.  `reading_context_v2`
2.  `common_judgment_metadata_v1`

概念上の request builder boundary は次のとおりとする。

``` python
build_ai_reading_request_v2(
    reading_context,
    judgment_metadata,
    *,
    sections=None,
    language="ja",
    tone="professional_warm",
)
```

-   二つの input を flatten、merge、または一つの raw object へ変換してはならない。
-   prompt construction 前に、それぞれの owner validator を通さなければならない。
-   builder は input を deep-copy して扱い、元 object を変更してはならない。
-   consultation の唯一の source of truth は
    `reading_context["consultation"]` とする。別の consultation argument を禁止する。
-   `reading_context_v2.source_metadata` と Common Judgment Metadata を merge してはならない。
-   v1.2ではpartial section generationをsupportしない。`sections` parameterは将来拡張用に
    reservedとし、`None`だけを許可する。`sections=None`は22.4のexact eight sectionsすべてを
    生成することを意味し、successful final wrapperのsection cardinalityを変更してはならない。
-   v1.2 AI Reading v2でsupportする`language`は`"ja"`だけとする。その他の値はinvalidとし、
    localizationは将来versionへdeferする。`tone`はmodel-authored textの表現だけに影響し、
    trusted fixed fieldまたは22.5のdisclaimer constantを変更してはならない。

v1.2のtone vocabularyは次のnormative constantに固定する。

``` python
AI_READING_V2_SUPPORTED_TONES = (
    "professional_warm",
)
```

`tone`のdefaultは`"professional_warm"`とし、他の値はinvalidとする。v1の
`SUPPORTED_TONES`をimportまたは暗黙に再利用してはならない。toneはmodel-authored textだけに
影響でき、facts、catalog、reference、section ID/title、year/order、disclaimer、status、その他の
trusted fieldを変更してはならない。

#### 22.2.1 Internal request contract

`build_ai_reading_request_v2()`のreturn valueは、final `ai_reading_v2` wrapperとは別の
internal/runtime contract `ai_reading_request_v2`とする。exact top-level fieldは次の13件とし、
すべてREQUIRED、field omissionおよびunknown fieldを禁止する。

1.  `schema_version`
2.  `version`
3.  `method`
4.  `status`
5.  `language`
6.  `tone`
7.  `source_contracts`
8.  `trusted_catalogs`
9.  `trusted_attachments`
10. `model_input`
11. `messages`
12. `model_output_schema`
13. `validation`

identity fieldは次に固定する。

``` json
{
  "schema_version": "ai_reading_request_v2",
  "version": "ai_reading_request_v2",
  "method": "reading_prompt_v2",
  "status": "ready_for_ai_generation",
  "language": "ja",
  "tone": "professional_warm"
}
```

`source_contracts`はexactly次のshapeとし、validated input identityをexact projectionする。

``` json
{
  "reading_context": {
    "schema_version": "reading_context_v2",
    "method": "reading_context_v2",
    "version": "reading_context_v2",
    "status": "ready_for_ai_reading"
  },
  "judgment_metadata": {
    "schema_version": "common_judgment_metadata_v1"
  }
}
```

`trusted_catalogs`はexactly次の5 fieldを持つ。

| field | type |
|---|---|
| `fact_codes` | array of string |
| `source_components` | array of string |
| `warnings` | array of 22.10 `warning_catalog_entry` |
| `uncertainty` | array of 22.10 `uncertainty_catalog_entry` |
| `luck_value_sources` | array of 22.12 `luck_value_source_entry` |

`trusted_attachments`はexactly次のfieldを持つ。

| field | type / exact value |
|---|---|
| `final_schema_version` | `"ai_reading_v2"` |
| `final_version` | `"ai_reading_v2"` |
| `final_method` | `"openai_responses_api_v2"` |
| `final_status` | `"completed"` |
| `engine_version` | string \| null。Reading Contextからexact projection |
| `sections` | 22.4のexact 8件の`section_id` / `title` object |
| `future_flow_years` | array of integer。22.12のtrusted year/order |
| `consultation_present` | boolean |
| `disclaimer` | exact `AI_READING_V2_DISCLAIMER` |

`request.status`はrequest lifecycle、`trusted_attachments.final_status`はsuccessful final assemblyで
使用するtrusted expected valueであり、混同してはならない。`final_status="completed"`はmodel
generationとfinal validationが成功した場合にだけfinal wrapperへattachできる。

`model_input`はexactly次の5 fieldを持つ。

| field | rule |
|---|---|
| `reading_context` | validated `reading_context_v2`のexact deep copy |
| `judgment_metadata` | validated `common_judgment_metadata_v1`のexact deep copy |
| `trusted_catalogs` | request内`trusted_catalogs`のexact deep copy |
| `section_slots` | 22.4のexact 8件の`section_id` / `title` object |
| `future_flow_years` | trusted year/orderのarray of integer |

`messages`はexactly2件のarrayとし、順序をsystem、userに固定する。各entryはexactly`role`と
`content`を持ち、unknown fieldを禁止する。`role`はそれぞれ`"system"`、`"user"`に固定する。
両`content`はtrusted codeだけが次のconstantとserialization ruleから構築し、自由作文template、
model-authored content、v1 promptのimportまたは再利用を禁止する。

`messages[0].content`は次のnormative constantとexact string matchしなければならない。

``` python
AI_READING_V2_SYSTEM_PROMPT = (
    "あなたは八雲式四柱推命エンジンのAI Reading v2文章化レイヤーです。出力言語は日本語、toneはprofessional_warmとし、model_output_schemaに厳密に一致するJSONだけを返してください。\n"
    "sectionsは提示された順序どおりのexactly 8 positional slotsとし、section ID、title、yearその他のtrusted fieldを返さないでください。\n"
    "占術上の主張は、提示されたfacts、source components、および許可されたluck crosswalkだけを根拠とし、referenceを新規作成してはいけません。\n"
    "warningとuncertaintyは提示されたcatalog IDからだけ選択し、新規作成、変更、正規化、重複排除をしてはいけません。\n"
    "出生時間不明の場合はknown_pillars_onlyを守り、時柱または時柱由来の解釈を推定せず、strength confidenceを強化せず、estimated timingとapplicable uncertaintyを保持し、internal_reference_timeを出生時刻として扱わないでください。\n"
    "四柱、蔵干、通変星、十二運、五行score、身強身弱、干支関係、格局、用神、大運、歳運、current luck、integrated luckを再計算、再判定、再分類してはいけません。\n"
    "missing hour、true solar time、timezone correction、location correctionを推定してはいけません。\n"
    "consultationは説明の優先順位とpractical contextにだけ使用し、占術結果を生成または変更してはいけません。\n"
    "すべてのgrounded_text_blockでclaim_typeを宣言し、意図するtextと一致させてください。practicalに占術またはluckの主張を含めず、astrologyはfactでgroundし、luck_astrologyは許可されたlocationとluck crosswalkでgroundしてください。占術またはluckの主張をpracticalとして偽装してはいけません。\n"
    "返してよいのはmodel-owned payloadだけです。section_id、title、year、disclaimer、catalog、source contract、engine_version、schema_version、version、method、status、validationを返してはいけません。\n"
    "source_fact_codes、source_components、warning IDs、uncertainty IDsは提示されたallowed valuesからだけ選択し、strict JSONとして返してください。"
)
```

`messages[1].content`は次のexact constantとcanonical JSONを文字列連結した値とする。

``` python
AI_READING_V2_USER_PROMPT_PREFIX = (
    "以下のmodel_inputだけを使用し、model_output_schemaに厳密に一致するJSONを生成してください。\n"
    "model_input="
)

user_content = AI_READING_V2_USER_PROMPT_PREFIX + json.dumps(
    model_input,
    ensure_ascii=False,
    separators=(",", ":"),
    sort_keys=False,
    allow_nan=False,
)
```

serializationはUTF-8のJSON text、indentなし、追加whitespaceなし、final newlineなしとする。
`model_input`のkey insertion orderは22.2.1のcontract order、各nested trusted objectのkey orderは
各owner contractまたは本節の記載順とする。`null`、empty array、empty objectを省略してはならない。
prefix後のsubstringはそれだけで`model_input`全体へdecodeできなければならず、前後に別dataまたは
自由文を追加してはならない。`reading_context`と`judgment_metadata`は別keyのまま保持し、flatten、
mergeまたは相互変換してはならない。tone等のtrusted instructionはsystem constantだけに置き、
`model_input` dataへ混入しない。`model_output_schema`は22.2.3のexact schema objectとする。

`validation`はexactly次のshapeのdeterministic reportとする。

``` json
{
  "valid": true,
  "errors": [],
  "missing_required_fields": [],
  "unknown_fields": []
}
```

requestの`validation`は22.13.1のprompt-specific prerequisite validation reportとする。
successful requestでは`valid=true`かつ三つのarrayがemptyでなければならない。invalid reportは
requestへattachして返さず、22.13.1の`ValueError` boundaryに従う。

#### 22.2.2 Exact model-only payload

modelはtrusted-owned fieldをechoしてはならない。model response payloadはexactly次の4 fieldを
REQUIREDとして持ち、unknown fieldを禁止する。

| field | type |
|---|---|
| `summary` | 22.4 `grounded_text_block` |
| `sections` | exactly 8 `model_section_payload` objects |
| `future_flow_yearly` | array of `model_year_payload` |
| `consultation_answer` | 22.4 `grounded_text_block` \| null |

`model_section_payload`はexactly次の8 fieldを持つ。

| field | type |
|---|---|
| `facts` | array of string |
| `summary` | `grounded_text_block` |
| `detail` | `grounded_text_block` |
| `evidence` | array of `grounded_text_block` |
| `interpretation` | array of `grounded_text_block` |
| `advice` | array of `grounded_text_block` |
| `warnings` | array of warning ID string |
| `uncertainty` | array of uncertainty ID string |

`model_year_payload`はexactly`summary`と`detail`を持ち、両方を`grounded_text_block`とする。
modelは`section_id`、`title`、`year`、catalog、disclaimer、source contract、engine version、
validation、schema/version/method/statusを返してはならない。

deterministic assemblyは次に固定する。

1.  model `sections`はexactly 8件とする。
2.  trusted codeはindex 0から7へ22.4のfixed `section_id` / `title`を順にattachする。
3.  `future_flow_yearly`の件数はtrusted year countとexact matchしなければならない。
4.  trusted codeは各model year indexへ同じindexのtrusted yearをattachし、assembled `yearly`を
    final `future_flow` sectionだけへ置く。
5.  consultationがabsentの場合、model `consultation_answer`は`null`だけを許可する。presentの場合は
    exact `grounded_text_block`をREQUIREDとし、`null`を許可しない。
6.  model-selected referenceをvalidation・resolveした後にだけtrusted final wrapperへ採用する。

model payloadのunknown field、trusted fieldのecho、section count不一致、year payload count不一致を
invalidとする。

#### 22.2.3 Exact model output JSON Schema

`ai_reading_request_v2.model_output_schema`はstrict JSON Schema objectとし、schema object自体の
top-level key insertion orderを`$defs`、`type`、`properties`、`required`、
`additionalProperties`に固定する。`type`は`"object"`、`required`はexactly `summary`、`sections`、
`future_flow_yearly`、`consultation_answer`の順、`additionalProperties`は`false`とし、
`properties`は同じ4 fieldだけを同じ順で持つ。

`$defs`はexactly次の7 definitionを記載順で持つ。

1.  `fact_code_array`
2.  `source_component_array`
3.  `warning_id_array`
4.  `uncertainty_id_array`
5.  `grounded_text_block`
6.  `model_section_payload`
7.  `model_year_payload`

最初の4 definitionはtrusted catalogから構築するdynamic string-array schemaとする。sourceは次に
固定する。

| definition | exact allowed-value source |
|---|---|
| `fact_code_array` | `trusted_catalogs.fact_codes` |
| `source_component_array` | `trusted_catalogs.source_components` |
| `warning_id_array` | `warning_id` values from `trusted_catalogs.warnings` |
| `uncertainty_id_array` | `uncertainty_id` values from `trusted_catalogs.uncertainty` |

allowed valueが1件以上の場合、dynamic string-array definitionはexactly次のshapeとし、`enum`には
対応trusted arrayの値を同じ順序で入れる。

``` json
{
  "type": "array",
  "items": {
    "type": "string",
    "enum": ["allowed_value"]
  },
  "uniqueItems": true
}
```

allowed valueが0件の場合は22.6のempty dynamic enum policyに従い、exactly次のshapeとする。

``` json
{
  "type": "array",
  "items": {
    "type": "string"
  },
  "minItems": 0,
  "maxItems": 0,
  "uniqueItems": true
}
```

`grounded_text_block` definitionはexactly次のshapeとする。

``` json
{
  "type": "object",
  "properties": {
    "text": {"type": "string"},
    "claim_type": {
      "type": "string",
      "enum": ["practical", "astrology", "luck_astrology"]
    },
    "source_fact_codes": {"$ref": "#/$defs/fact_code_array"},
    "source_components": {"$ref": "#/$defs/source_component_array"},
    "warnings": {"$ref": "#/$defs/warning_id_array"},
    "uncertainty": {"$ref": "#/$defs/uncertainty_id_array"}
  },
  "required": [
    "text",
    "claim_type",
    "source_fact_codes",
    "source_components",
    "warnings",
    "uncertainty"
  ],
  "additionalProperties": false
}
```

`claim_type.enum`は上記3語を常に無条件で列挙するstatic enumではなく、22.4のavailable claim type
policyによってrequestごとにtrusted codeが構築する。上記JSONは3 typeすべてがavailableな場合の
shapeを示す。per-type reference cardinalityとlocation固有ruleはconditional JSON Schemaへ埋め込まず、
strict JSON Schema validation後の22.13 semantic validationで検証する。複雑なconditional `oneOf`を
追加してはならない。

`model_section_payload` definitionはexactly次のshapeとする。

``` json
{
  "type": "object",
  "properties": {
    "facts": {"$ref": "#/$defs/fact_code_array"},
    "summary": {"$ref": "#/$defs/grounded_text_block"},
    "detail": {"$ref": "#/$defs/grounded_text_block"},
    "evidence": {
      "type": "array",
      "items": {"$ref": "#/$defs/grounded_text_block"}
    },
    "interpretation": {
      "type": "array",
      "items": {"$ref": "#/$defs/grounded_text_block"}
    },
    "advice": {
      "type": "array",
      "items": {"$ref": "#/$defs/grounded_text_block"}
    },
    "warnings": {"$ref": "#/$defs/warning_id_array"},
    "uncertainty": {"$ref": "#/$defs/uncertainty_id_array"}
  },
  "required": [
    "facts",
    "summary",
    "detail",
    "evidence",
    "interpretation",
    "advice",
    "warnings",
    "uncertainty"
  ],
  "additionalProperties": false
}
```

`model_year_payload` definitionはexactly次のshapeとする。

``` json
{
  "type": "object",
  "properties": {
    "summary": {"$ref": "#/$defs/grounded_text_block"},
    "detail": {"$ref": "#/$defs/grounded_text_block"}
  },
  "required": ["summary", "detail"],
  "additionalProperties": false
}
```

root `properties`はexactly次のschemaを持つ。

| property | exact schema |
|---|---|
| `summary` | `{"$ref":"#/$defs/grounded_text_block"}` |
| `sections` | `type=array`、`items={"$ref":"#/$defs/model_section_payload"}`、`minItems=8`、`maxItems=8` |
| `future_flow_yearly` | `type=array`、`items={"$ref":"#/$defs/model_year_payload"}`、`minItems=maxItems=len(trusted_attachments.future_flow_years)` |
| `consultation_answer` | `consultation_present=false`では`{"type":"null"}`、trueでは`{"$ref":"#/$defs/grounded_text_block"}` |

`sections`のpositional ownershipはindex 0から順に`core_personality`、`career`、`wealth`、
`relationships`、`health`、`current_luck`、`future_flow`、`advice`とする。`section_id`と`title`を
model schemaへ含めない。`future_flow_yearly`のyearはschemaへ含めず、trusted year countを両cardinality
keywordへ同じintegerとして埋め込む。consultationがabsentの場合、modelはJSON `null`以外を返せない。

JSON Schema validationだけでfinal validityを確定してはならない。per-type reference cardinality、
22.4.2のlocation matrix、およびglobal component enumでは表現しないscope-specific luck validityは、
schema validation後にsemantic validationしなければならない。luckについては22.12のblock scope、
source component、`luck_value_source_entry`の一致を検証する。

#### 22.2.4 Common Metadata source path trust boundary

AI Reading v2のinputは引き続き`reading_context_v2`と`common_judgment_metadata_v1`のexactly二つとし、
raw `chart_result`を第三inputとして追加してはならない。owner adapterが生成しowner validatorを
通過したCommon Judgment Metadataでは、non-null `source_path`をupstream adapterによるtrusted
presence assertionとして扱う。prompt builderはraw `chart_result`へ再resolveせず、registered
source pathとのexact match、present sourceでのrequired `method`、component record schemaを検証する。

AI Reading layerはraw provenance correctnessを再証明しない。`source_path=null`のrecordと
`month_command` aggregate containerはallowed source componentから除外する。non-null
`source_path`はcomponentの存在・provenance metadataを示すだけであり、Common Judgment Metadataを
astrology value sourceへ昇格させてはならない。

### 22.3 Responsibility boundary

-   `reading_context_v2.facts` は、AI がnon-luckの占術上の factual claimとして参照可能な
    value/codeのallowlistとする。luck valueだけは22.12のexplicit crosswalkに限定した例外とし、
    この例外によってfacts allowlist全体を拡張してはならない。
-   `reading_context_v2.interpretation_hints` は topic / focus guidance であり、
    factual truth source ではない。
-   `common_judgment_metadata_v1` は component ごとの certainty、warnings、
    uncertainty の source とする。新しい占術 value の source としてはならない。
-   Reading Context top-level `warnings` / `uncertainty` は global input limitation とする。
-   `consultation` は文章の emphasis と practical context にだけ使用し、
    astrology calculation input としてはならない。
-   `source_metadata` は provenance 専用とし、certainty source としてはならない。

### 22.4 Exact eight sections

AI Reading v2 の section ID は次の8件だけとし、記載順も固定する。

| order | section ID | trusted fixed title |
|---:|---|---|
| 1 | `core_personality` | `本質・性格` |
| 2 | `career` | `仕事・適職` |
| 3 | `wealth` | `金運` |
| 4 | `relationships` | `恋愛・人間関係` |
| 5 | `health` | `健康傾向` |
| 6 | `current_luck` | `現在の運勢` |
| 7 | `future_flow` | `今後の流れ` |
| 8 | `advice` | `総合アドバイス` |

title mappingは既存v1の`SECTION_TITLES_JA`をsource of truthとしてfreezeしたものである。
trusted codeがIDとtitleをattachし、modelは生成・変更してはならない。

AI Reading v2のtraceability unitは、1 sentenceではなく次の
`grounded_text_block`とする。各blockはexactly次の6 fieldを記載順でREQUIREDとして持つ。

``` json
{
  "text": "...",
  "claim_type": "practical",
  "source_fact_codes": [],
  "source_components": [],
  "warnings": [],
  "uncertainty": []
}
```

-   `text`はstringとする。
-   `claim_type`はmodel-owned declarationとし、22.4.1のavailable enumに含まれるstringとする。
-   `source_fact_codes`はtrusted dynamic enum内のfact codeだけを持つarray of stringとする。
-   `source_components`は§4のregistered Common Judgment componentだけを持つarray of stringとする。
-   `warnings`は22.10のtop-level warning catalogにresolveするwarning IDだけを持つarray of stringとする。
-   `uncertainty`は22.10のtop-level uncertainty catalogにresolveするuncertainty IDだけを持つ
    array of stringとする。
-   v1.2はblock単位のtraceabilityを要求し、sentence分割によるperfect semantic verificationは
    要求しない。

#### 22.4.1 Machine-readable claim classification

`claim_type`のfull vocabularyは次のnormative constantに固定する。このfieldはCommon Judgmentの
canonical `status`とは別namespaceである。

``` python
AI_READING_V2_CLAIM_TYPES = (
    "practical",
    "astrology",
    "luck_astrology",
)
```

Modelは各blockの意図するtextについて`claim_type`を宣言する。trusted codeは`claim_type`を推測、
生成、補完、変更してはならない。Generator v2はdeclaration、reference、location、crosswalkだけを
structural / semantic validationし、textに対するkeyword、NLP、heuristic classificationを行っては
ならない。declarationと実際のtext意味の一致は22.14のQuality Gate v2 responsibilityとする。

`claim_type = "practical"`は次をすべてMUSTとする。

-   `source_fact_codes == []`かつ`source_components == []`とする。
-   `warnings`と`uncertainty`はtrusted catalog内の既存IDを選択できるが、fact groundingとして
    扱ってはならない。
-   textにastrology claim、engine-calculated claim、luck-valued claimを含めてはならない。

`claim_type = "astrology"`は次をすべてMUSTとする。

-   `source_fact_codes`に1件以上のvalidated Reading Context v2 fact codeを持つ。
-   `source_components`はoptionalとするが、`luck_pillars`、`current_luck`、`annual_luck`、
    `integrated_luck`を含めてはならない。
-   component-only groundingを禁止する。`source_components`はcertainty / provenance traceの補助であり、
    astrology value sourceではない。
-   `warnings`と`uncertainty`はtrusted catalog内の既存IDをoptionalに選択できる。

`claim_type = "luck_astrology"`は次をすべてMUSTとする。

-   `source_components`に22.12のallowed luck componentを1件以上持つ。
-   block location、selected luck component、trusted `luck_value_source_entry`が22.12のcrosswalkへ
    exact matchしなければならない。
-   `source_fact_codes`はoptionalとし、存在する場合はnon-luck contextual groundingだけを補助する。
-   non-luck `source_components`およびtrusted warning / uncertainty IDはoptionalとする。
-   Generatorはtextからluck claimを推測せず、declared `claim_type`とcrosswalkだけを検証する。

Available `claim_type` enumはtrusted codeがrequestごとに次の固定順で構築する。

1.  `practical`は常に含める。
2.  `astrology`は`trusted_catalogs.fact_codes`が1件以上の場合だけ含める。
3.  `luck_astrology`は`trusted_catalogs.luck_value_sources`が1件以上の場合だけ含める。

fact catalogがemptyなら`astrology`を除外し、luck value source catalogがemptyなら
`luck_astrology`を除外する。両方がemptyの場合は`["practical"]`とする。claim type enum自体を
emptyにしてはならず、`enum: []`を使用してはならない。location固有ruleおよびper-type reference
cardinalityはJSON Schema validation後のsemantic validationで検証する。

#### 22.4.2 Claim type location matrix

各`grounded_text_block` locationで許可するclaim typeを次に固定する。`NO`のtypeをmodelが選択した
payloadはsemantic-invalidとする。

| block location | `practical` | `astrology` | `luck_astrology` |
|---|:---:|:---:|:---:|
| top-level `summary` | YES | YES | NO |
| `core_personality` / `career` / `wealth` / `relationships` / `health` / `advice` の`summary`・`detail` | YES | YES | NO |
| 上記6 sectionの`evidence[]`・`interpretation[]` | NO | YES | NO |
| 上記6 sectionの`advice[]` | YES | YES | NO |
| `current_luck`の`summary`・`detail`・`advice[]` | YES | YES | YES |
| `current_luck`の`evidence[]`・`interpretation[]` | NO | YES | YES |
| `future_flow` non-yearlyの`summary`・`detail`・`advice[]` | YES | YES | YES |
| `future_flow` non-yearlyの`evidence[]`・`interpretation[]` | NO | YES | YES |
| `future_flow.yearly[]`の`summary`・`detail` | YES | YES | YES |
| `consultation_answer` | YES | YES | NO |

`evidence`と`interpretation`はempty collectionにできるため、sourceが利用できない場合の
`practical` fallbackを許可しない。`luck_astrology`がYESのlocationでも、22.12の対応するcrosswalk
entryが存在しなければ使用できない。

`future_flow`以外の7 sectionは、次のfieldだけをすべてREQUIREDとして持つ。

``` json
{
  "section_id": "core_personality",
  "title": "本質・性格",
  "facts": ["day_master.stem"],
  "summary": {
    "text": "...",
    "claim_type": "astrology",
    "source_fact_codes": ["day_master.stem"],
    "source_components": ["five_elements"],
    "warnings": [],
    "uncertainty": []
  },
  "detail": {
    "text": "...",
    "claim_type": "astrology",
    "source_fact_codes": ["day_master.stem"],
    "source_components": ["five_elements"],
    "warnings": [],
    "uncertainty": []
  },
  "evidence": [
    {
      "text": "...",
      "claim_type": "astrology",
      "source_fact_codes": ["day_master.stem"],
      "source_components": ["five_elements"],
      "warnings": [],
      "uncertainty": []
    }
  ],
  "interpretation": [
    {
      "text": "...",
      "claim_type": "astrology",
      "source_fact_codes": ["day_master.stem"],
      "source_components": ["five_elements"],
      "warnings": [],
      "uncertainty": []
    }
  ],
  "advice": [
    {
      "text": "...",
      "claim_type": "astrology",
      "source_fact_codes": ["day_master.stem"],
      "source_components": [],
      "warnings": [],
      "uncertainty": []
    }
  ],
  "warnings": [],
  "uncertainty": []
}
```

-   `section_id` は上記8 IDのいずれかとし、重複・不足・追加を禁止する。
-   `title` は上記mappingに完全一致しなければならない。
-   `facts` は AI-authored sentence ではなく、input に存在する fact code の配列とする。
-   top-level `summary`、section `summary` / `detail`、`evidence` / `interpretation`の各entry、
    `advice`の各entryは`grounded_text_block`とする。
-   `warnings` と `uncertainty` は、22.10 の trusted top-level catalog 内で
    resolve可能なID stringだけを保持する。
-   section-level singular `judgment_status` は追加しない。一つの section が異なる
    canonical status の複数 component を参照できるためである。
-   `future_flow`だけは22.12の`yearly`を追加REQUIRED fieldとして持つ。他の7 sectionに
    `yearly`を置くことを禁止する。

Section-level `facts`のownershipは次に固定する。

1.  trusted prompt builderが`reading_context_v2.facts[].code`からallowed fact-code dynamic
    enumを構築する。
2.  modelは各sectionの`facts`をそのenumからSELECTできる。
3.  modelは新しいfact codeをINVENTしてはならない。
4.  trusted validatorはsection `facts`の全codeがinputに存在することを確認・resolveする。
5.  trusted final wrapperはvalidated fact codesだけを保持する。
6.  trusted codeはmodelが選択しなかったfactを意味推測によって追加・補完してはならない。
7.  section `facts`はsection-level index / overviewであり、individual `grounded_text_block`の
    `source_fact_codes`を代替しない。
8.  block内のclaim groundingは、そのblock自身の`source_fact_codes` / `source_components`で
    検証する。fact codeがsection `facts`に存在するだけではblockのgrounding成立とみなさない。

Non-luck astrology valueのsource of truthは`reading_context_v2.facts`だけとする。`source_components`
単独ではvalue groundingとしてinvalidであり、Common Judgment Metadataはcertainty / provenance traceを
補助するだけでastrology value sourceにはならない。raw `chart_result`または第三のvalue sourceを
AI Reading v2 inputへ追加してはならない。v1.2ではfact化されていないmonth command、roots、relationsの
詳細値をAI Reading value claimに使用しない。将来必要な場合は別versionでReading Context fact追加または
explicit crosswalkをreviewし、本versionへnon-luck crosswalkを追加してはならない。

`claim_type`からsection `facts`を自動生成してはならない。trusted codeはmodelが選択しなかったfactまたは
component referenceを推測して追加・補完してはならない。

### 22.5 Output contract

successful AI Reading v2 wrapper は次の top-level field をすべて REQUIRED とする。
field omissionを禁止する。

``` json
{
  "schema_version": "ai_reading_v2",
  "engine_version": "1.2",
  "summary": {
    "text": "",
    "claim_type": "practical",
    "source_fact_codes": [],
    "source_components": [],
    "warnings": [],
    "uncertainty": []
  },
  "sections": [
    {
      "section_id": "core_personality",
      "title": "本質・性格",
      "facts": [],
      "summary": {"text": "", "claim_type": "practical", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "detail": {"text": "", "claim_type": "practical", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "evidence": [],
      "interpretation": [],
      "advice": [],
      "warnings": [],
      "uncertainty": []
    },
    {
      "section_id": "career",
      "title": "仕事・適職",
      "facts": [],
      "summary": {"text": "", "claim_type": "practical", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "detail": {"text": "", "claim_type": "practical", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "evidence": [],
      "interpretation": [],
      "advice": [],
      "warnings": [],
      "uncertainty": []
    },
    {
      "section_id": "wealth",
      "title": "金運",
      "facts": [],
      "summary": {"text": "", "claim_type": "practical", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "detail": {"text": "", "claim_type": "practical", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "evidence": [],
      "interpretation": [],
      "advice": [],
      "warnings": [],
      "uncertainty": []
    },
    {
      "section_id": "relationships",
      "title": "恋愛・人間関係",
      "facts": [],
      "summary": {"text": "", "claim_type": "practical", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "detail": {"text": "", "claim_type": "practical", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "evidence": [],
      "interpretation": [],
      "advice": [],
      "warnings": [],
      "uncertainty": []
    },
    {
      "section_id": "health",
      "title": "健康傾向",
      "facts": [],
      "summary": {"text": "", "claim_type": "practical", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "detail": {"text": "", "claim_type": "practical", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "evidence": [],
      "interpretation": [],
      "advice": [],
      "warnings": [],
      "uncertainty": []
    },
    {
      "section_id": "current_luck",
      "title": "現在の運勢",
      "facts": [],
      "summary": {"text": "", "claim_type": "practical", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "detail": {"text": "", "claim_type": "practical", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "evidence": [],
      "interpretation": [],
      "advice": [],
      "warnings": [],
      "uncertainty": []
    },
    {
      "section_id": "future_flow",
      "title": "今後の流れ",
      "facts": [],
      "summary": {"text": "", "claim_type": "practical", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "detail": {"text": "", "claim_type": "practical", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "evidence": [],
      "interpretation": [],
      "advice": [],
      "warnings": [],
      "uncertainty": [],
      "yearly": []
    },
    {
      "section_id": "advice",
      "title": "総合アドバイス",
      "facts": [],
      "summary": {"text": "", "claim_type": "practical", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "detail": {"text": "", "claim_type": "practical", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "evidence": [],
      "interpretation": [],
      "advice": [],
      "warnings": [],
      "uncertainty": []
    }
  ],
  "consultation_answer": null,
  "warnings": [],
  "uncertainty": [],
  "source_contracts": {
    "reading_context": {
      "schema_version": "reading_context_v2",
      "method": "reading_context_v2",
      "version": "reading_context_v2",
      "status": "ready_for_ai_reading"
    },
    "judgment_metadata": {
      "schema_version": "common_judgment_metadata_v1"
    }
  },
  "disclaimer": "本鑑定は八雲式四柱推命エンジンの計算結果に基づく参考情報です。将来の出来事を保証するものではなく、医療・法律・投資その他の専門的判断を代替するものではありません。重要な意思決定は、必要に応じて適切な専門家へご相談ください。",
  "validation": {
    "valid": true,
    "errors": [],
    "missing_required_fields": [],
    "unknown_fields": []
  },
  "method": "openai_responses_api_v2",
  "version": "ai_reading_v2",
  "status": "completed"
}
```

-   `engine_version` は validated Reading Context input から exact projection する。
-   `sections` は22.4の exact eight sectionsをexactly 8件、同一順序で持つ。空配列、
    subset、追加sectionはsuccessful wrapperとしてinvalidとする。上記JSONは8件すべてを
    含むvalid structural exampleであり、`sections: []`をplaceholderとして使用しない。
-   `consultation_answer` は REQUIRED conditional fieldとし、consultation が `null` の場合は
    `null` とする。consultation inputが存在する場合は`null`を禁止し、次のexact objectをREQUIREDとする。

``` json
{
  "text": "...",
  "claim_type": "practical",
  "source_fact_codes": [],
  "source_components": [],
  "warnings": [],
  "uncertainty": []
}
```

非null `consultation_answer`では`text`と`claim_type`をmodel-authoredとする。source arraysは22.6の
dynamic enum、`warnings` / `uncertainty`は22.10のcatalog IDだけを許可し、trusted validatorが
すべてresolveする。consultation自体をastrology fact sourceとしてはならない。`claim_type = "astrology"`
は少なくとも一つのfact codeを必要とし、`claim_type = "practical"`は両source arraysをemptyとする。
`claim_type = "luck_astrology"`は禁止する。practical textをengine calculationとして表現してはならない。

-   top-level `summary`は`grounded_text_block`とする。
-   `warnings` と `uncertainty` は trusted code が input から source contract、
    resolvable source path、raw valueを保持して投影する配列とする。deduplicate、
    normalize、相互変換、modelによる追加を禁止する。
-   `source_contracts` は二つの input contract identity の exact projection とし、
    source metadata をmergeしない。
-   `disclaimer`は次のnormative constantとexact string matchしなければならない。

``` text
AI_READING_V2_DISCLAIMER = "本鑑定は八雲式四柱推命エンジンの計算結果に基づく参考情報です。将来の出来事を保証するものではなく、医療・法律・投資その他の専門的判断を代替するものではありません。重要な意思決定は、必要に応じて適切な専門家へご相談ください。"
```

この文面は将来保証の禁止、医療・法律・投資に関する非断定、重要判断での専門家相談を
customer-facingな日本語で示す。trusted codeがexact constantをattachし、modelは生成・変更
してはならない。validatorはexact string matchを検証する。v1.2では`language="ja"`だけを
supportし、localizationを行わない。`tone`はこのconstantへ影響しない。disclaimerには個別の
astrology fact、鑑定結果、consultation内容を含めてはならない。
-   `validation` は trusted validator の deterministic report とする。
-   `method` は successful v2 generation method `openai_responses_api_v2`、
    `status` は generation lifecycle の `completed` とする。これは Common Judgment の
    canonical judgment statusとは別 namespaceである。

### 22.6 Trusted fields and model-authored fields

Model がauthorできる自然言語は、validated prompt/schemaが許可する次のtextに限定する。

-   top-level `summary.text`
-   section `summary.text` / `detail.text`
-   evidence / interpretation の `text`
-   advice blockの`text`
-   consultation answer text（consultation が存在する場合）
-   `future_flow.yearly[].summary.text` / `detail.text`

自然言語以外では、modelは各`grounded_text_block`の`claim_type`をavailable claim type enumから宣言し、
section `facts`、各`grounded_text_block`の`source_fact_codes` / `source_components`、および
section/block/consultationのwarning ID / uncertainty IDをtrusted dynamic enumからSELECTできる。
これらはmodelによる新規reference生成ではない。

Trusted code は次をattachまたはprojectしなければならない。

-   `schema_version`、`engine_version`、`method`、`version`、`status`
-   exact section IDs と fixed titles
-   `source_contracts`
-   top-level warning / uncertainty catalogとそのID
-   `validation`
-   `future_flow` の year と ordering
-   fixed disclaimer

fact/component referenceの選択責任は次の順序に固定する。

1.  trusted prompt builderがvalidated inputsからallowed `source_fact_codes`とallowed
    `source_components`のdynamic enumを構築する。fact enumには実在する
    `reading_context_v2.facts[].code`だけを含める。component enumには§4のregistered recordの
    うちowner validationを通過し、`source_path`がnon-nullでregistered pathとexact matchする
    componentだけを含める。prompt builderはraw `chart_result`へ再resolveしない。missing sourceの
    placeholder recordおよび`month_command` aggregate containerを含めない。fact enumは
    `reading_context_v2.facts`のinput array順、component enumは§4のfrozen registry順を保持する。
2.  modelはそのenumからreferenceをSELECTできる。
3.  modelは新しいreferenceをINVENTできない。
4.  trusted validatorがmodel-selected referenceの存在を確認し、inputへresolveする。
5.  trusted final wrapperはvalidated referenceだけを保持する。
6.  trusted codeは、modelがどのfact/componentを意味したかを推測してreferenceを生成、
    選択、補完してはならない。
7.  warning ID / uncertainty IDだけは例外とし、trusted codeが22.10のcatalog projection時に
    deterministicにassignする。modelは既存IDのdynamic enumからSELECTするだけとする。

したがって、trusted codeによるreferenceの`attach`はmodel-selected valueのvalidation後の
採用を意味し、trusted code自身による意味上のreference選択または生成を意味しない。

dynamic enumのJSON Schema表現は次に固定する。allowed valueが1件以上ある場合は、そのtrusted
valueだけを`items.enum`へ置く。

``` json
{
  "type": "array",
  "items": {
    "type": "string",
    "enum": ["allowed_value"]
  },
  "uniqueItems": true
}
```

allowed valueが0件の場合は、empty arrayだけを許可する次のschemaとする。

``` json
{
  "type": "array",
  "items": {
    "type": "string"
  },
  "minItems": 0,
  "maxItems": 0,
  "uniqueItems": true
}
```

`enum: []`を使用してはならない。このruleはfact code、source component、warning ID、uncertainty IDの
全dynamic enumへ同じように適用する。exact schema constructionは22.2.3をsource of truthとする。

### 22.7 Judgment status writing policy

Common Judgment Metadata の canonical `status` は文章表現に次の制約を与える。

-   `resolved`: current engine judgment を通常表現できる。ただし未来・傾向を保証表現にしない。
-   `provisional`: 限定表現を必須とし、documented limitationを保持する。
-   `uncertain`: 関連するuncertaintyを明示し、単一の断定結論を避ける。
-   `unsupported`: 占術解釈を補完しない。current engineではsupportされていない旨だけを
    表現できる。
-   `null`: `resolved` として扱わない。direct factの引用は可能だが、そのcomponentだけを
    根拠にcertainty claimまたはcomponent-derived interpretationを生成しない。

複数componentを参照するsentenceは、参照したすべてのcomponentのpolicyを満たさなければ
ならない。AIまたはtrusted codeが新しいstatus rankingや「strictest status」を計算しては
ならない。`component_status` はtrace informationに限定し、canonical `status` をoverride
してはならない。

### 22.8 Three-pillar / unknown birth time policy

`birth_time_status.known == false` の場合、次をMUSTとする。

-   hour pillarを推定しない。
-   hour-derived interpretationを生成しない。
-   `known_pillars_only` scopeを尊重する。
-   strength confidence capを尊重し、certaintyを強化しない。
-   applicable uncertaintyを保持し、文章から消さない。
-   estimated luck timingをestimatedとして表現する。
-   `internal_reference_time` を出生時刻として表現しない。
-   missing root / element / relationを、complete chartにおける不存在と断定しない。
-   hour-dependent relationの不存在を推定しない。
-   unknown birth timeの影響を受けるclaimは、resolve可能な applicable uncertainty
    referenceを持たなければならない。

このpolicyはGC10 three-pillar Reading Context v2 contractと整合しなければならない。

### 22.9 Grounding / source policy

1.  `claim_type = "astrology"`のnon-luck astrology value sourceは、validated inputの
    `reading_context_v2.facts`だけとする。そのblockは`reading_context_v2.facts[].code`へresolveする
    `source_fact_codes`を1件以上持たなければならない。`source_components`だけではvalue groundingを
    成立させてはならない。
2.  `claim_type = "luck_astrology"`だけが22.12のexplicit crosswalkに限定したtrusted factual source
    exceptionを使用できる。`claim_type = "practical"`はfact/component referenceを持ってはならない。
3.  fact code / component referenceは、inputからtrusted codeが構築したdynamic enumで
    制約しなければならない。
4.  source referenceはinput内でresolve可能でなければならない。Common Judgment Metadataのcomponent
    referenceはcertainty/provenance supportであり、non-luck astrology value sourceではない。
5.  `interpretation_hints` はtopic/focusを案内できるが、新しいtruthを作れない。
6.  Common Judgment Metadataはcertaintyを制御するが、新しいastrology valueを作れない。
7.  warnings / uncertaintyをfactへ変換してはならない。
8.  consultationはemphasis / practical adviceにだけ使用する。
9.  general practical adviceをengine calculationとして表現してはならない。
10. missing sourceを補完せず、missingのまま扱う。
11. top-level summaryおよびsectionのsummary、detail、evidence、interpretation、adviceに
    含まれるastrology claimは、それを含む`grounded_text_block`の`claim_type`とreferenceでtrace
    できなければならない。別blockのdeclaration/referenceを暗黙に流用してはならない。
12. 22.12のluck exceptionは`reading_context_v2.facts` allowlist全体を拡張せず、luck以外の
    structured Reading Context fieldを新しいfactual sourceとして許可しない。

### 22.10 Evidence, warnings, uncertainty

次の意味を混同してはならない。

-   Common Judgment `evidence`: raw calculation evidence。
-   AI Reading sectionのevidence `text`: customer-facing explanation。
-   provenance: input contractのsource path / source metadata。
-   Golden / human verification evidence: runtime AI Reading contract外のverification artifact。

AI Reading evidence textはvalidated source referenceを持たなければならず、新しいcalculation
evidenceとして扱ってはならない。

Top-level `warnings` は、exactly次のshapeのwarning entryだけを持つarrayとする。

``` json
{
  "warning_id": "warning_0001",
  "source_contract": "reading_context_v2",
  "source_path": "warnings[0]",
  "value": "..."
}
```

Top-level `uncertainty` は、exactly次のshapeのuncertainty entryだけを持つarrayとする。

``` json
{
  "uncertainty_id": "uncertainty_0001",
  "source_contract": "common_judgment_metadata_v1",
  "source_path": "components.strength.uncertainty[0]",
  "value": {
    "code": "...",
    "category": "...",
    "status": "...",
    "severity": "...",
    "scope": [],
    "message": "..."
  }
}
```

-   `source_contract`は`reading_context_v2`または`common_judgment_metadata_v1`だけを許可する。
-   `source_path`は指定source contract内のraw valueへexactly resolveしなければならない。
-   `value`はresolved raw warning stringまたはstructured uncertainty objectのexact deep copyとする。
-   warning IDは`warning_0001`、uncertainty IDは`uncertainty_0001`から始まる4桁zero-padded
    independent sequenceとし、trusted codeがdeterministically assignする。同一catalog内のID
    collisionを禁止する。modelはIDを生成・変更してはならない。
-   sectionおよびgrounded text blockの`warnings`はwarning ID stringだけ、`uncertainty`は
    uncertainty ID stringだけを持つ。raw valueの複製を禁止し、全IDはtop-level catalogへ
    exactly one resolveしなければならない。
-   raw valueの順序変更、deduplicate、normalize、warning/uncertainty間の相互変換、意味の追加を
    禁止する。
-   warning / uncertainty referenceはfact groundingではなく、`claim_type`を推測、変更、または
    自動分類する材料として使用してはならない。`practical` blockも既存trusted IDを参照できる。

Catalogのcanonical traversal orderは次に固定する。

1.  `reading_context_v2` top-level `warnings`をraw array順にwarning catalogへ投影する。
2.  `reading_context_v2` top-level `uncertainty`をraw array順にuncertainty catalogへ投影する。
3.  Common Judgment recordsを、§4の初期source registryと完全に同じ次の順で一度だけ走査する。
    `five_elements`、`month_command.basic`、`month_command.weighted`、
    `month_command.seasonal`、`month_command.integrated`、`roots`、`strength`、`relations`、
    `pattern`、`useful_gods`、`luck_pillars`、`current_luck`、`annual_luck`、`integrated_luck`。
    各record内では`warnings`、`uncertainty`の順に参照し、それぞれのraw array順で対応catalogへ
    投影する。`month_command` aggregateはgroup containerであるためcatalog sourceにせず、
    nested 4 componentsだけを上記位置・順序で走査する。

この走査順はstable ID assignmentのためだけに使用し、新しい占術priorityを意味しない。
warning IDとuncertainty IDはそれぞれ独立に連番を進める。

### 22.11 AI MUST NOT CALCULATE

AI Reading v2において、AIおよびAI Reading layerは次を行ってはならない。

-   四柱、蔵干、通変星、十二運の再計算
-   五行scoreの再計算
-   身強身弱、格局、用神の再判定
-   大運、歳運、integrated luckの再計算
-   missing hourの推定
-   true solar time、timezone correction、location correctionの推定
-   sourceにない吉凶判定の生成
-   confidence / certaintyのupgrade
-   consultationからの占術結果生成
-   sourceにないfact、evidence、source path、fact code、component nameの生成
-   一要素だけからの人物断定
-   将来の保証
-   医療・法律・投資等の断定
-   不安を煽る表現
-   「必ず」「絶対」等の根拠なき決定表現

AIのroleは、validated engine truthを `organize`、`verbalize`、`explain` することだけとする。

文章生成順序は次を維持する。

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

### 22.12 Future flow / luck

#### 22.12.1 Trusted luck value grounding

luckに限り、次のexplicit crosswalkで指定されたReading Context v2 structured pathを、factsとは
別のtrusted factual sourceとして許可する。astrology valueのsource of truthはReading Contextで
あり、Common Judgment Metadataはvalue sourceではない。Common Judgment Metadataはcomponentの
certainty、warnings、uncertainty、provenance metadataだけを提供する。

`current_luck` sectionのcrosswalkは次に固定する。

| source_component | context_path |
|---|---|
| `luck_pillars` | `luck.luck_pillars` |
| `current_luck` | `luck.current_luck` |
| `annual_luck` | `luck.annual_luck` |
| `integrated_luck` | `luck.integrated_luck` |

`future_flow`のyear index `i`のcrosswalkは次に固定する。

| source_component | context_path |
|---|---|
| `current_luck` | `luck.five_year_luck[i].current_luck` |
| `annual_luck` | `luck.five_year_luck[i].annual_luck` |
| `integrated_luck` | `luck.five_year_luck[i].integrated_luck` |

`trusted_catalogs.luck_value_sources`のcanonical orderは、最初に`current_luck` crosswalkを上表順で
走査し、次に`future_flow`をtrusted `five_year_luck` orderで走査し、各year内をfuture-flow crosswalkの
上表順で走査する。利用不可entryは追加せず、残るentryのrelative orderを変更しない。

`luck_value_source_entry`はexactly次の4 fieldを持つ。

| field | type / rule |
|---|---|
| `section_id` | `"current_luck"` \| `"future_flow"` |
| `year` | integer \| null。`current_luck`ではnull、`future_flow`ではtrusted year |
| `source_component` | `"luck_pillars"` \| `"current_luck"` \| `"annual_luck"` \| `"integrated_luck"` |
| `context_path` | 上記crosswalkとexact matchするresolvable Reading Context path |

trusted prompt builderは、対応するCommon Judgment Metadata recordが利用可能な場合だけ
`luck_value_source_entry`をcatalogへ追加する。利用可能とは、owner validationを通過し、recordの
`source_path`がnon-nullでregistered pathとexact matchし、required `method`を持ち、対応する
Reading Context pathのvalueがnon-nullであることをいう。対応metadata recordが利用不可、または
Reading Context pathがmissing/nullの場合、そのluck pathをmodel factual sourceとして許可しない。

`claim_type = "luck_astrology"`のblockは、次の三条件をすべて満たす場合だけvalidとする。

1.  claimを含む`grounded_text_block.source_components`がallowed luck componentを持つ。
2.  blockのlocation/scopeにexact matchする`luck_value_source_entry`が存在する。
3.  同entryの`context_path`が本節のallowed Reading Context v2 luck pathへresolveする。

`luck_astrology`を許可するscopeは、`current_luck` section、`future_flow` section、
`future_flow.yearly[i]`のexactly三つに限定する。top-level `summary`、`core_personality`、`career`、
`wealth`、`relationships`、`health`、`advice`、`consultation_answer`ではluck structured-path exceptionを
禁止する。これらのscopeでnon-luck astrology factual claimを行う場合は`claim_type = "astrology"`と
22.4.1のfact grounding ruleを使用し、luck structured pathをvalue sourceとしてはならない。

`current_luck` sectionの`summary`、`detail`、各`evidence`、各`interpretation`、およびastrology-dependent
`advice` blockで`claim_type = "luck_astrology"`を使う場合、各model-selected luck `source_component`はcurrent-luck
crosswalkのexactly one top-level Reading Context luck pathへresolveしなければならない。

`future_flow` sectionのnon-yearly `summary`、`detail`、各`evidence`、各`interpretation`、および
astrology-dependent `advice` blockで`claim_type = "luck_astrology"`を使う場合、選択された`source_component`について
`trusted_catalogs.luck_value_sources`に存在するfuture-flow全year entryのcontext pathをtrusted year順の
ordered setとしてresolveしなければならない。modelはそのordered setのsubset yearを指定できない。
特定yearのclaimは対応する`future_flow.yearly[i]` blockに置かなければならない。
`five_year_luck=[]`の場合、future-flow non-yearly blockはluck exceptionを使用できない。

`future_flow.yearly[i]`の`summary`または`detail` blockで`claim_type = "luck_astrology"`を使う場合、trusted positional
index `i`とtrusted attached yearによって、選択された`source_component`をexactly one
`luck.five_year_luck[i].<component>` pathへresolveする。modelはyear、index、pathを返してはならない。

`source_components`はglobal allowed enumであるが、そのmembershipだけでluck groundingをvalidとしては
ならない。validatorおよびQuality Gateはblock scope、source component、trusted
`luck_value_source_entry`のcrosswalk一致を必ず検証し、scopeに対応するentryがなければinvalidとする。
non-luck source componentはcertainty/provenance supportとして使用できるが、単独ではnon-luck value groundingを
成立させない。

yearはtrusted attachmentとする。modelおよびAI Reading layerはluck valueを再計算、再分類、normalize、
補完または推測してはならない。`target_datetime`をbirth timeとして扱わず、`target_datetime`自体から
新しいastrology factを作ってはならない。このexceptionは§20のfacts allowlist、Reading Context v2
schema、またはCommon Judgment Metadataのevidence/value semanticsを変更しない。

#### 22.12.2 Yearly output

`future_flow` で扱う yearとorderingは、
`reading_context_v2.luck.five_year_luck` からtrusted inputとして取得する。modelはyearを
生成、変更、追加、並べ替えしてはならない。trusted codeがfinal outputへyearとorderingを
attachし、modelは各固定yearに対する文章だけを生成する。inputにないyearを補完してはならない。

`future_flow` sectionだけは、22.4の共通fieldに加えて`yearly`をREQUIREDとする。`yearly`は
exactly次のentry shapeを持つarrayとする。

``` json
{
  "year": 2026,
  "summary": {
    "text": "...",
    "claim_type": "practical",
    "source_fact_codes": [],
    "source_components": [],
    "warnings": [],
    "uncertainty": []
  },
  "detail": {
    "text": "...",
    "claim_type": "practical",
    "source_fact_codes": [],
    "source_components": [],
    "warnings": [],
    "uncertainty": []
  }
}
```

-   `year`はintegerとし、trusted codeがinputからattachする。modelはyearを生成、変更、追加、
    削除、並べ替えしてはならない。
-   `summary`と`detail`はそれぞれ22.4のexact `grounded_text_block`とする。model-authoredなのは
    各blockの`text`と`claim_type`であり、yearly entry全体を別のtraceability unitとして扱ってはならない。
-   各blockの`source_fact_codes` / `source_components`は22.6のdynamic enumからmodelがSELECTし、
    trusted validatorがresolveする。modelはreferenceをINVENTできず、trusted codeは意味を推測して
    referenceを生成・補完しない。
-   各blockの`warnings` / `uncertainty`は22.10のtrusted catalog IDだけを許可し、全IDを
    trusted validatorがresolveする。unknown birth timeがyearly claimへ影響する場合は、該当する
    block自身がapplicable uncertainty IDを持たなければならない。
-   `summary`と`detail`の各blockは22.4.1のper-type reference ruleおよび22.4.2のlocation matrixを
    満たさなければならない。`luck_astrology`では対応するyear/index crosswalkを満たすluck componentが
    1件以上必要であり、`astrology`ではfact codeが1件以上必要である。
-   `yearly`の件数、year value、orderingは`reading_context_v2.luck.five_year_luck`とexact match
    しなければならない。同inputがemptyの場合は`yearly=[]`とする。inputにないyearを禁止する。
-   他の7 sectionに`yearly` fieldを置くことを禁止し、unknown-field rejectionの対象とする。

### 22.13 Validator contract

#### 22.13.1 Prompt-specific prerequisite validation

owner validationの後、catalog constructionより前に次のprompt-specific prerequisite validatorを
実行する。

``` python
validate_ai_reading_prompt_inputs_v2(
    reading_context,
    judgment_metadata,
) -> dict[str, Any]
```

いずれかのinputがMappingでない場合は`TypeError`をraiseする。両inputがMappingであるがinvalidな
場合は例外ではなく、exactly次のdeterministic reportを返す。validな場合は`valid=true`、三つの
arrayをemptyとして同じshapeを返す。

``` json
{
  "valid": false,
  "errors": [],
  "missing_required_fields": [],
  "unknown_fields": []
}
```

`build_ai_reading_request_v2()`はこのreportがinvalidの場合に`ValueError`をraiseし、invalid requestを
返してはならない。prerequisite validatorは次を検証する。

-   Reading Context v2とCommon Judgment Metadataの両owner validator reportがvalidであること。
-   Reading Context top-level `warnings`がarray of stringであること。
-   Reading Context top-level `uncertainty`の各entryがexactly`code`、`category`、`status`、
    `severity`、`scope`、`message`を持つstructured objectであること。field typeとvocabularyは
    §4および`engine/judgment_schema.py`の既存contractと一致し、`message`はstringまたはnull、
    `scope`はarray of stringとする。
-   `reading_context.luck`がMappingであり、`luck.five_year_luck`がREQUIRED arrayであること。
    empty arrayはvalidとする。
-   `five_year_luck`の各entryがMappingで、integer `year`を持ち、yearが重複しないこと。
-   各`five_year_luck` entryが`current_luck`、`annual_luck`、`integrated_luck`を持ち、各valueが
    Mappingまたはnullであること。
-   22.12のtop-level luck crosswalk pathが存在し、各valueがMappingまたはnullであること。
-   fact valueを再計算せず、owner-validated Reading Context内のvalue/codeだけを使用すること。
-   component compatibilityをCommon Judgment Metadataのfrozen registry、registered path、record
    schemaだけに対して検証し、raw `chart_result`へresolveしないこと。
-   `engine_version`がstringまたはnullであること。fallbackまたはversion inferenceを禁止する。

このvalidatorはowner validatorの責務を置換せず、占術計算、missing valueの補完、normalization、
input mutationを行ってはならない。

#### 22.13.2 Request and final validation lifecycle

AI Reading v2のvalidation lifecycleは次の非循環順序に固定する。

1.  `reading_context_v2`をowner validatorで検証する。
2.  `common_judgment_metadata_v1`をowner validatorで検証する。
3.  `validate_ai_reading_prompt_inputs_v2()`でprompt-specific prerequisiteを検証する。
4.  trusted warning / uncertainty catalog、fact/component dynamic enum、luck value source catalog、
    available claim type enumを構築し、trusted attachmentsを構築する。
5.  22.2.3に従ってexact `model_output_schema`を構築する。
6.  22.2.1のexact system constantとcanonical user serializationからexact `messages`を構築する。
7.  exact `messages`と`model_output_schema`を使用してmodelを呼び出す。
8.  model responseを22.13.3のDraft 2020-12 policyでstrict JSON Schema validationする。
9.  schema-valid model payloadをsemantic validationし、claim typeごとのreference rule、location matrix、
    fact resolution、component resolution、luck block scope crosswalk、warning ID、uncertainty ID、
    section count、future year countを確認する。text意味のNLP判定は行わない。
10. validated model-owned fieldsへtrusted catalog、source contracts、engine version、fixed section ID/title、
    future year/order、disclaimer、schema/version/method/statusをdeterministically attachして、
    `validation` fieldをまだ持たないfinal candidateを構築する。
11. final candidateを検証し、deterministic validation reportを一度だけ生成する。
12. そのreportを`validation` fieldへattachする。
13. `validation` field自体のexact shape/typeをschema-checkし、report内容を再生成しない。

final candidateのvalidation対象から`validation` fieldを除外してreportを一度だけ作ることで、
self-referential validationおよび無限loopを禁止する。successful wrapperではreportの`valid`が
`true`、他の三arrayがemptyでなければならない。reportがinvalidの場合、そのcandidateを
successful AI Reading v2 wrapperとして返してはならない。

AI Reading v2 validatorは少なくとも次を検証する。

-   exact `schema_version` / `version` / required top-level fields
-   unknown field rejection
-   exact eight section IDs、順序、重複、不足
-   fixed title mapping
-   `grounded_text_block`のexact six-field shape、available `claim_type`、per-type reference rule、
    location matrix
-   fact-code existence
-   registered component-reference existence
-   luck value source catalogのexact crosswalk、metadata availability、Reading Context path resolution
-   warning / uncertainty catalogのexact shape、stable ID、canonical traversal order、source path resolution
-   section/block/consultationのwarning ID / uncertainty ID resolution
-   nonnull consultation answerのexact shape
-   trusted fieldとmodel-authored fieldのboundary
-   `future_flow.yearly`のexact shape、year / ordering integrity、および他sectionでの`yearly`禁止

validatorは占術計算、score再計算、status再判定、missing data補完を行ってはならない。
invalid outputをtrusted AI Reading v2 wrapperとして返してはならない。

#### 22.13.3 Local JSON Schema validation

Local validation dialectはJSON Schema Draft 2020-12、Python implementationは
`jsonschema.Draft202012Validator`に固定する。providerへ渡すschemaとlocal validatorは、いずれも
`ai_reading_request_v2["model_output_schema"]`という同一schema contractを使用しなければならない。
provider固有の`type` / `name` / `strict` wrapperはschema本体とは別transport layerとし、schema本体へ
`$schema` fieldを追加してはならない。

Local structural validationはexactly次の順で行う。

1.  `jsonschema.Draft202012Validator.check_schema(model_output_schema)`を実行する。
2.  同schemaから`jsonschema.Draft202012Validator` instanceを構築し、
    `iter_errors(model_payload)`ですべてのstructural errorを取得する。
3.  errorをinstance JSON pathを第一keyとするdeterministic orderingへ並べる。instance pathは
    `error.absolute_path`、schema pathは`error.absolute_schema_path`の各segmentをRFC 6901 JSON Pointerへ
    変換し（`~`を`~0`、`/`を`~1`へescapeし、array indexはbase-10 integer stringとする）、sort keyをexactly
    `(instance_pointer, schema_pointer, str(validator), message)`とする。
4.  structural validationがPASSした場合だけ22.13.2 step 9のsemantic validationを実行する。

このlocal validationにはPython dependency `jsonschema`が必要である。dependency追加はPrompt v2
Phase 1.1またはGenerator v2 implementation changeとして明示的に行い、本spec clarificationだけで
`requirements.txt`を変更してはならない。

### 22.14 Quality Gate v2 handoff

Quality Gate v2は将来、次の三contractをflattenせず別々に受け取る。

1.  `ai_reading_v2`
2.  `reading_context_v2`
3.  `common_judgment_metadata_v1`

AI Reading v2 outputは、Quality Gate v2が少なくとも次を検証できるstructureを持たなければ
ならない。

-   exact schemaおよびexact section IDs
-   fact-code / component-reference existenceとsource resolution
-   engine value / label contradiction
-   canonical status writing policy
-   unknown-hour restriction
-   warning / uncertainty preservation
-   unsupported numeric claim
-   fabricated evidence / path / reference
-   consultationとastrology calculationの分離
-   future-flow year integrity

Generator v2は`claim_type`のenum membership、typeごとのreference cardinality、22.4.2のlocation matrix、
trusted ID resolution、22.12のluck crosswalk、section/year cardinality、deterministic assembly、および
model declarationのexact preservationを検証する。Generator v2はkeyword、NLP、その他のheuristicで
textを分類してはならない。

Quality Gate v2は`claim_type`と実際のtext意味の一致、astrology claimを`practical`と宣言する偽装、
luck proseを`astrology`または`practical`と宣言する偽装、fact/componentとproseのsemantic relevance、
engine value contradiction、certainty/status wording、unknown-hour-derived prose、unsupported numeric claim、
consultationとastrologyの分離を検証する。Quality Gate v2はGenerator v2のstructural/semantic validationを
代替しない。

`prohibited_claim` findingはAI Reading model outputに含めず、Quality Report v2の責任とする。

### 22.15 Compatibility boundary

AI Reading v2導入時、次を変更してはならない。

-   `engine/reading_context.py`
-   `engine/reading_prompt.py`
-   `engine/reading_generator.py`
-   `engine/reading_quality.py`
-   `engine/reading_repair.py`
-   `engine/reading_product.py`
-   `api/reading_routes.py`
-   `reading_context_v1`
-   `reading_api_v1`
-   `reading_product_v1`
-   existing `ReadingGenerationResult`
-   `tests/golden/v1_1/**`
-   existing v1 AI Contract / Product / Renderer / PDF fixtures

AI Reading v2は新規opt-in moduleとして実装し、v1 consumerを一括切替してはならない。

22.2から22.13のrequest、grounding、validation contractはAI Reading v2 orchestration layerだけの
clarificationである。§20 Reading Context v2 contract、`engine/reading_context_v2.py`、GC03/GC10
Reading Context v2 Golden、`engine/judgment_metadata.py`、§4 Common Judgment Metadata semantics、
v1 pipeline、`tests/golden/v1_1/**`、API、およびastrology calculation ruleを変更しない。

### 22.16 Phased migration

AI Reading v2は次の順に段階導入する。Big Bang migrationを禁止する。

1.  Phase 1: 本`claim_type` / local validator clarificationを含む§22 spec freeze
2.  Phase 2: Prompt v2 Phase 1.1
3.  Phase 3: Prompt v2 targeted / regression tests
4.  Phase 4: new opt-in `reading_generator_v2` implementation
5.  Phase 5: Generator v2 unit / four-pillar / three-pillar tests
6.  Phase 6: Quality Gate v2
7.  Phase 7: Auto-Repair v2
8.  Phase 8: AI Reading v2 Golden after human review
9.  Phase 9: ReadingProduct v2
10. Phase 10: API v2
11. Phase 11: PDF / E2E

Generator v2をPrompt v2 Phase 1.1より先に実装してはならない。Prompt v2 Phase 1.1のexact scopeは次に
限定する。

-   `AI_READING_V2_CLAIM_TYPES`の追加
-   `grounded_text_block`へのrequired `claim_type`追加
-   dynamic available claim type enumの構築
-   `AI_READING_V2_SYSTEM_PROMPT`を22.2.1のclaim declaration instructionへexact同期
-   `model_output_schema`のclaim type property / required list更新
-   canonical message expected testsおよびPrompt v2 testsの更新

Prompt v2 Phase 1.1ではrequest top-level fields、`trusted_catalogs` top-level fields、`model_input` fields、
`AI_READING_V2_USER_PROMPT_PREFIX`、prompt-specific prerequisite validator、既存luck crosswalk、
Reading Context validator、Common Judgment Metadata validatorを変更してはならない。

AI Reading v2はexisting engine outputのvalidation / grounding / verbalization layerであり、
astrology calculation ruleへのimpactは `NONE` とする。

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

### 23.4 Responsibility boundary

Quality Gate v2は完成済みの次の三contractをflattenせず別々に受け取る。

1.  `ai_reading_v2`
2.  `reading_context_v2`
3.  `common_judgment_metadata_v1`

Quality Gate v2は次を行う。

-   trusted field、reference、catalog、year / orderのdefense-in-depth validation。
-   `claim_type`と本文意味の整合性検査。
-   fact / component / luck sourceと本文のsemantic relevance検査。
-   engine value、label、canonical status policy、warning、uncertaintyと本文の整合性検査。
-   prohibited claim、過度な断定、安全性の検査。
-   公開可否のdecisionとfindingをQuality Report v2として返却。

Quality Gate v2は次を行ってはならない。

-   占術再計算、score再計算、status再判定またはmissing value補完。
-   input、AI Reading、本文またはtrusted fieldの変更。
-   本文の修復、`claim_type`の自動変更またはreferenceの自動追加。
-   Common Judgment Metadata statusの新しいranking、優先順位または「strictest status」の計算。
-   raw `chart_result`の第三input化。
-   `source_components`からのastrology valueまたはluck valueの推測。
-   keyword不一致がないことだけをsemantic PASSの根拠にすること。
-   Generator v2のstructural / semantic validationの代替。

Quality Gate v2はAI Reading v2の文章品質と公開可否を判定する層であり、
Generator v2の成功を占術的正しさの保証として扱ってはならない。

Quality Gate v2のpublic entry pointは次に固定する。

``` python
evaluate_ai_reading_quality_v2(
    ai_reading: Mapping[str, Any],
    reading_context: Mapping[str, Any],
    judgment_metadata: Mapping[str, Any],
    *,
    semantic_assessor: SemanticAssessorV2 | None = None,
) -> AIReadingQualityReportV2
```

`AIReadingQualityReportV2`およびfindingを表す`AIReadingQualityFindingV2`はfrozen dataclassとする。
`AIReadingQualityReportV2.to_dict()`は23.6のexact reportをdeep copyで返し、内部stateへのaliasを返さない。

### 23.5 Input validation and trusted identity

各inputがnon-Mappingの場合は`TypeError`とし、Quality Report v2を生成しない。
Mapping inputは次の順序で検査する。

1.  Reading Context v2 owner validation。
2.  Common Judgment Metadata owner validation。
3.  AI Reading v2 final contract validation。
4.  Reading Context v2とCommon Judgment MetadataからPrompt v2 trusted requestを再構築。
5.  再構築したtrusted catalogs / attachmentsとAI Reading v2を照合。
6.  source contracts、engine version、section ID / title、future year / order、disclaimer、
    warning catalog、uncertainty catalogを照合。
7.  sectionおよびblockのfact code、component、warning ID、uncertainty IDを再構築catalogへresolve。
8.  22.12のluck crosswalkとReading Context pathを照合。

Mapping inputがowner-invalidまたはprompt prerequisite-invalidの場合、
`input_contract_invalid` ERROR findingを持つ`fail` reportを返し、semantic assessorを呼び出さない。
個々のcontractがvalidでも、AI Reading v2と検証inputのtrusted identityが一致しない場合は
`input_contract_mismatch`とする。

Mapping inputのinvalid policyは次に固定する。

-   Reading Context v2、Common Judgment Metadata、AI Reading v2を23.5の順序でそれぞれ
    独立に検査し、最初のinvalid contractでfail-fastしない。
-   owner-invalidなReading Context v2またはCommon Judgment Metadataごとに、
    `input_contract_invalid`候補をexactly 1件生成する。
-   AI Reading v2 final contractがinvalidな場合は`input_contract_invalid`ではなく、
    `ai_reading_contract_invalid`候補をexactly 1件生成する。
-   これらのfinding `path`はreport-levelのempty string、`evidence`は該当contractの
    rootを示す`[{"source_contract": <contract>, "path": ""}]`とする。
    `<contract>`はAI Reading v2で`"ai_reading_v2"`、Reading Context v2で
    `"reading_context_v2"`、Common Judgment Metadataで`"common_judgment_metadata_v1"`とする。
-   複数contractがinvalidな場合はすべてのcontract単位候補を生成し、23.12で
    canonical sort / dedupする。owner validatorのerror array順でfinding数を増やさない。
-   Reading Context v2とCommon Judgment Metadataがowner-validだがprompt prerequisite-invalidの
    場合は、`input_contract_invalid`候補をexactly 1件生成する。`path` はempty string、
    `evidence`は両contract rootを指す2 entryとし、23.12の順序にcanonicalizeする。
-   owner validatorの`missing_required_field:path`、`type:path:...`等の独自error stringを
    RFC 6901 JSON Pointerとして転記、変換または保存しない。存在しないfield pathを
    findingまたはevidenceに生成しない。

Quality Gate v2はGenerator v2のprivate helperをimportせず、owner validatorおよび
`build_ai_reading_request_v2()`のpublic contractからtrusted dataを再構築する。
inputはmutation、normalization、completionしない。

### 23.6 Quality Report v2 exact contract

Quality Report v2のidentityは次に固定する。

``` python
AI_READING_QUALITY_REPORT_V2_SCHEMA_VERSION = "ai_reading_quality_report_v2"
AI_READING_QUALITY_REPORT_V2_VERSION = "ai_reading_quality_report_v2"
AI_READING_QUALITY_REPORT_V2_METHOD = "ai_reading_quality_gate_v2"
AI_READING_QUALITY_REPORT_V2_STATUS = "completed"
```

top-level fieldは次の順序のexactly 13 fieldとする。すべてREQUIRED、unknown field禁止。

1.  `schema_version`
2.  `version`
3.  `method`
4.  `status`
5.  `decision`
6.  `blocking`
7.  `human_review_required`
8.  `error_count`
9.  `warning_count`
10. `info_count`
11. `input_contracts`
12. `semantic_assessment`
13. `findings`

``` json
{
  "schema_version": "ai_reading_quality_report_v2",
  "version": "ai_reading_quality_report_v2",
  "method": "ai_reading_quality_gate_v2",
  "status": "completed",
  "decision": "pass",
  "blocking": false,
  "human_review_required": false,
  "error_count": 0,
  "warning_count": 0,
  "info_count": 0,
  "input_contracts": {
    "ai_reading_v2": {
      "schema_version": "ai_reading_v2",
      "version": "ai_reading_v2",
      "method": "openai_responses_api_v2",
      "status": "completed",
      "engine_version": null
    },
    "reading_context_v2": {
      "schema_version": "reading_context_v2",
      "version": "reading_context_v2",
      "method": "reading_context_v2",
      "status": "ready_for_ai_reading"
    },
    "common_judgment_metadata_v1": {
      "schema_version": "common_judgment_metadata_v1"
    }
  },
  "semantic_assessment": {
    "status": "completed",
    "method": "semantic_assessor_method",
    "version": "semantic_assessor_version"
  },
  "findings": []
}
```

top-levelの`schema_version`、`version`、`method`、`status`はnon-empty string、
countはbooleanを含まない0以上のinteger、
`blocking`と`human_review_required`はboolean、`findings`は23.7のexact finding arrayとする。
`decision`は`"pass" | "fail" | "review"`のみとする。

`input_contracts` fieldは上記の順序のexactly 3 fieldを持ち、各nested objectも上記の
field順序を保持する。identity valueはstringまたはnull、`engine_version`はstringまたはnullとする。
owner-valid inputでは各fixed identityがexact matchしなければならない。

Mapping-invalid inputの`input_contracts` identity projectionは次のexact algorithmに固定する。

-   上記exact field shapeの各identity fieldと`engine_version`を独立に処理する。
-   対象fieldが存在し、値がPython `str`型なら、empty stringを含むraw値をそのまま投影する。
-   対象fieldがmissing、nullまたはnon-stringならnullを投影する。
-   identity投影元の親objectがmissingまたはMappingでない場合、上記exact shapeの
    該当nested report objectに定義されたすべてのfieldをnullとする。
-   他fieldのvalidityによって投影値を変更しない。strip、normalize、infer、complete、
    stringifyを禁止し、boolean、numberまたはその他のnon-stringをstringへ変換しない。
-   このprojectionのために占術計算または新しい占術判断を行わない。

`semantic_assessment`は次の順序のexactly 3 fieldを持つ。

1.  `status`
2.  `method`
3.  `version`

`status`は`"not_run" | "completed" | "unavailable" | "failed" | "inconclusive"`とする。
`not_run`はdeterministic ERRORのためsemantic検査を開始しなかった場合、
`unavailable`はassessor未設定またはidentity不正、`failed`はassessor実行またはoutput validation失敗、
`inconclusive`は少なくとも1件の意味判定を確定できない場合とする。
`not_run`と`unavailable`では`method` / `version`をnull、他の三statusでは
23.11で呼出前に検証したassessor identityのnon-empty stringとする。
`pass`には`status == "completed"`を必須とする。statusごとのexact lifecycleは23.11に従う。

reportはraw provider response、model usage、API key、非決定的timestampを含めない。

### 23.7 Finding exact contract

Findingは次の順序のexactly 9 fieldを持つ。すべてREQUIRED、unknown field禁止。

1.  `finding_id`
2.  `code`
3.  `severity`
4.  `blocking`
5.  `path`
6.  `message`
7.  `evidence`
8.  `repairability`
9.  `requires_human_review`

``` json
{
  "finding_id": "finding_0001",
  "code": "claim_type_mismatch",
  "severity": "ERROR",
  "blocking": true,
  "path": "/sections/0/summary",
  "message": "claim_typeが本文の意味と一致しません。",
  "evidence": [
    {
      "source_contract": "ai_reading_v2",
      "path": "/sections/0/summary"
    }
  ],
  "repairability": "auto",
  "requires_human_review": false
}
```

-   `finding_id`はcanonical sort後に`finding_0001`から始まる4桁zero-padded独立連番とする。
-   `code`は23.9のfrozen issue code catalogのみを許可する。
-   `severity`は`"ERROR" | "WARNING" | "INFO"`のみとする。
-   `path`はAI Reading v2内のRFC 6901 JSON Pointerとし、report-level findingはempty stringとする。
-   `message`は23.9のcode catalog所有のfixed messageとし、semantic assessorが生成、変更しない。
-   `evidence`は原則1件以上のexact evidence entry arrayとする。
    `semantic_assessment_unavailable`、`semantic_assessment_failed`、
    `semantic_assessment_inconclusive`のreport-level infrastructure findingに限り、
    `path == ""`かつ`evidence == []`とする。その他のfindingにempty evidenceを許可しない。
-   evidence entryは`source_contract`、`path`の順序のexactly 2 fieldを持ち、unknown fieldを禁止する。
-   evidence `source_contract`は`"ai_reading_v2" | "reading_context_v2" |
    "common_judgment_metadata_v1"`のみとする。
-   evidence `path`はRFC 6901 JSON Pointerとし、source contract内のvalueへresolveする。
    invalid input findingは23.5のcontract root policyに従う。
-   `repairability`は`"auto" | "human" | "none"`のみとする。
-   `requires_human_review`はbooleanとする。

### 23.8 Decision, severity, and blocking semantics

`severity`、Findingの`blocking`、Reportの`blocking`は異なる三概念とする。

-   `severity`は問題の重大度を示す。
-   Finding `blocking`はそのfindingが単独で自動公開を停止するかを示す。
-   Report `blocking`は最終`decision`に基づく公開停止状態を示す。

次をMUSTとする。

-   ERROR findingは`blocking = true`。
-   INFO findingは`blocking = false`、`requires_human_review = false`。
-   `requires_human_review = true`のfindingはseverityがWARNINGでも`blocking = true`。
-   WARNINGはcode mappingにより`blocking = false`または`true`になり得る。
-   ERROR findingが1件以上なら`decision = "fail"`。
-   ERRORがなく、human review findingがあるかsemantic assessmentが未完了なら
    `decision = "review"`。
-   その他の場合だけ`decision = "pass"`。
-   Report `blocking == (decision != "pass")`をexact invariantとする。
-   ERRORがなくても`decision = "review"`ならReport `blocking = true`。
-   semantic assessment未完了を`pass`としてはならない。
-   Reportの`human_review_required == any(finding.requires_human_review for finding in findings)`を
    exact invariantとする。
-   `error_count`、`warning_count`、`info_count`はfindingsのseverity countとexact matchする。

v1の「ERRORだけがblocking」という実装慣例をv2に暗黙再利用してはならない。
`review`はERRORとは異なるが、自動公開、PDF生成または`pass`への変更を行ってはならない。
§23.8のdecision kernel自体は変更しない。v1.2では§23.14どおりhuman approval overrideを
定義しないため、明示的なhuman approvalを理由とする公開またはdecision overrideも許可しない。

### 23.9 Frozen issue code catalog

severity、blocking、repairability、human reviewおよびmessageは次のfrozen mappingからtrusted codeが付与する。
semantic assessorまたはAuto-Repairがこれらを決定、変更してはならない。

| code | severity | blocking | repairability | human review | fixed message |
|---|---|---:|---|---:|---|
| `input_contract_invalid` | ERROR | true | none | false | 入力contractがowner validationまたはprompt prerequisite validationを通過しません。 |
| `input_contract_mismatch` | ERROR | true | none | false | AI Readingと検証入力のtrusted identityが一致しません。 |
| `ai_reading_contract_invalid` | ERROR | true | none | false | AI Reading v2の構造がfinal contractに一致しません。 |
| `trusted_field_mismatch` | ERROR | true | none | false | AI Reading v2のtrusted fieldが再構築値と一致しません。 |
| `reference_resolution_error` | ERROR | true | none | false | 参照がtrusted sourceへ解決できません。 |
| `warning_uncertainty_not_preserved` | ERROR | true | none | false | warningまたはuncertaintyが保持されていません。 |
| `disclaimer_mismatch` | ERROR | true | none | false | disclaimerがtrusted constantと一致しません。 |
| `future_year_integrity_error` | ERROR | true | none | false | future_flowのyearまたは順序がtrusted inputと一致しません。 |
| `claim_type_mismatch` | ERROR | true | auto | false | claim_typeが本文の意味と一致しません。 |
| `fact_semantic_mismatch` | ERROR | true | human | true | source_fact_codesが本文の占術主張を意味的に支持しません。 |
| `component_semantic_mismatch` | ERROR | true | human | true | source_componentsが本文のcertaintyまたはprovenance表現と整合しません。 |
| `luck_semantic_mismatch` | ERROR | true | human | true | luck_astrology本文がtrusted luck sourceと整合しません。 |
| `engine_value_contradiction` | ERROR | true | human | true | 本文がengine確定値またはlabelと矛盾します。 |
| `judgment_status_wording_violation` | ERROR | true | auto | false | 本文の確度表現がcanonical judgment status policyに違反します。 |
| `unknown_hour_derived_claim` | ERROR | true | human | true | 出生時刻不明入力からhour由来の主張を生成しています。 |
| `missing_applicable_uncertainty` | ERROR | true | human | true | 適用可能なuncertaintyが本文または参照に保持されていません。 |
| `unsupported_numeric_claim` | ERROR | true | auto | false | 本文の数値主張をtrusted sourceで確認できません。 |
| `consultation_astrology_leak` | ERROR | true | human | true | consultationから新しい占術判断を生成しています。 |
| `prohibited_claim` | ERROR | true | human | true | 医療・法律・投資の断定、将来保証、不安煽りまたはその他の禁止主張が含まれています。 |
| `overconfident_wording` | WARNING | false | auto | false | 本文に過度に断定的な表現があります。 |
| `evidence_interpretation_advice_confusion` | WARNING | false | auto | false | evidence、interpretation、adviceの役割が混同されています。 |
| `astrology_wording_ambiguity` | WARNING | false | auto | false | 占術上の根拠または確度の表現が曖昧です。 |
| `semantic_assessment_unavailable` | WARNING | true | human | true | semantic assessorが未設定またはidentity不正のため意味検査を実行できません。 |
| `semantic_assessment_failed` | WARNING | true | human | true | semantic assessorの実行または出力検証に失敗しました。 |
| `semantic_assessment_inconclusive` | WARNING | true | human | true | semantic assessorが一つ以上の意味検査を確定できませんでした。 |
| `source_limitation_note` | INFO | false | none | false | source limitationが適切に開示されています。 |

### 23.10 Deterministic and semantic checks

Deterministic checksは少なくとも次を含む。

-   三inputのowner / final contract validation。
-   contract identity、trusted field、fixed section、title、year / order、disclaimerの照合。
-   fact / component / warning / uncertainty referenceのexistenceとsource resolution。
-   warning / uncertainty catalogのexact preservation。
-   declared `claim_type`のlocation / reference ruleとluck crosswalk。
-   明示的なunsupported numeric literal。
-   report / finding shape、count、order、dedup、decision invariant。

Semantic checksは少なくとも次を含む。

-   `claim_type`と本文意味の一致。
-   fact / componentとproseのsemantic relevance。
-   luck valueとluck proseの一致。
-   engine value / labelの言い換え矛盾。
-   `resolved` / `provisional` / `uncertain` / `unsupported` / null statusに応じた表現。
-   unknown birth timeからのhour-derived interpretation。
-   consultationからのastrology calculationまたは新しい占術判断。
-   医療・法律・投資の断定、将来の保証、不安を煽る表現。
-   applicable warning / uncertaintyが本文の確度表現に適切に反映されているか。

keyword、regular expression、literal comparisonはpositive evidenceまたはdeterministic findingに使用できるが、
matchしないことだけでsemantic checkをPASSにしてはならない。
warnings / uncertaintyはastrology factではなく、`claim_type`の自動分類材料にしない。

#### 23.10.1 明示的なunsupported numeric literal

Quality Gate v2は、`claim_type == "astrology"`または
`claim_type == "luck_astrology"`である各`grounded_text_block.text`について、ASCII数字または
全角数字を含む明示的numeric literalをdeterministically検査しなければならない。
`claim_type == "practical"`のtextはこのdeterministic numeric checkの対象外とし、一般助言中の
行動数・時間と占術数値主張の区別、および`practical`へ偽装された占術数値主張はsemantic assessorが
検査する。deterministic numeric checkでfindingがないことをsemantic checkのPASSとしてはならない。

numeric grammarで使用するcharacter classをexactly次に固定する。

``` text
DIGIT := [0-9０-９]
SIGN := "+" | "-" | "＋" | "－"
DECIMAL_SEPARATOR := "." | "．"
PERCENT := "%" | "％"
HYPHEN_RANGE_SEPARATOR := "-" | "－"
NON_HYPHEN_RANGE_SEPARATOR := "–" | "—" | "〜" | "～"
RANGE_SEPARATOR := HYPHEN_RANGE_SEPARATOR | NON_HYPHEN_RANGE_SEPARATOR
WHITESPACE := Python str.isspace()がtrueを返す1 code point
OPTIONAL_WHITESPACE := WHITESPACE*

UNSIGNED_SCALAR := DIGIT+ (DECIMAL_SEPARATOR DIGIT+)? PERCENT?
SCALAR := SIGN? UNSIGNED_SCALAR
HYPHEN_RANGE := SCALAR OPTIONAL_WHITESPACE HYPHEN_RANGE_SEPARATOR OPTIONAL_WHITESPACE UNSIGNED_SCALAR
NON_HYPHEN_RANGE := SCALAR OPTIONAL_WHITESPACE NON_HYPHEN_RANGE_SEPARATOR OPTIONAL_WHITESPACE SCALAR
RANGE := HYPHEN_RANGE | NON_HYPHEN_RANGE
```

ASCII数字と全角数字が同一token内に混在することを許可する。integer partおよび存在するdecimal
fractionはそれぞれ1文字以上の`DIGIT`を持たなければならない。hyphen rangeではright endpointを
`UNSIGNED_SCALAR`に限定するため、`30-40`と`-6-3`はvalid range、`30--40`と`-6--3`はmalformedとする。
non-hyphen rangeでは両endpointにoptional `SIGN`を許可するため、`-6〜-3`と`－６～－３`はvalid
rangeとする。`.5`、`．５`、`70.`、`７０．`、decimal separatorの重複、range endpointの欠落、
その他grammar全体に一致しないnumeric-looking candidateはmalformedとし、部分tokenまたは短い
rangeへ分割して採用せずsemantic assessorへ委譲する。Unicode minus `−`（U+2212）は`SIGN`または
`RANGE_SEPARATOR`として扱わず、その文字を含むcandidate全体をsemantic assessorへ委譲する。

`RANGE`は二つのendpointを独立した`SCALAR`として検査する。interval、包含関係、差、幅、順序または
占術上の意味を計算してはならない。一方でもunsupportedであれば、そのblockはunsupported numeric
literalを持つものとする。

比較のために、認識済みnumeric token内だけでexactly次の変換を許可する。

``` text
０..９ -> 0..9
＋ -> +
－ -> -
． -> .
％ -> %
```

この変換はcomparison-onlyとし、AI Reading、Reading Context、Common Judgment Metadataまたは
trusted valueを変更してはならない。全文NFKC normalization、漢数字変換、その他のUnicode
normalizationを禁止する。漢数字はdeterministic numeric checkの対象外としsemantic assessorへ
委譲する。

version、IDまたはsource codeの一部であるnumeric spanをnumeric claimとして抽出してはならない。
lexer用の追加character classをexactly次に固定する。

``` text
ASCII_LETTER := [A-Za-z]
IDENTIFIER_CHAR := ASCII_LETTER | "_" | "." | "．" | DIGIT
NUMERIC_MARK := DIGIT | SIGN | DECIMAL_SEPARATOR | PERCENT | RANGE_SEPARATOR | "−"
```

version / ID / source code exclusionはexactly次に限定する。

-   maximalな`IDENTIFIER_CHAR+` spanのうち、1文字以上の`DIGIT`と、1文字以上の`ASCII_LETTER`または
    `_`をともに含むspan。identifierが数字から始まるかどうかを問わない。例: `v1.2`、
    `warning_0001`、`section2`、`strength.v2`、`70abc`、`70_foo`。
-   `DIGIT+`だけのsegmentが`.`または`．`で3 segment以上連結されたmaximal dotted chain。
    例: `1.2.3`。separatorが1件だけの`70.0`はdecimal literalとして扱う。

date / time grammarに一致するspan内のnumeric literalはdeterministic numeric checkから除外し、
semantic assessorへ委譲する。component widthをexactly次に固定し、各component内でASCII数字、
全角数字およびその混在を許可する。

``` text
YEAR := exactly 4 DIGIT
MONTH := 1 or 2 DIGIT
DAY := 1 or 2 DIGIT
HOUR := 1 or 2 DIGIT
MINUTE := exactly 2 DIGIT
SECOND := exactly 2 DIGIT
DATE_TIME_MARK := DIGIT | "/" | "-" | ":" | "年" | "月" | "日" | "時" | "分" | "秒"

YEAR年MONTH月DAY日
YEAR年MONTH月
MONTH月DAY日
YEAR/MONTH/DAY
MONTH/DAY
YEAR-MONTH-DAY
HOUR:MINUTE
HOUR:MINUTE:SECOND
HOUR時MINUTE分
HOUR時MINUTE分SECOND秒
HOUR時
```

上記grammarの`/`、`-`、`:`、`年`、`月`、`日`、`時`、`分`、`秒`は記載したliteral characterに
固定する。standaloneの`MINUTE分`はdurationの可能性があるためdate / time exclusionに含めない。
date / time candidateはmaximalな連続`DATE_TIME_MARK+` spanとし、そのcandidate全体が上記patternの
いずれかへ一致する場合だけ除外する。candidateの部分spanをdate / timeとして除外してはならない。
date / time grammarへの一致は字句上の除外条件だけであり、componentの値域、暦上または時計上の
実在性、文章上の妥当性、対象時点との整合性を保証しない。したがって`2026年9月23日`と
`2026年13月40日`はともにlexical dateとして除外する一方、`1年2月`、`123:456`、`999時999分`、
`30分`は除外しない。意味判定はsemantic assessorの責務とする。除外したdate / time spanの一部を
numeric tokenとして再抽出してはならない。

lexical processing orderとcandidate boundaryをexactly次に固定する。

1.  maximalなversion / ID / source code spanおよびmaximal dotted chainを先に除外する。
2.  残るtextから上記date / time grammarに一致するmaximal spanを除外する。
3.  残るtext上のmaximalな連続`NUMERIC_MARK+`をatomic runとする。通常の`WHITESPACE`はrunを分離する。
4.  `WHITESPACE+`だけを挟む隣接atomic runについて、left runの末尾またはright runの先頭が
    `RANGE_SEPARATOR`または`−`である場合、その二runをrange linkで接続する。range linkの推移閉包に
    含まれるrunと間のwhitespaceをすべて含むleftmost-longestのmaximal spanを一つのrange candidateと
    する。linkを持たないatomic runはそれ自体を一つのcandidateとする。この規則はseparator前後の
    whitespaceが0、片側だけ、両側のいずれであっても同じcandidateを構築する。
5.  各candidate全体が`RANGE`へ一致する場合だけvalid rangeとして採用する。全体が一致しない場合でも、
    candidateが単一atomic runであり、その全体が`SCALAR`へ一致する場合だけscalar tokenとして採用する。
6.  1文字以上の`DIGIT`を含むがstep 5のいずれにも一致しないcandidateはcandidate全体をmalformedとし、
    内部の`SCALAR`または短い`RANGE`を再抽出してはならない。`−`を含むcandidateは全体をsemantic
    assessorへ委譲する。

一度valid rangeまたはmalformed range candidateへ取り込んだrunを再使用してはならない。この規則により、
`30-40`、`30 -40`、`30- 40`および`30 - 40`はそれぞれ一つのvalid range、`70 80`は二つのscalar
tokenとなる。`.5`、`70.`、`70%80`、
`30--40`および`-6--3`はcandidate全体がmalformedであり、内部の`5`、`70`、`30-40`、`-6-3`等を
再抽出しない。`30 - 40 - 50`もmaximal candidate全体がmalformedであり、`30 - 40`を短いrangeとして
採用しない。`70点`では`70`をscalarとして抽出し、`−6`では`6`を再抽出しない。

先に除外したspanまたはmalformed candidateの一部を後続stepでnumeric tokenとして再抽出してはならない。
このlexical processing order、candidate boundaryおよびatomicityはAI Reading textとtrusted string leafの
両方へ同じように適用する。

yearだけの表現、yearに一般語が続く表現およびyear rangeはdate / time exclusionに含めない。
したがって`2026年`、`2026年の運勢`、`2026年度`、`2026年頃`ではyear literalを抽出し、
`2026〜2030年`では両year endpointを抽出する。一方、`2026年9月23日`、`2026/09/23`および
`10:30`は各date / time span全体を除外する。`70点`と`７０点`はdate / time exclusionに含めず、
それぞれcomparison-only normalization後の`70`を検査する。year literalを抽出することと、trusted
`future_flow_years`を根拠として使用できることは別の規則とし、後者は次のscope一致時だけ許可する。

-   `future_flow.yearly[i]` blockでは、そのtrusted positional indexにattachされたexact yearだけ。
-   `future_flow` sectionのnon-yearly blockでは、trusted `future_flow_years`の全year。
-   top-level summary、`current_luck`を含む他section、および`consultation_answer`では、
    `future_flow_years`をnumeric sourceとして使用しない。

future yearとのnumeric一致はyear literalのsupportだけを意味し、fact grounding、luck grounding、
future eventの保証または新しい占術判断を成立させない。

`claim_type == "astrology"` blockのtrusted numeric universeは、同じblockの
`source_fact_codes`がresolveするReading Context factの`value`と、上記scope規則によって当該blockに
許可されたexact-scope future yearだけとする。section-level `facts`、unreferenced fact、別blockのfact、
別blockのreferenceまたは当該blockに許可されないfuture yearを流用してはならない。各referenced
factの`value`をJSON treeとして再帰走査し、booleanを除くfinite JSON number、およびstring leaf内で
本節のnumeric grammarにより認識され、version / ID / source codeまたはdate / time exclusionに
該当しないliteralをtrusted numeric tokenとして使用できる。

`claim_type == "luck_astrology"` blockのtrusted numeric universeは、同blockのreferenced fact、
§22.12のcrosswalkでblock scope、selected `source_component`およびyear / indexへexact matchする
`luck_value_source_entry.context_path`が指すReading Context value、および上記scope規則によって
当該blockに許可されたexact-scope future yearだけとする。fact valueとluck valueの再帰走査規則は
同じとする。unselected component、別year、別scope、nullまたはunavailableなluck value、または
当該blockに許可されないfuture yearを使用してはならない。

Common Judgment Metadataのvalue / evidence、warning / uncertainty catalog、section-level fact、
unreferenced fact、other-block fact、crosswalkに一致しないReading Context field、`target_datetime`、
null / unavailable luck valueをtrusted numeric sourceにしてはならない。Common Judgment Metadataは
status、certainty、warnings、uncertaintyおよびprovenanceを提供できるが、numeric astrology valueを
作らない。

trusted JSON numberからcomparison valueを作る前に、§23.5のowner / final input validationを完了
しなければならない。本節は、NaN、Infinity、numeric subclassまたはその他のowner / final contract
不適合値について、新しいissue code、finding、error分類または入力契約を追加せず、既存のinput
validation結果を変更しない。numeric conversionは、既存契約を通過したplain JSON snapshot内のexact
builtin `int`または`float`だけを受け取り、`bool`をnumeric sourceとして扱ってはならない。

finite JSON numberのcomparison `Decimal`はexactly次の手順で構築する。

1.  valueを
    `json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=False, allow_nan=False)`で
    numeric textへserializeする。
2.  返されたnumeric textをそのまま`Decimal(numeric_text)`へ渡す。

`Decimal.from_float`、rounding、`quantize`、tolerance、unit conversionまたはpercent conversionを
使用してはならない。したがって、`70`、`70.0`、`0.1`、`1e-6`および`-0.0`から構築するcomparison
valueは、それぞれ`Decimal("70")`、`Decimal("70.0")`、`Decimal("0.1")`、`Decimal("1e-06")`および
`Decimal("-0.0")`とする。serializationまたは`Decimal`構築へ到達する前に既存owner / final contractで
拒否された値を、本節だけを根拠に再分類してはならない。

plain numeric tokenはcomparison-only normalization後のexact decimal valueで比較する。
`70`と`70.0`、`７０`と`70`、`+70`と`70`、`-0`と`0`はequalとする。signを保持し、
`-70`と`70`はequalとしない。percent tokenとplain tokenは別kindとし、`0.5`、`50`、`50%`を
相互に変換してはならない。trusted string leafの`50%`とAI Reading textの`５０％`はequalとするが、
trusted JSON number `50`は`50%`をsupportしない。rounding、unit conversion、percent conversion、
tolerance、近似比較またはastrology recalculationを禁止する。

unsupported literalを1件以上持つblockについて、`unsupported_numeric_claim` findingをblockごとに
exactly 1件生成する。同一block内のunsupported literal数をfinding数へ反映しない。findingの`path`は
当該`grounded_text_block`の`text` fieldへのRFC 6901 JSON Pointerとし、`evidence`はexactly同じ
AI Reading text pathを指す次の1 entryだけとする。存在しないtrusted source pathをevidenceとして
作ってはならない。

``` json
[
  {
    "source_contract": "ai_reading_v2",
    "path": "/sections/0/summary/text"
  }
]
```

複数blockがunsupported literalを持つ場合は各blockに1 findingを生成する。finding schema、issue
catalog、fixed message、canonical evidence normalization、sort、exact dedupおよびfinding ID assignmentは
§23.7、§23.9、§23.12から変更しない。semantic assessor由来の同code findingは
`(code, path, canonical_evidence_json)`がexact一致する場合だけ既存規則でdeduplicateし、異なるpathまたは
evidenceを強制統合してはならない。

Phase 5.1では、numeric checkの実装後も`evaluate_ai_reading_quality_v2()`のpublic PASS防止
`NotImplementedError`境界を維持する。public PASSの解禁はnumeric実装の独立監査後に、別工程および
別の人間承認によってのみ行う。

### 23.11 Provider-independent semantic assessor

Quality Gate v2 coreはprovider-independentとし、OpenAI SDK、model name、API keyまたは
provider transportをcore public contractへ固定しない。semantic assessorは次の三inputを
exact deep copyとして別々に受け取る。

`SemanticAssessorV2`は`assess()`に加え、read-only identity attributeとして`method`と
`version`を公開し、両方をnon-empty stringとする。Quality Gate v2は
`assess()`呼出前に`method`、`version`の順で各attributeをat most 1回取得する。
最初の取得例外で停止し、再取得しない。両方を取得できた場合はtypeと
non-emptyを検証したidentity snapshotをreportに使用する。呼出後にidentityを
再取得、推測または補完しない。

`semantic_assessor is None`、identity attributeの取得が例外、attribute欠落、type不正、
またはempty stringの場合は`unavailable`とし、assessorを呼び出さない。
`method` / `version`はともにnull、`semantic_assessment_unavailable`をexactly 1件とする。

``` python
assess(
    ai_reading,
    reading_context,
    judgment_metadata,
) -> SemanticAssessmentResultV2
```

raw `chart_result`、Generator request、provider responseまたはflattenしたinputを渡さない。

assessor outputはtop-levelに`status`、`findings`の順序のexactly 2 fieldを持ち、
unknown fieldを禁止する。

``` json
{
  "status": "completed",
  "findings": [
    {
      "code": "claim_type_mismatch",
      "path": "/sections/0/summary",
      "evidence": [
        {
          "source_contract": "ai_reading_v2",
          "path": "/sections/0/summary"
        }
      ]
    }
  ]
}
```

`status`は`"completed" | "inconclusive"`とする。各finding declarationは`code`、`path`、
`evidence`の順序のexactly 3 fieldとし、unknown fieldを禁止する。
assessorはsemantic issue code、AI Reading path、evidence referenceだけを宣言する。
severity、blocking、message、repairability、human review、finding IDを返してはならない。
trusted QG codeが23.9からそれらを付与する。

assessorが宣言できる`code`は次のexact allowlistに限定する。

1.  `claim_type_mismatch`
2.  `fact_semantic_mismatch`
3.  `component_semantic_mismatch`
4.  `luck_semantic_mismatch`
5.  `engine_value_contradiction`
6.  `judgment_status_wording_violation`
7.  `unknown_hour_derived_claim`
8.  `missing_applicable_uncertainty`
9.  `unsupported_numeric_claim`
10. `consultation_astrology_leak`
11. `prohibited_claim`
12. `overconfident_wording`
13. `evidence_interpretation_advice_confusion`
14. `astrology_wording_ambiguity`
15. `source_limitation_note`

input / contract / trusted-field error code、および`semantic_assessment_*`のinfrastructure codeを
assessorが返してはならない。これらはtrusted QG codeだけが生成する。

assessorは次を行ってはならない。

-   新しい占術判断、fact、value、referenceまたはsource pathの生成。
-   占術計算、status ranking、missing hour推測またはcertainty upgrade。
-   inputまたはAI Readingの変更。
-   文章、`claim_type`、referenceまたはtrusted fieldの修復。
-   severity、blockingまたはAuto-Repair eligibilityの決定。

semantic assessment lifecycleは次に固定する。

| status | assessor call | infrastructure finding | assessor declarations | method / version | decision effect |
|---|---:|---|---|---|---|
| `not_run` | no | none | none | null / null | semantic検査前のdeterministic ERRORにより`fail` |
| `completed` | exactly 1 | none | validated declarationをすべて保持 | validated identity snapshot | 全findingに23.8を適用 |
| `unavailable` | no | `semantic_assessment_unavailable` exactly 1 | none | null / null | deterministic ERRORがなければ`review` |
| `failed` | exactly 1 attempt | `semantic_assessment_failed` exactly 1 | すべて破棄 | validated identity snapshot | deterministic ERRORがなければ`review` |
| `inconclusive` | exactly 1 | `semantic_assessment_inconclusive` exactly 1 | output validationを通過したdeclarationをすべて保持 | validated identity snapshot | 保持したERRORがあれば`fail`、それ以外は`review` |

deterministic checkにERRORが1件以上ある場合は、assessorの有無やidentityを
評価せず`not_run`とし、assessorを呼び出さない。`completed`で
`semantic_assessment_*` findingを生成しない。`unavailable`、`failed`、`inconclusive`は
表の対応するinfrastructure finding以外の`semantic_assessment_*` findingを含めない。
これらinfrastructure findingは`path == ""`、`evidence == []`とする。

assessorの`assess()`実行が例外を出した場合、またはoutputがexact shape、status、
allowlist、pathまたはevidence validationを通過しない場合は`failed`とする。
一部でもinvalidなoutputからdeclarationを採用しない。assessorがvalidな
`status == "inconclusive"`を返した場合は、validなdeclarationを保持した上で
infrastructure findingを追加する。hidden retryを禁止する。
assessorのraw responseをQuality Report v2に保存しない。

### 23.12 Finding order and deduplication

finding候補は次のsort keyでcanonical orderingする。

``` text
(
  severity_rank,
  path,
  code,
  canonical_evidence_json
)
```

severity rankは`ERROR = 0`、`WARNING = 1`、`INFO = 2`とする。
evidence entryは`(source_contract, path)`でsortし、同一finding内のexact duplicateだけを除去する。
finding dedup identityは`(code, path, canonical_evidence_json)`とする。dedup後に
`finding_0001`からIDを付与する。

sortはlocaleに依存しないUnicode code pointのascending lexicographic comparisonとする。
`canonical_evidence_json`は、exact duplicate除去後に`(source_contract, path)`でsortした
evidence arrayを、各entryのfield順序を`source_contract`、`path`に固定し、次の
Python serializationとexactly同等なUTF-8 JSON textにしたものとする。

``` python
json.dumps(
    canonical_evidence,
    ensure_ascii=False,
    separators=(",", ":"),
    sort_keys=False,
    allow_nan=False,
)
```

empty evidenceを許可された23.7のinfrastructure findingでは
`canonical_evidence_json == "[]"`とする。

このfinding dedup ruleはQuality Report内のfindingにだけ適用する。
AI Reading、Reading Context、Common Judgment Metadataのwarning / uncertaintyの順序変更、
deduplicate、normalizeまたは相互変換は22.10どおり禁止する。

### 23.13 Auto-Repair v2 handoff

Quality Report v2自体をAuto-Repair v2へのhandoff sourceとする。Auto-Repair v2は
`repairability == "auto"`のfindingだけを候補にでき、target finding IDをreport順で保持する。
`repairability == "human"`または`"none"`のfindingを自動修復してはならない。

`repairability == "auto"`はAuto-Repair v2の検討候補を示すだけであり、
実際のfield変更許可、repair instructionまたはrepair成功を意味しない。
変更可能なmodel-owned pathは§24.4のexact contractだけとする。

trusted field、trusted reference、catalog、section ID / title、future year / order、disclaimer、
source contracts、engine versionまたはAI Reading validation reportを自動修復してはならない。
semantic assessor unavailable / failed / inconclusive findingはAuto-Repair対象外とする。

Auto-Repair後は同じ三input contractを用いてQuality Gate v2を再実行し、§24の
`attempt`、`issue_codes`、`before_hash`、`after_hash`、`result`を記録する。

### 23.14 Safety and human review policy

`birth_time_status.known == false`の場合、Quality Gate v2は22.8の各MUSTを本文意味と
referenceの両面から検査する。missing hour、hour pillar、hour-derived relation、
complete chartにおける不存在または`internal_reference_time`を出生時刻とする主張を禁止する。
strength confidence cap、`known_pillars_only`、estimated timing、applicable uncertaintyを弱体化しない。

次は`prohibited_claim`のERROR findingとし、disclaimerが正しいことを理由に許可しない。

-   占術による医療診断、治療指示または症状の断定。
-   法律判断、法的結果または法的行動の断定。
-   投資利益、損失回避、収益または金銭結果の保証。
-   結婚、転職、成功、発症その他の将来事象の保証。
-   不安、恐怖または依存を煽る表現。

general practical advice、専門家への相談推奨、不確実性を保持した一般的な未来表現は、
それ自体だけで`prohibited_claim`としない。

human reviewは少なくとも次の場合に必須とする。

-   semantic assessorがunavailable、failedまたはinconclusive。
-   fact / component / luck relevance、engine contradictionまたはunknown-hour-derived proseを自動判定できない。
-   `prohibited_claim`またはconsultation-derived astrologyが検出された。
-   applicable uncertaintyの反映可否を確定できない。

human reviewの完了、reviewer、reviewed-at、承認理由またはdecision overrideは
Quality Report v2へ暗黙追加しない。そのapproval artifactは将来の別contractとしてfreezeする。
v1.2ではそのapproval artifactを定義せず、`review`をhuman approvalで`pass`へ変更すること、
ReadingProduct V2を構築すること、またはPDFを生成・公開することを禁止する。

### 23.15 Compatibility boundary

Quality Gate v2は新規opt-in moduleとし、`engine/reading_quality.py`、`engine/reading_repair.py`、
v1 Reading Product、v1 API、v1 Golden、existing `ReadingQualityReport`およびexisting `QualityIssue`を
変更しない。v1のseverityまたはblocking慣例をv2へ暗黙継承しない。

Quality Gate v2のastrology calculation impactは`NONE`とする。

------------------------------------------------------------------------

## 24. Auto-Repair V2

### 24.1 Owner, identity, and public API

Auto-Repair v2のownerは新規opt-in module `engine/reading_repair_v2.py`とする。
`engine/reading_repair.py`とv1 repair contractは変更しない。

identity literalをexactly次に固定する。

``` text
AI_READING_REPAIR_V2_SCHEMA_VERSION = "ai_reading_repair_result_v2"
AI_READING_REPAIR_V2_VERSION = "ai_reading_repair_v2"
AI_READING_REPAIR_V2_METHOD = "openai_quality_issue_targeted_patch_v2"
AI_READING_REPAIR_V2_MAX_ATTEMPTS = 2
```

public entrypointはexactly次とする。`client`と`model`は明示的なkeyword-only
argumentとし、Auto-Repair v2 moduleが環境変数からproviderまたはmodelを暗黙決定してはならない。

``` python
def repair_ai_reading_v2(
    ai_reading: Mapping[str, Any],
    quality_report: AIReadingQualityReportV2,
    reading_context: Mapping[str, Any],
    judgment_metadata: Mapping[str, Any],
    *,
    semantic_assessor: SemanticAssessorV2 | None,
    client: Any,
    model: str,
    max_output_tokens: int = 6000,
    reasoning_effort: str = "low",
    store: bool = False,
) -> AIReadingRepairResultV2:
    ...
```

1 attemptにつき`client.responses.create(...)`をat most 1回呼び出す。provider transport、
configuration、response schemaまたはpatch validation failureに対するhidden provider retryを禁止する。
callerが同じattemptを暗黙再実行することも禁止する。

### 24.2 Trigger and target selection

automatic repairはexactly次の全条件を満たす場合だけ開始する。

1.  `quality_report.decision == "fail"`。
2.  blocking findingが1件以上存在する。
3.  すべてのblocking findingで`repairability == "auto"`。
4.  各target findingが24.4のeditable grounded text blockへ1意にresolveできる。

`pass`のauto-repairable WARNINGは記録のみとし、PASSを理由に文章を書き換えない。
`review`をPASSへ変更するためのautomatic repairを禁止する。blocking findingに
`repairability == "human"`または`"none"`が1件でもある場合、providerを呼び出さず
configuration errorとする。

initial target findingはinitial Quality Report v2のcanonical report orderで、
`repairability == "auto"`のfindingを抽出する。resultの`target_finding_ids`はそのfinding IDを
exact orderで保持し、deduplicate、sort、renumberまたは修正後reportのIDへ置換しない。
attempt 2のprovider inputはattempt 1後のQuality Reportに残るauto-repairable findingから再構築するが、
top-level `target_finding_ids`はinitial reportの値を維持する。

### 24.3 Exact provider request and provider-owned patch response

Auto-Repair v2はGenerator v2と同じResponses-style injectable client boundaryを使うが、
Generator v2のprivate helperをcontract authorityとしない。repair moduleは各attemptで
public `build_ai_reading_request_v2(reading_context, judgment_metadata)`を呼び、そのowner-valid
`model_input`をgrounding inputとしてdeep snapshotする。Prompt requestの`messages`、
`model_output_schema`、provider raw response、usage、response ID、API keyはrepair model inputへ入れない。

repair providerへ渡すmodel inputは次の順序でexactly 5 fieldを持つ。unknown fieldを禁止する。
下のJSONはordered field schemaの説明用fragmentであり、empty array / objectは以下の
exact runtime contentと置換すべきplaceholderである。そのままvalid request instanceではない。

``` json
{
  "schema_version": "ai_reading_repair_request_v2",
  "attempt": 1,
  "target_findings": [],
  "editable_blocks": [],
  "grounding_input": {}
}
```

-   `schema_version`はliteral `"ai_reading_repair_request_v2"`。
-   `attempt`はcurrent attemptとexact matchする`1 | 2`。
-   `target_findings`はcurrent pre-attempt reportから24.2で選択したfindingをreport orderで
    deep-copyする。各entryは§23.7のexactly 9-field finding representationとし、少なくとも1件。
-   `editable_blocks`は24.4でdeduplicateしたeditable path orderのarray。各entryは`path`、`text`の
    順序でexactly 2 fieldを持ち、`path`はeditable text path、`text`はcurrent AIReadingV2の
    そのpathにあるexact stringとする。
-   `grounding_input`は上記public Prompt Builderが返した`model_input`のexact deep snapshot。
    repair moduleは値の抽出、再計算、要約、catalog削減またはreference補完を行わない。

providerへは上の5-field inputと、変更可能pathとgroundingを識別するために必要な
データだけを渡す。full AIReadingV2、full QualityReportV2、その他のapplication
stateをmodel inputとして渡さない。`target_findings`と`grounding_input`はread-only contextであり、
providerが返せる変更権限を与えない。

system instructionのownerはrepair moduleとし、constantとvalueをexactly次に固定する。

``` python
AI_READING_REPAIR_V2_JSON_SCHEMA_NAME = "ai_reading_repair_patch_v2"
AI_READING_REPAIR_V2_INSTRUCTIONS = (
    "You repair only the supplied AI Reading v2 text fields. "
    "Return only JSON matching the supplied strict schema. "
    "Use only op=replace and only an allowed path. "
    "Do not invent or modify trusted facts, references, identities, catalogs, "
    "section metadata, years, disclaimer, or validation data."
)
```

user contentは5-field repair model inputを次でserializeしたexact stringとし、prefix、suffix、
current time、environment valueまたはnetworkから取得したhidden contextを追加しない。

``` python
json.dumps(
    repair_model_input,
    ensure_ascii=False,
    separators=(",", ":"),
    sort_keys=False,
    allow_nan=False,
)
```

1 attemptのprovider payloadは次のkey order / value constructionに固定し、
`client.responses.create(**deepcopy(payload))`をexactly 1回呼び出す。

``` python
{
    "model": resolved_model,
    "instructions": AI_READING_REPAIR_V2_INSTRUCTIONS,
    "input": [{"role": "user", "content": serialized_repair_model_input}],
    "max_output_tokens": max_output_tokens,
    "reasoning": {"effort": reasoning_effort},
    "store": store,
    "text": {
        "format": {
            "type": "json_schema",
            "name": "ai_reading_repair_patch_v2",
            "schema": repair_patch_schema,
            "strict": True,
        }
    },
}
```

`model`はcaller-supplied non-empty stringをstripした値。environmentまたはdefault modelへfallbackしない。
`max_output_tokens`はbooleanを含まなpositive integer、`reasoning_effort`はexactly
`"minimal" | "low" | "medium" | "high"`、`store`はexact built-in booleanとする。`client.responses.create`が
callableでない、またはいずれかのcaller optionがinvalidな場合はproviderを呼ぶ前に
`AIReadingRepairV2ConfigurationError`とする。Auto-Repair moduleはAPI key、model、clientまたはcurrent timeを
environmentから暗黙取得しない。

`repair_patch_schema`はJSON Schema Draft 2020-12の次のexact mappingとする。key orderも記載順とし、
field、keywordまたはconstraintを追加・削除しない。

``` json
{
  "type": "object",
  "properties": {
    "patches": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "properties": {
          "op": {"const": "replace"},
          "path": {"type": "string", "minLength": 1},
          "value": {"type": "string", "minLength": 1}
        },
        "required": ["op", "path", "value"],
        "additionalProperties": false
      }
    }
  },
  "required": ["patches"],
  "additionalProperties": false
}
```

JSON Schemaで表現しないwhitespace-only、path eligibility、duplicate、order、no-opは
response parse後に本節と24.4でlocal validationする。

response extractionは次のexact algorithmとする。field accessは対象が`Mapping`ならkey lookup、
それ以外はattribute lookupとする。最初に`response.output_text`がnon-empty stringなら
stripして使う。それ以外は`response.output`がlist / tupleの場合にそのorder、各itemの
`content`がlist / tupleの場合にそのorderでnon-empty stringの`text`をstripして集め、
`"\n".join(parts)`を使う。usable textが0件なら
`AIReadingRepairV2ProviderResponseError`。extracted text全体をJSONとして1回parseし、NaN / Infinity /
duplicate key / trailing prose / code fenceをrejectする。raw response、usage、response ID、API keyは
result、attempt log、exception diagnosticへ保存しない。

providerが返すmodel-owned JSONはexactly次のshapeとする。unknown fieldを禁止する。

``` json
{
  "patches": [
    {
      "op": "replace",
      "path": "/sections/0/summary/text",
      "value": "修正後の文章"
    }
  ]
}
```

`patches`は1件以上のarray。各entryは`op`、`path`、`value`の順序でexactly 3 fieldを持つ。

-   `op`はliteral `"replace"`のみ。
-   `path`はRFC 6901 JSON Pointerのnon-empty string。
-   `value`はnon-empty string。whitespace-only stringを禁止する。
-   同一`path`の重複を禁止する。
-   異なるpatch間でancestor / descendant関係にある`path`を禁止する。
-   provider responseのpath orderは24.4で導出したeditable path orderのsubsequenceでなければならない。
-   元のtextとexactly同じ`value`はno-opとし、invalid patchである。
-   empty `patches`、malformed JSON、code fence、extra prose、unknown op、unknown path、type mismatchを
    repair failureとし、部分的に適用しない。

patch array全体のvalidationがPASSした後だけ、deep copyしたAIReadingV2へarray orderでatomicに適用する。
1件でもinvalidな場合は0件適用とする。full AIReadingV2 response、model-owned payload全体の
replacement、merge-patch、JSON Patchの`add` / `remove` / `move` / `copy` / `test`を許可しない。

### 24.4 Editable path derivation

Auto-Repair v2が変更できるのは、target findingと関連付くmodel-owned
`grounded_text_block.text`だけとする。AIReadingV2から次のblock rootをcanonical traversal orderで列挙する。

1.  `/summary`
2.  section array orderで、各sectionの`/summary`、`/detail`、`/evidence` array order、
    `/interpretation` array order、`/advice` array order
3.  `future_flow`の`yearly` array orderで各entryの`/summary`、`/detail`
4.  non-nullな`/consultation_answer`

finding `path`に対し、上記block rootのうちfinding pathと同一、またはfinding pathの
RFC 6901 segment ancestorであるlongest rootを関連blockとする。finding pathがそのblockの
`/text`または`/claim_type`等のdescendantであっても、editable pathはexactly
`<block-root>/text`とする。関連blockが0件または1意でないfindingはautomatic repair対象にできない。

provider responseの`path`はここで導出したeditable path stringのいずれかと
Unicode code point単位でexact matchしなければならない。URI fragment / percent encoding、
decode後だけ等価な`~0` / `~1`変形、array indexのleading zero、Unicode digitまたは
normalize後だけ等価なpathを許可しない。decodeしたpathを別pathとして再解釈せず、
exact membership検査に失敗した場合はpatch array全体をrejectする。

複数findingが同じtext pathへresolveする場合、最初のfinding orderの位置で1つのeditable pathに
deduplicateするが、`target_finding_ids`は全finding IDを元の順序で保持する。

次はmodel-owned fieldであってもeditableではない。

-   `claim_type`
-   `source_fact_codes`
-   `source_components`
-   block / sectionの`warnings`、`uncertainty`
-   section `facts`
-   future yearおよびyear order
-   consultation presence / absence

次は所有者にかかわらず常に変更禁止とする。

-   schema / version / method / status / engine identity
-   trusted warning / uncertainty catalog
-   source contracts
-   fixed section ID / title / order
-   attached future year / order
-   disclaimer
-   AI Reading validation report
-   Reading Context、Common Judgment Metadata、Quality Report
-   engine resultまたは占術計算値

### 24.5 Validation and Quality Gate rerun

validation orderをexactly次に固定する。

1.  input typeとplain JSON snapshot可否を検証する。
2.  Reading Context v2とCommon Judgment Metadataのowner validationを実行する。
3.  initial Quality Report v2のidentity、decision、finding catalog invariantをowner contractで検証する。
4.  24.2のtriggerとtarget finding orderを検証する。
5.  editable pathを24.4で導出する。
6.  current AIReadingV2のbefore hashを算出する。
7.  providerを1回だけ呼び出す。
8.  response全体と24.3で検証する。
9.  deep copyへpatchをatomicに適用する。
10. final AIReadingV2 contractとtrusted fieldが変更されていないことを検証する。
11. after hashを算出する。
12. 同じReading Context v2、Common Judgment Metadata、同じ`semantic_assessor` instanceで
    `evaluate_ai_reading_quality_v2()`を実行する。
13. resultにattempt logとfinal reportを保存する。

rerunのdeterministic ERRORが残る場合、Quality Gateの凍結lifecycleによりsemantic assessorは
呼び出されない。deterministic checkがPASSした場合は、同じassessorを通じてsemantic lifecycleを
最初から実行する。initial semantic resultをrepair後へcopy、reuseまたはPASSとしてはならない。

attempt後reportが`decision == "pass"`なら即時終了する。PASS以外で、かつ次attemptの
24.2条件を満たす場合だけattempt 2へ進む。次attemptのtriggerを満たさなくなった場合、または
2回のattempt後もPASSでない場合は、利用可能なautomatic repair attemptが尽きたものとして
`status == "exhausted"`を返す。PASSでないreportを書き換えたり、repairが成功したとみなしたり
しない。

### 24.6 Canonical hashing

`before_hash`、`after_hash`、および他節のAuto-Repair snapshot hashはexactly次で算出する。

``` python
sha256(
    json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")
).hexdigest()
```

hex digestはlowercase 64 ASCII characterとする。hashのためにinputのkey order、numeric value、string、
warning / uncertainty orderを変更しない。`sort_keys=True`はserializationのためだけに使用する。

### 24.7 Exact result and attempt-log contracts

`RepairAttemptLogV2`のJSON representationは次の順序でexactly 5 fieldを持つ。

1.  `attempt`: integer。`1 | 2`。
2.  `issue_codes`: current pre-attempt reportでtargetとなったcodeのreport-order array of string。
3.  `before_hash`: 24.6のlowercase SHA-256。
4.  `after_hash`: 24.6のlowercase SHA-256。
5.  `result`: `"repaired" | "failed"`。

valid patchがatomicに適用され、after hashがbefore hashと異なり、final AIReadingV2 contractを
満たすattemptだけ`result == "repaired"`とする。provider / transport / schema / invalid patch failureは
`result == "failed"`相当だが、public resultを返さずtyped exceptionをraiseする。exceptionは実行済み
attempt number、issue codes、before hash、存在する場合のafter hashをread-only diagnostic dataとして
保持できるが、Quality Reportへ追加してはならない。

`AIReadingRepairResultV2.to_dict()`は次の順序でexactly 10 fieldを返す。
下のJSONはordered outer schemaの説明用fragmentであり、`{}`と`[]`は各owner
contractに従うcomplete snapshot / non-empty runtime arrayと置換すべきplaceholderである。
そのままvalid result instanceではない。

``` json
{
  "schema_version": "ai_reading_repair_result_v2",
  "version": "ai_reading_repair_v2",
  "method": "openai_quality_issue_targeted_patch_v2",
  "status": "pass",
  "initial_ai_reading": {},
  "final_ai_reading": {},
  "initial_quality_report": {},
  "final_quality_report": {},
  "target_finding_ids": [],
  "attempts": []
}
```

-   `status == "pass"`はfinal reportの`decision == "pass"`とexact matchする。
-   `status == "exhausted"`は1件以上のvalid attemptを完了したが、final decisionがPASSでなく、
    次attemptの24.2 triggerを満たさないか2 attemptsへ到達した場合とする。
-   initial / final AI Readingはplain JSON deep snapshot。
-   initial / final Quality Reportはそれぞれの`to_dict()` deep snapshot。
-   `target_finding_ids`は24.2のinitial report order。
-   `attempts`はattempt number orderの1または2件のlog。
-   resultと`to_dict()`はinputまたは保持snapshotへのmutable referenceを公開しない。

### 24.8 Exceptions and non-goals

moduleはbase `AIReadingRepairV2Error`と、次のpublic typed subclassを所有する。

-   `AIReadingRepairV2ConfigurationError`
-   `AIReadingRepairV2ProviderRequestError`
-   `AIReadingRepairV2ProviderResponseError`
-   `AIReadingRepairV2PatchValidationError`
-   `AIReadingRepairV2CandidateValidationError`

trigger不成立、invalid caller optionまたはmissing dependencyはconfiguration error。provider transport failureは
provider request error。model responseのparse / schema failureはprovider response error。24.3違反はpatch
validation error。patch後のfinal AIReadingV2 / trusted-field invariant違反はcandidate validation errorとする。
exceptionから個人情報、API key、full provider responseを暗黙にmessageへ含めない。

Auto-Repair v2は占術計算、fact生成、reference補完、claim type再分類、human approval、
publication decision overrideを行わない。入力AIReadingV2、Reading Context、Common Judgment Metadata、
Quality Reportを変更しない。

------------------------------------------------------------------------

## 25. ReadingProduct V2

### 25.1 Owner, identity, and public builder

ReadingProduct v2のownerは新規opt-in module `engine/reading_product_v2.py`とする。
`engine/reading_product.py`、`reading_product_v1`およびv1 consumerを変更しない。

identity literalをexactly次に固定する。

``` text
READING_PRODUCT_V2_SCHEMA_VERSION = "reading_product_v2"
READING_PRODUCT_V2_VERSION = "reading_product_v2"
READING_PRODUCT_V2_METHOD = "reading_product_v2"
READING_PRODUCT_V2_STATUS = "ready_for_publication"
```

public builderはexactly次とする。

``` python
def build_reading_product_v2(
    engine_result: Mapping[str, Any],
    reading_context: Mapping[str, Any],
    ai_reading: Mapping[str, Any],
    quality_report: AIReadingQualityReportV2,
    *,
    generated_at: datetime,
    repair_result: AIReadingRepairResultV2 | None = None,
) -> ReadingProductV2:
    ...
```

Prompt request、provider raw response、API keyをargumentまたはproduct fieldとして受け取らない。
Common Judgment MetadataはQuality Gate inputであるが、ReadingProductV2の5番目のembedded source snapshotとしない。

### 25.2 Exact top-level schema

`ReadingProductV2.to_dict()`は次の順序でexactly 10 fieldを返す。すべてREQUIRED、
unknown field禁止。
下のJSONはordered top-level schemaの説明用fragmentであり、`{}`は各owner contractで
展開すべきnested snapshotのplaceholderである。そのままvalid Product instanceとはみなさない。

``` json
{
  "schema_version": "reading_product_v2",
  "version": "reading_product_v2",
  "method": "reading_product_v2",
  "status": "ready_for_publication",
  "engine_result": {},
  "reading_context": {},
  "ai_reading": {},
  "quality_report": {},
  "repair_history": {},
  "metadata": {}
}
```

`engine_result`、`reading_context`、`ai_reading`、`quality_report`はbuilder inputのplain JSON deep snapshotとする。
`quality_report`は`AIReadingQualityReportV2.to_dict()` representationとする。builder後のinput mutationまたは
productの`to_dict()` result mutationは、product内部snapshotに影響してはならない。

4 source snapshotのowner contractとnullabilityを次に固定する。

| Product field | type / nullability | owner contract |
|---|---|---|
| `engine_result` | non-null plain JSON object | public `calculate_chart()` successful result。Productはfieldを追加・削除・normalizeしない |
| `reading_context` | non-null plain JSON object | §20のowner-valid `reading_context_v2` |
| `ai_reading` | non-null plain JSON object | §22のfinal validated `ai_reading_v2` |
| `quality_report` | non-null plain JSON object | §23.6の`AIReadingQualityReportV2.to_dict()` |

各snapshot内でowner contractがnullableと定義したfieldのnullは保持する。Product独自のnull fallback、
legacy aliasまたはsource reconstructionを禁止する。

### 25.3 Repair history

`repair_history`は常にnon-null mappingとし、次の順序でexactly 2 fieldを持つ。

repairなし:

``` json
{
  "state": "not_repaired",
  "result": null
}
```

Auto-Repair v2あり:
下の`{}`は24.7のcomplete `AIReadingRepairResultV2.to_dict()` snapshotを表す説明用
placeholderであり、そのままvalid repair history instanceではない。

``` json
{
  "state": "auto_repair_v2",
  "result": {}
}
```

`state`は`"not_repaired" | "auto_repair_v2"`だけを許可する。`auto_repair_v2`の`result`は
24.7のexact `AIReadingRepairResultV2.to_dict()` snapshot、`not_repaired`の`result`はnullとする。
booleanによる曖昧なrepair状態を禁止する。

`repair_result` supplied時は次をすべて満たさなければならない。

-   `repair_result.status == "pass"`
-   `repair_result.final_ai_reading == ai_reading`
-   `repair_result.final_quality_report.to_dict() == quality_report.to_dict()`
-   attempt logが1件または2件
-   first log `before_hash`が`repair_result.initial_ai_reading`の24.6 hashと一致する
-   final log `after_hash`が`ai_reading`の24.6 hashと一致する
-   2 logsの場合、log 1 `after_hash ==` log 2 `before_hash`
-   `target_finding_ids`がinitial report内のauto-repairable finding IDをinitial report orderで保持する
-   各logのattempt number、issue code order、hash、resultが§24.7を満たす

`repair_result` absent時は`state == "not_repaired"`とし、repair historyを推測、復元または空arrayで
代用しない。

### 25.4 Exact metadata schema

`metadata`は次の順序でexactly 12 fieldを持つ。
下のJSONは`not_repaired`のvalid enum choiceを使ったfield / orderを示す。`"..."`と
`{}`は実際のowner value / 25.4 exact nested mappingに置換すべき説明用placeholderであり、
そのままvalid Product instanceではない。

``` json
{
  "product_version": "reading_product_v2",
  "engine_version": "...",
  "reading_context_schema": "reading_context_v2",
  "ai_reading_version": "ai_reading_v2",
  "ai_generation_method": "...",
  "quality_gate_version": "ai_reading_quality_report_v2",
  "quality_status": "pass",
  "generated_at": "2026-01-01T00:00:00+09:00",
  "recalculates_astrology": false,
  "rewrites_ai_reading": "none",
  "snapshot_hashes": {},
  "source_bundle_sha256": "..."
}
```

-   `engine_version`は`engine_result["engine_metadata"]["engine_version"]`、
    `reading_context["engine_version"]`、`ai_reading["engine_version"]`の共通するnon-empty exact string。
    いずれかがnull / missing / non-string、または相互不一致の場合はProductを構築しない。
-   `reading_context_schema == reading_context["schema_version"] == "reading_context_v2"`。
-   `ai_reading_version == ai_reading["version"]`。
-   `ai_generation_method == ai_reading["method"]`。
-   `quality_gate_version == quality_report["version"]`。
-   `quality_status == quality_report["decision"] == "pass"`。
-   `generated_at`はcaller-supplied timezone-aware `datetime`を`isoformat(timespec="seconds")`で表したstring。
    `tzinfo is None`、`utcoffset() is None`、または`microsecond != 0`をrejectする。timezone変換または
    現在時刻補完を行わない。
-   `recalculates_astrology` is exactly `false`。
-   `rewrites_ai_reading`はrepair history stateとexact matchする`"none" | "auto_repair_v2"`。

`snapshot_hashes`は次の順序でexactly 5 fieldを持ち、値は24.6で算出したlowercase SHA-256とする。

``` json
{
  "engine_result": "...",
  "reading_context": "...",
  "ai_reading": "...",
  "quality_report": "...",
  "repair_history": "..."
}
```

`source_bundle_sha256`は次のexact mappingを24.6でhashした値とする。
下の`{}`はhash inputのordered fieldを示す説明用placeholderであり、実際の
hash inputではProductがdeep-snapshotした対応field値に置換する。

``` json
{
  "engine_result": {},
  "reading_context": {},
  "ai_reading": {},
  "quality_report": {},
  "repair_history": {}
}
```

snapshot hashとbundle hashはProduct内のexact snapshotsが一緒にpackageされたことと、構築後の
置換を検出する。とくにembedded `ai_reading`とembedded `quality_report`のその組を
Product構築後に改変していないことを証明する。

このhashは、embedded Quality Reportが過去にそのexact AIReading snapshotをQuality Gateで
評価して生成されたことまでをcryptographically証明しない。v1.2 Productが検証できるのは、
両owner contract、PASS / completed state、frozen owner contract上すでに表現できるidentity /
source-contract relationship、および本節のsnapshot / bundle invariantに限る。

歴史的な実行provenanceはcanonical application pipeline
`Generator v2 -> Quality Gate v2 -> PASS -> ReadingProductV2 builder`が保証する運用境界であり、
ReadingProductV2 v1.2のcryptographic proof responsibilityの範囲外とする。Productはそれより強い
provenanceをclaimしない。QualityReportV2にAI snapshot hash、`evaluated_ai_sha256`、source hash、
provenance hashその他のnew fieldを追加せず、Product builderもQuality Gateを再実行しない。
このexplicit binding hashをQualityReport側に持たせる変更は将来の別contract / versionに限る。

### 25.5 PASS-only construction and validation order

ReadingProductV2はfinal `quality_report.decision == "pass"`の場合だけ構築する。
`review`または`fail`ではvalidation errorをraiseし、blockedまたはpartial Productを返さない。

validation orderをexactly次に固定する。

1.  four source inputのtype、plain JSON、finite numberを検証する。
2.  Reading Context v2をowner validatorで検証する。
3.  AIReadingV2のexact final identity、`status == "completed"`、`validation.valid == true`を検証する。
4.  Quality Report v2をowner dataclass contractで検証し、`status == "completed"`および
    `decision == "pass"`を検証する。
5.  Quality Reportの`input_contracts.ai_reading_v2`がembedded AIReadingV2の
    `schema_version`、`version`、`method`、`status`、`engine_version`のexact projectionと一致し、
    `input_contracts.reading_context_v2`がembedded Reading Contextの`schema_version`、`version`、
    `method`、`status`のexact projectionと一致することを検証する。
6.  Quality Reportの`input_contracts.common_judgment_metadata_v1`がAIReadingV2
    `source_contracts.judgment_metadata`のidentityとexact matchすることを検証する。
7.  AIReadingV2 `source_contracts.reading_context`がReading Context snapshotのidentityとexact matchすることを検証する。
8.  engine versionが25.4のexact owner paths間で一致することを検証する。
9.  PASS-only preconditionを検証する。
10. repair historyと25.3のconsistencyを検証する。
11. `generated_at`を25.4で検証する。
12. source snapshotsをdeep copyし、snapshot hashとbundle hashを算出する。
13. final Productを構築し、exact top-level / metadata / repair shapeを再検証する。

mismatch、missing field、hash inconsistency、non-PASS report、repair provenance inconsistencyは
`ReadingProductV2ValidationError`とする。builderはQuality Gateを再実行しない、decisionを変更しない、
占術計算を行わない、AI proseを書き換えない、missing sourceを補完しない。
Judgment Metadata、Prompt request、SemanticAssessor、provider responseまたはその他の5番目の
source snapshot / dependencyを、historical Quality Gate executionを証明する目的で追加しない。

### 25.6 Publication and compatibility boundary

v1.2では`pass`だけがpublication eligibleとする。`review`と`fail`はpublication prohibited。
human approval override contractをv1.2に追加しない、REVIEWをPASSへ変更しない、human approvalで
Quality Gateをbypassしない。

publication state transitionをexactly次に固定する。

``` text
QualityReport pass
  -> ReadingProductV2 construction eligible
  -> PDF v2 generation eligible

QualityReport fail + all blocking findings auto-repairable
  -> Auto-Repair v2 eligible
  -> rerun Quality Gate
  -> final passの場合だけReadingProductV2 construction eligible

QualityReport review
or non-auto-repairable fail
or exhausted repair result
  -> ReadingProductV2 construction prohibited
  -> PDF v2 generation / publication prohibited
```

ReadingProductV2導入を理由にReadingProduct v1、v1 renderer、v1 PDF、v1 APIまたはv1 Goldenを
変更しない。

------------------------------------------------------------------------

## 26. PDF鑑定書 V2

### 26.1 Owner, identity, and input boundary

HTML renderer ownerを新規`engine/reading_renderer_v2.py`、PDF ownerを新規
`engine/reading_pdf_v2.py`とする。v1 modulesを変更しない。

identity literalをexactly次に固定する。

``` text
READING_RENDERER_V2_VERSION = "reading_renderer_v2"
READING_RENDERER_V2_METHOD = "reading_renderer_v2"
READING_RENDERER_V2_STATUS = "ready"
READING_PDF_V2_TEMPLATE_VERSION = "reading_pdf_template_v2"
READING_PDF_V2_VERSION = "reading_pdf_v2"
READING_PDF_V2_METHOD = "html_to_pdf_playwright_chromium_v2"
READING_PDF_V2_STATUS = "ready"
```

rendererとPDFの唯一のauthoritative content inputは`ReadingProductV2`とする。Engine Result、
Reading Context、AIReadingV2、Quality Reportを別argumentで受け取るalternate pathを禁止する。
Productの`status == "ready_for_publication"`、`quality_report.decision == "pass"`、metadata
`quality_status == "pass"`、snapshot / bundle hash consistencyをrender前に検証する。

### 26.2 Public renderer and PDF APIs

public signatureをexactly次に固定する。

``` python
def render_reading_product_v2_html(
    product: ReadingProductV2,
    *,
    document_title: str | None = None,
    include_css: bool = True,
) -> str:
    ...

async def write_reading_product_v2_pdf_async(
    product: ReadingProductV2,
    output_path: str | Path,
    *,
    document_title: str | None = None,
    page_format: str = "A4",
    print_background: bool = True,
    prefer_css_page_size: bool = True,
    timeout_ms: int = 30000,
) -> Path:
    ...

def write_reading_product_v2_pdf(
    product: ReadingProductV2,
    output_path: str | Path,
    *,
    document_title: str | None = None,
    page_format: str = "A4",
    print_background: bool = True,
    prefer_css_page_size: bool = True,
    timeout_ms: int = 30000,
) -> Path:
    ...

async def render_reading_product_v2_pdf_bytes_async(
    product: ReadingProductV2,
    *,
    document_title: str | None = None,
    page_format: str = "A4",
    print_background: bool = True,
    prefer_css_page_size: bool = True,
    timeout_ms: int = 30000,
) -> bytes:
    ...

def render_reading_product_v2_pdf_bytes(
    product: ReadingProductV2,
    *,
    document_title: str | None = None,
    page_format: str = "A4",
    print_background: bool = True,
    prefer_css_page_size: bool = True,
    timeout_ms: int = 30000,
) -> bytes:
    ...
```

sync APIをrunning event loopから呼び出した場合は、nested loopまたはthreadへ暗黙fallbackせず
`ReadingPdfV2GenerationError`をraiseしasync APIの使用を要求する。
`output_path`は`.pdf`のみを許可する。parent directoryはPDF writerが作成できるが、既存の
non-directory parent、write failure、empty fileをgeneration errorとする。

argument validationを次に固定する。`document_title`がnullの場合はliteral
`"八雲式四柱推命 鑑定書"`を使用し、non-nullの場合はnon-empty / non-whitespace stringだけを許可して
内容をnormalizeしない。v1.2の`page_format`はliteral `"A4"`だけを許可する。
`include_css`、`print_background`、`prefer_css_page_size`はexact built-in boolean、`timeout_ms`は
booleanを含まないpositive built-in integerとする。invalid argumentはprovider / Chromiumを起動する前に
`ReadingPdfV2ValidationError`とする。

### 26.3 Mandatory visible content and order

可視content sectionを次の順序に固定する。applicable sourceが空の場合もheadingを暗黙に
削除せず、contract上optionalと明示された「相談への回答」だけpresenceに応じて出力する。

1.  表紙
2.  基本情報
3.  命式
4.  日主
5.  五行
6.  月令・通根
7.  身強身弱
8.  干支関係
9.  格局
10. 用神
11. 本質・性格
12. 仕事・適職
13. 金運
14. 恋愛・人間関係
15. 健康傾向
16. 現在大運
17. 現在歳運
18. 今後の流れ
19. 長期大運
20. 総合アドバイス
21. 相談への回答（`consultation_answer != null`の場合だけ）
22. 注意事項・免責

source ownershipを次に固定する。

-   表紙、基本情報、命式、日主、五行、月令・通根、身強身弱、干支関係、格局、用神、
    現在大運、現在歳運、長期大運の計算値はProduct内のEngine Result / Reading Context snapshotから
    表示し、rendererが再計算しない。
-   AI section、future/yearly flow、総合アドバイス、consultation answerはProduct内のfinal
    AIReadingV2 textをexactly表示し、rewrite、summarize、mergeまたは補完しない。
-   `future_flow.yearly`はProduct内のyear orderを保持し、attached yearを各yearly entryと一緒に表示する。
-   non-null `consultation_answer`は専用の「相談への回答」sectionに表示し、他sectionに暗黙mergeしない。
-   visible warning / uncertaintyの唯一のauthorityはProduct内のfinal AIReadingV2 top-level
    `warnings`および`uncertainty` catalogとする。それぞれのarray orderとentry内のexact valueを
    維持して「注意事項・免責」に表示し、deduplicate、sort、Reading Context catalogとの
    merge / concatenation、severity rewrite、message rewriteまたは補完を行わない。Reading Contextの
    warning / uncertaintyはProduct invariantですでに必要なvalidation / cross-checkにだけ用い、
    第二のvisible catalogとして表示しない。
-   `birth_time_status.known == false`では、hour pillarが不明であること、three-pillar / known-pillars-only
    scope、timing uncertaintyに対応するfinal AIReadingV2 catalog entryを「注意事項・免責」に
    visibleに表示する。hourを補完しない。AIReadingV2 / Reading Context preservation invariantが
    崩れている場合、Product / rendererは文言を補完または修復せずvalidation errorとする。
-   disclaimerはfinal AIReadingV2のtrusted disclaimerを「注意事項・免責」にexactly表示し、
    fallback disclaimerへ置換しない。

### 26.4 Canonical HTML and provenance metadata

`render_reading_product_v2_html()`の戻り値はUTF-8でserialize可能なcomplete HTML documentとし、
`<!DOCTYPE html>`を持つ。同じProductと同じargumentsからbyte-for-byte同じHTML stringを返す。
現在時刻、random ID、network resource、provider call、filesystem contentをrendering inputにしない。

HTMLは次の7項目のinternal provenance metadataを`<meta>`に保持する。各valueは
Product metadataおよび本節のidentity constantからexact-copyし、これらを顧客向けproseへ
混入させない。

-   engine version
-   Reading Context schema
-   AI Reading version / method
-   Quality Gate version / decision
-   ReadingProduct version
-   PDF template versionはowner constant
    `READING_PDF_V2_TEMPLATE_VERSION == "reading_pdf_template_v2"`
-   Product `source_bundle_sha256`

HTML escapeを行い、API key、system/user prompt、provider raw response、usage、response IDをvisible contentまたは
HTML metadataへ出力しない。

### 26.5 PDF generation, failures, and non-goals

PDF backendはPlaywright Chromiumによるcanonical HTMLのprintとする。rendererまたはPDF moduleは
占術計算、AI prose rewrite、repair、Quality Gate decision override、AI provider callを行わない。

`engine/reading_pdf_v2.py`は次のexact public exception hierarchyを所有する。これ以外の
public PDF v2 exception subclassをv1.2に追加しない。v1 PDFのexceptionを変更しない。

``` python
class ReadingPdfV2Error(Exception): ...
class ReadingPdfV2ValidationError(ReadingPdfV2Error): ...
class ReadingPdfV2DependencyError(ReadingPdfV2Error): ...
class ReadingPdfV2GenerationError(ReadingPdfV2Error): ...
```

public HTML rendererとPDF APIのinput / argument / Product invariant failureは
`ReadingPdfV2ValidationError`。Playwright import failure、Chromium不在または起動失敗は
`ReadingPdfV2DependencyError`。renderer execution failure、timeout、file write failure、invalid /
empty PDF backend outputは`ReadingPdfV2GenerationError`とする。sync APIのrunning-event-loop failureは
26.2どおり`ReadingPdfV2GenerationError`とする。

file outputは存在、regular file、size > 0、prefix `%PDF`を検証する。bytes outputもnon-emptyかつ
prefix `%PDF`を検証する。invalid / empty outputをsuccessful artifactとして返さない。

typography、color、marginその他のvisual stylingは、readability、content preservation、section orderまたは
securityを壊さない限りv1.2 frozen content contractに含めない。レイアウト変更と占術ルール変更を
同一PRで大量に混ぜない。

### 26.6 PDF Golden authority

machine regression authorityはexact ReadingProductV2 JSONと26.4のcanonical HTML / content structureとする。
Chromiumが再生成したPDF bytesのenvironment間bit-for-bit equalityを要求しない。

committed/reference PDFは30.6に従ってmanifestのsize、SHA-256、human visual review recordへbindする。
SHA-256はcommitted artifact自体の完全性を検査するもので、別environmentでの再生成bytes一致を
意味しない。visual reviewはmandatory section、切れ、重なり、文字化け、warning / uncertainty、
unknown-hour notice、disclaimer、future/yearly、consultation sectionの保持を確認する。

------------------------------------------------------------------------

## 27. API V2

### 27.1 Scope and schema owner

v1.2でfreezeするのはtransport-neutralなAPI v2 metadata / success envelope / error envelope contractである。
schema ownerは将来のopt-in `api/reading_contract_v2.py`とする。public HTTP route、router registration、
authentication、storage、download URLは本節のv1.2必須実装に含めない。

identity literalをexactly次に固定する。

``` text
READING_API_V2_SCHEMA_VERSION = "reading_api_envelope_v2"
READING_API_V2_ERROR_SCHEMA_VERSION = "reading_api_error_v2"
READING_API_V2_VERSION = "v2"
```

### 27.2 Success envelope

success envelopeは次の順序でexactly 11 fieldを持つ。すべてREQUIRED、unknown field禁止。
下のJSONはtransport-neutral outer / nested envelope fieldの説明用fragmentであり、
`reading_product: {}`は§25のcomplete owner-valid snapshotと置換すべきplaceholderである。
そのままvalid success envelope instanceではない。

``` json
{
  "schema_version": "reading_api_envelope_v2",
  "api_version": "v2",
  "engine_version": "...",
  "schema_versions": {
    "reading_context": "reading_context_v2",
    "ai_reading": "ai_reading_v2",
    "quality_report": "ai_reading_quality_report_v2",
    "reading_product": "reading_product_v2",
    "pdf": "reading_pdf_v2"
  },
  "rule_versions": {
    "rule_version": "1.2"
  },
  "quality": {
    "version": "ai_reading_quality_report_v2",
    "status": "completed",
    "decision": "pass"
  },
  "publication": {
    "eligible": true,
    "reason": "quality_gate_pass"
  },
  "reading_product": {},
  "pdf_artifact": null,
  "warnings": [],
  "uncertainty": []
}
```

-   `engine_version`はReadingProductV2 metadataからexact-copyするnon-empty string。
-   `schema_versions`は記載順のexactly 5 field。PDF artifactがnullでも`pdf` versionを保持する。
-   `rule_versions`はexactly `rule_version` 1 fieldを持ち、embedded Productの
    `engine_result["engine_metadata"]["rule_version"]` non-empty stringをexact-copyする。
-   `quality`は記載順のexactly 3 fieldで、embedded ProductのQuality Reportとexact matchする。
-   ProductがPASS-onlyであるため`publication`はexactly
    `{"eligible":true,"reason":"quality_gate_pass"}`とする。REVIEW / FAIL envelopeをsuccessとして構築しない。
-   `reading_product`はexact ReadingProductV2 snapshot。
-   `warnings`と`uncertainty`はembedded `ai_reading`のcatalogをorderを変更せずdeep-copyする。

`pdf_artifact`はnullまたは次の順序でexactly 4 fieldのmappingとする。
下のJSONはschema-valid field / type exampleであり、actual `size`と`sha256`は
対応するPDF bytesとexact matchしなければならない。

``` json
{
  "type": "pdf",
  "media_type": "application/pdf",
  "size": 1,
  "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
}
```

`size`はpositive integer。`sha256`はlowercase 64-character SHA-256。filesystem path、signed URL、
storage key、raw bytesは本metadata objectに含めない。

### 27.3 Error envelope

error envelopeは次の順序でexactly 3 fieldを持つ。

``` json
{
  "schema_version": "reading_api_error_v2",
  "api_version": "v2",
  "error": {
    "code": "generation_error",
    "message": "処理を完了できませんでした。",
    "stage": "quality_gate",
    "request_id": null
  }
}
```

`error`は`code`、`message`、`stage`、`request_id`の順序でexactly 4 field。

-   `code`は`"input_error" | "unsupported" | "calculation_error" | "generation_error"`。
-   `message`は個人情報、API key、prompt、provider raw response、Python exception textを含まないpublic string。
-   `stage`は`"input" | "calculation" | "reading_context" | "judgment_metadata" | "prompt" |
    "generation" | "quality_gate" | "repair" | "product" | "pdf" | "publication" | null`。
-   `request_id`はnon-empty stringまたはnull。

HTTP status mapping、route path、request modelはHTTP v2 route freezeまで本節のcontract外とする。

### 27.4 Contract builder and compatibility

transport-neutral builderを実装する場合のpublic signatureは次とする。

``` python
def build_reading_api_v2_envelope(
    product: ReadingProductV2,
    *,
    pdf_artifact: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    ...

def build_reading_api_v2_error_envelope(
    *,
    code: str,
    message: str,
    stage: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    ...
```

builderはProductのPASS/publication/hash invariantとoptional PDF artifact metadataを検証し、deep-copyした
JSON-safe envelopeを返す。占術計算、AI generation、Quality Gate、PDF generationを実行しない。
error builderは27.3のallowlist / type / public-message constraintsだけを検証し、exception textを
messageへ自動変換しない。両builderはinput mappingを変更せず、current timeを追加しない。
success envelopeの`engine_version`、`schema_versions`、`rule_versions`とembedded Productにより、
response単体から使用したengine / rule / source schemaを追跡可能にする。

breaking changeはAPI versionを分離する。v1.1互換が必要な場合は将来のHTTP layerでadapterを設ける。
`api/reading_routes.py`、`reading_api_v1`、existing request / response modelを変更しない。
public HTTP v2 routeはcomprehensive v1.2 engine / product releaseの必須条件ではなく、
28.2のexternal-release separationに従うpost-v1.2 product integrationとする。

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

### 28.1 Version Source Policy

各versionの役割とsource of truthを次のとおり分離する。

| version | role | source of truth |
|---|---|---|
| `ENGINE_VERSION` | engine release compatibility version | `engine/version.py` |
| `RULE_VERSION` | engine-wide aggregate rule baseline | `engine/version.py` |
| component version | component独自rule/schema version | component owner moduleのexplicit constantおよびraw output |
| method | algorithm identifier。versionではない | component owner module |
| schema version | payload contract version | schema owner |
| API version | external transport contract | API owner |
| Golden version | regression artifact namespace | Golden wrapperおよびmanifest |

component sourceに独立したversionが存在しない場合は`version: null`とする。method suffixからのversion parsing、および`ENGINE_VERSION`または`RULE_VERSION`によるcomponent versionの代用は禁止する。

### 28.2 Common Judgment Metadata Migration

Common Judgment MetadataのmigrationはOption D Hybridを採用する。Big Bang migrationは禁止する。

#### Phase 1 --- v1.2

Option Bのopt-in metadata adapterだけを追加する。

-   adapter
-   strict validator
-   explicit source registry
-   explicit legacy-status mapping registry
-   existing raw component output変更なし
-   consumer変更なし
-   Golden変更なし

AI Reading v2へ進む前に、Common Judgment Metadata spec freeze、opt-in adapter、strict validator、source registry、explicit legacy-status mapping、`current_luck_resolved`をcanonical `resolved`へmappingしないtest、missing version=`null` test、suffix inference禁止test、evidence semantics test、warnings / uncertainty exact-copy testを完了する。

#### Phase 2 --- AI Reading v2

AI Reading v2は`reading_context_v2`とCommon Judgment Metadataを別contractとしてconsumeする。既存v1 consumerを一括切替してはならない。

#### Phase 3 --- v1.3+

必要に応じてversioned judgment outputへcomponent単位で段階移行する。

次はv1.3以降へdeferできる。

-   existing component outputへのversion追加
-   raw status rename
-   全componentへの空warnings / uncertainty追加
-   evidence shape統一
-   branch relation全面共通化
-   versioned component Golden
-   v1 output migration

API v2公開はAI Reading v2の外部公開工程まで分離できる。

### 28.3 v1.1 Compatibility

Common Judgment Metadata導入を理由に、`tests/golden/v1_1/**`、`reading_context_v1`、`reading_api_v1`、`reading_product_v1`またはexisting v1 API contractを変更してはならない。initial adapterはraw sourceを変更しない。

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
9.  ReadingProduct Contract Test
10. PDF End-to-End Test
11. Golden Artifact Verification Test
12. Security / Privacy Test

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

### 30.3 Golden Artifact共通contract

v1.2 Golden Artifactはhuman-reviewed regression artifactであり、runtime astrology evidence、
trusted calculation source、AI grounding sourceまたはprovider substituteではない。Goldenの存在を理由に
新しい占術値、fact、reference、warning、uncertaintyまたはQuality Gate PASSを生成してはならない。

Goldenは`tests/golden/v1_2/`配下に置き、各artifact categoryは`manifest.json`を持つ。
manifestは次の順序でexactly 5 fieldを持つ。
下のJSONは`ai_reading_v2` categoryのschema-valid exampleである。actual manifestの
`size`と`sha256`はcommitted bytesから算出した値へ置換する。

``` json
{
  "schema_version": "golden_artifact_manifest_v2",
  "version": "golden_artifact_v2",
  "artifact_type": "ai_reading_v2",
  "file_count": 2,
  "files": [
    {
      "artifact_id": "GC03:ai_reading_v2",
      "path": "GC03_1984_fukuoka_male_afternoon_ai_reading_v2.json",
      "size": 1,
      "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
    },
    {
      "artifact_id": "GC10:ai_reading_v2",
      "path": "GC10_1985_ishikawa_female_unknown_birth_time_ai_reading_v2.json",
      "size": 1,
      "sha256": "1111111111111111111111111111111111111111111111111111111111111111"
    }
  ]
}
```

`artifact_type`はenumであり、allowed literalはexactly
`"ai_reading_v2" | "reading_product_v2" | "pdf_v2"`の3つとする。
AI Reading、ReadingProduct、PDFのcategory manifestはそれぞれ対応する単一literalを使い、
pipe-concatenated stringをvalueとして使ってはならない。

`files` entryは次の順序でexactly 4 fieldを持つ。下のentryはfield / typeの
schema-valid exampleであり、actual integrity valueはcommitted fileとexact matchしなければならない。

``` json
{
  "artifact_id": "GC03:ai_reading_v2",
  "path": "GC03_1984_fukuoka_male_afternoon_ai_reading_v2.json",
  "size": 1,
  "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
}
```

-   `artifact_id`はcategory内でuniqueなnon-empty string。
-   `path`はmanifest directoryからのrelative POSIX path。absolute path、`..`、backslashを禁止する。
-   `size`はcommitted fileのbyte lengthとexact matchするpositive integer。
-   `sha256`はcommitted file bytesのlowercase 64-character SHA-256とexact matchする。
-   `files`は`artifact_id`のUnicode code point ascending order、`file_count == len(files)`とする。
-   manifest自身を`files`へ含めない。

JSON GoldenはUTF-8、trailing newline 1個、duplicate keyなし、finite plain JSON valueだけを許可し、
parse後のcanonical comparisonには24.6のserializationを用いる。human review timestampをtest実行時に
更新せず、reviewed artifactの固定recordとして扱う。

### 30.4 AI Reading v2 Golden

AI Reading v2 Golden rootは`tests/golden/v1_2/ai_reading_v2/`とし、minimum caseをexactly次の
2 fixture familyとする。

1.  `GC03_1984_fukuoka_male_afternoon`
2.  `GC10_1985_ishikawa_female_unknown_birth_time`

case filenameはそれぞれ
`GC03_1984_fukuoka_male_afternoon_ai_reading_v2.json`、
`GC10_1985_ishikawa_female_unknown_birth_time_ai_reading_v2.json`に固定し、manifest
`file_count == 2`とする。

各case JSONは次の順序でexactly 9 fieldを持つ。
下のJSONはouter / nested field ownershipの説明用fragmentであり、`{}`は
参照するowner contractのcomplete snapshotと置換すべきplaceholderである。そのまま
valid Golden instanceとはみなさない。

``` json
{
  "schema_version": "ai_reading_v2_golden_v1",
  "version": "ai_reading_v2_golden_v1",
  "case_id": "GC03",
  "source_references": {
    "chart_fixture_id": "GC03_1984_fukuoka_male_afternoon",
    "reading_context_fixture": "tests/golden/v1_2/reading_context/GC03_1984_fukuoka_male_afternoon_consultation_reading_context_v2.json",
    "target_datetime": "2026-08-10T15:36:00+09:00",
    "consultation_context": {}
  },
  "provider_model": "test-model",
  "provider_response": {},
  "ai_reading": {},
  "quality_report": {},
  "human_review": {}
}
```

`source_references`は次の順序でexactly 4 fieldを持つ。

1.  `chart_fixture_id`: section冒頭のfixture family IDとexact matchするstring。
2.  `reading_context_fixture`: `tests/golden/v1_2/reading_context/`配下のsame-case owner-valid Golden path。
    GC03はnon-null consultationを含む上記consultation-bound fixture、GC10はexisting unknown-hour fixtureとする。
3.  `target_datetime`: timezone-aware ISO 8601 string。fixed inputでありcurrent timeを使用しない。
4.  `consultation_context`: public `build_consultation_context()`のowner-valid exact output snapshotまたはnull。
    GC03はnon-null、GC10はnullとし、referenced Reading Contextの`consultation`とexact matchさせる。

`provider_model`はliteral `"test-model"`。`provider_response`はGenerator v2へ1回だけ返すdeterministicな
model-owned payloadであり、final trusted wrapper fieldを含めない。`ai_reading`はそのresponseとsourceから
public Generator v2が構築したfinal AIReadingV2 snapshot、`quality_report`はdeterministic test assessorで
public Quality Gate v2を実行したcompleted / zero-finding / `decision == "pass"` reportとする。
live provider、network、API key、current time、environment-selected modelをGolden生成またはverificationに
使用してはならない。

Golden verificationのtest-only `SemanticAssessorV2`はidentityとoutputをexactly次に固定する。

``` text
method = "golden_semantic_assessor_v1"
version = "v1"
```

``` json
{
  "status": "completed",
  "findings": []
}
```

このassessorはprovider-independentなtest-only fakeであり、production concrete SemanticAssessorではない。
`method`と`version`はpublic Quality Gate v2の`semantic_assessment`へexact-copyされ、Golden
QualityReportのcanonical JSONとSHA-256を安定させる。Golden生成 / verificationは毎回この
same identity / outputを使い、liveまたはproduction assessorへfallbackしない。

`human_review`は次の順序でexactly 5 fieldを持つ。

``` json
{
  "status": "approved",
  "reviewer": "reviewer-id",
  "reviewed_at": "2026-01-01T00:00:00+09:00",
  "scope": "ai_reading_v2_prose_and_contract",
  "notes": []
}
```

`reviewer`はnon-empty string、`reviewed_at`はtimezone-aware ISO 8601 seconds、`notes`はarray of string。
このreviewはprose / contract / expected coverageの承認記録であり、runtime Quality Gate decision overrideではない。

GC03は少なくともfour pillars、current luck、future/yearly flow、exact numeric / luck grounding、
non-null consultation answer、clean PASSを同じintegrated artifactでcoverする。GC10はunknown hour、
null hour pillar、warning / uncertainty exact preservation、three-pillar / known-pillars-only wording、clean PASSをcoverする。

### 30.5 ReadingProduct v2 Golden

ReadingProduct v2 Golden rootは`tests/golden/v1_2/reading_product_v2/`とし、minimum casesはGC03とGC10とする。
case filenameは30.4のfixture family nameにsuffix `_reading_product_v2.json`を付けたものとし、
manifest `file_count == 2`とする。
各case JSONは次の順序でexactly 7 fieldを持つ。
下のJSONはouter field ownershipの説明用fragmentであり、`{}`は§25または30.4の
complete snapshotと置換すべきplaceholderである。そのままvalid Golden instanceではない。

``` json
{
  "schema_version": "reading_product_v2_golden_v1",
  "version": "reading_product_v2_golden_v1",
  "case_id": "GC03",
  "source_ai_reading_golden": "...",
  "generated_at": "2026-01-01T00:00:00+09:00",
  "reading_product": {},
  "human_review": {}
}
```

`source_ai_reading_golden`は30.4のsame-case repository-relative path、`generated_at`はProductに渡した
fixed caller-supplied timestampとexact matchする。`reading_product`は§25 public builderのexact outputで、
4 source snapshot、repair state、snapshot hashes、bundle hashを含む。GC03 / GC10いずれも
`repair_history.state == "not_repaired"`をminimum baselineとし、Auto-Repair provenance Goldenは追加caseとしてよい。

`human_review`は30.4と同じfield order / typeを使い、`scope`だけliteral
`"reading_product_v2_contract_and_content"`とする。verificationはsource GoldenからProductを再構築し、
canonical Product JSON、individual snapshot hash、bundle hash、PASS-only invariantをexact比較する。

### 30.6 PDF v2 Golden

PDF v2 Golden rootは`tests/golden/v1_2/pdf_v2/`とし、minimum casesはGC03とGC10とする。
各caseは少なくとも次の3 committed artifactを持つ。

1.  §26.4のcanonical UTF-8 HTML。
2.  human-reviewed reference PDF。
3.  visual review JSON。

filenameは30.4のfixture family nameへそれぞれ`.html`、`.pdf`、`_visual_review.json`を付けたものに固定し、
manifestは6 fileすべてを列挙して`file_count == 6`とする。

visual review JSONは次の順序でexactly 7 fieldを持つ。

``` json
{
  "schema_version": "pdf_v2_visual_review_v1",
  "version": "pdf_v2_visual_review_v1",
  "case_id": "GC03",
  "status": "approved",
  "reviewer": "reviewer-id",
  "reviewed_at": "2026-01-01T00:00:00+09:00",
  "checks": {
    "mandatory_sections": "pass",
    "no_clipping": "pass",
    "no_overlap": "pass",
    "no_mojibake": "pass",
    "warnings_uncertainty": "pass",
    "unknown_hour_notice": "pass",
    "disclaimer": "pass",
    "future_yearly": "pass",
    "consultation_answer": "pass"
  }
}
```

`checks`は次の順序でexactly 9 fieldを持つ。各valueは`"pass" | "not_applicable"`。

1.  `mandatory_sections`
2.  `no_clipping`
3.  `no_overlap`
4.  `no_mojibake`
5.  `warnings_uncertainty`
6.  `unknown_hour_notice`
7.  `disclaimer`
8.  `future_yearly`
9.  `consultation_answer`

applicable itemは`"pass"`必須。GC03の`future_yearly`と`consultation_answer`、GC10の
`warnings_uncertainty`と`unknown_hour_notice`は`"not_applicable"`にしてはならない。
renderer regressionはsame-case ReadingProductからcanonical HTMLを再生成してexact compareする。
Golden HTML regenerationは`document_title=None`、`include_css=True`のdefault argumentsを使用する。
reference PDF generationも26.2のdefault `document_title`、`page_format`、`print_background`、
`prefer_css_page_size`を使用し、renderer / PDF versionをvisual review recordと同じcommitで固定する。
reference PDFはmanifestのsize / SHA-256でintegrityを検査し、human visual review recordと一緒に保持するが、
別environmentで再生成したChromium PDF bytesとのbit-for-bit equalityを要求しない。

### 30.7 ルール変更時

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

本節はcomprehensive v1.2 engine / product / publication releaseのmechanical DoDとする。
`[x]`は本spec freeze時点でrepository実物とindependent auditにより完了確認済み、`[ ]`は
release前にartifactまたは実装の完了確認が必要な項目を表す。

### 35.1 Complete already

-   [x] v1.1 baselineと§28.3 compatibility boundaryが固定されている。
-   [x] calculation coreの主要ruleはmethod / version / status、structured evidence、warning / uncertaintyを持つ。
-   [x] 節入り境界、通変星100組、十二運matrix、身強身弱boundary、格局、用神、luck / annual luckの
    frozen regression coverageがある。
-   [x] Golden Chart baselineと承認recordが固定され、既知のintentional differenceが追跡可能である。
-   [x] Reading Context v2 public builder、owner validation、Goldenが固定されている。
-   [x] Common Judgment Metadata adapter / validator contractが実装・検証済みである。
-   [x] Prompt Builder v2がtrusted catalogs / attachments / section contractを構築する。
-   [x] Generator v2がprovider injection、one-call、strict model response、trusted final assemblyを実装する。
-   [x] Quality Gate v2がdeterministic / semantic / numeric checksとfinal PASS / REVIEW / FAIL reportを公開する。
-   [x] AI Reading v2がfacts / interpretation / advice ownershipを分離し、占術を再計算しない。
-   [x] calculationからQuality Gateまでのpublic-function engine-level E2EがGC03 / GC10で検証されている。

### 35.2 Remaining required before comprehensive v1.2 release

-   [ ] §24 Auto-Repair v2、§25 ReadingProduct v2、§26 PDF v2、§27 API v2および§30 Goldenの
    contractがPhase 7.1 independent auditをPASSし、spec freeze commit済みであることを確認する。
-   [ ] Auto-Repair v2を§24どおり実装し、text-only patch、2-attempt limit、no hidden retry、
    Quality Gate rerun、exhausted / typed-exception、immutabilityをtestする。
-   [ ] §30.4のGC03 / GC10 AI Reading v2 Goldenを作成し、human review、manifest size / SHA-256、
    network-independent regeneration testを完了する。
-   [ ] ReadingProduct v2を§25どおり実装し、PASS-only construction、4 snapshots、repair provenance、
    canonical binding hash、caller-supplied timestamp、immutabilityをtestする。
-   [ ] §30.5のGC03 / GC10 ReadingProduct v2 Goldenを作成し、canonical JSON / hash / human reviewを完了する。
-   [ ] renderer / PDF v2を§26どおり実装し、sync / async path / bytes API、ReadingProduct-only input、
    mandatory visible content、failure boundaryをE2E testする。
-   [ ] §30.6のGC03 / GC10 canonical HTML、reference PDF、manifest、human visual reviewを完了する。
-   [ ] GC10のunknown-hour / three-pillar warningとuncertaintyがAI Golden、Product Golden、canonical HTML、
    reference PDFまで保持されることを確認する。
-   [ ] GC03のcurrent luck、future/yearly numeric grounding、consultation answerがAI Golden、Product Golden、
    canonical HTML、reference PDFまで保持されることを確認する。
-   [ ] v1 / v2 full regressionを実行し、重大な未説明failure / errorが0件、xfail / xpass / skip差分が
    説明済みであることを確認する。
-   [ ] v1.2 changelog、既知制約、sample customer readingおよびGolden差分reviewを完了する。
-   [ ] 付録Dのrelease checklistを満たし、versionを固定して`v1.2.0` release tagを作成する。

### 35.3 Post-v1.2 / not required for this DoD

次はcomprehensive v1.2 engine / product / publication releaseの完了条件に含めない。

-   public HTTP v2 route、router registration、deployment-specific authentication / storage。
-   UI。
-   provider-specific concrete `SemanticAssessorV2` implementation。Protocol / injected boundaryはv1.2 contractとする。
-   live-provider GoldenまたはGolden test中のnetwork / API key使用。
-   REVIEWを公開可能にするhuman approval artifact / override。

### 35.4 Completion rule

v1.2完成と宣言できるのは、35.2と付録Dの全itemが完了し、§24〜§27 / §30のindependent contract audit、
implementation audit、final regression auditで未解決HIGH / MEDIUMが0件、remaining ambiguityがない場合だけとする。
35.3 itemの未実装をv1.2 blockerとして扱わず、逆に35.3を理由に35.2 itemを省略してはならない。

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
