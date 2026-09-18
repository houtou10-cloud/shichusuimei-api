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
    "source_fact_codes": {"$ref": "#/$defs/fact_code_array"},
    "source_components": {"$ref": "#/$defs/source_component_array"},
    "warnings": {"$ref": "#/$defs/warning_id_array"},
    "uncertainty": {"$ref": "#/$defs/uncertainty_id_array"}
  },
  "required": [
    "text",
    "source_fact_codes",
    "source_components",
    "warnings",
    "uncertainty"
  ],
  "additionalProperties": false
}
```

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

JSON Schema validationだけでfinal validityを確定してはならない。global component enumは
scope-specific luck validityを表現しないため、schema validation後に22.12のblock scope、
source component、`luck_value_source_entry`の一致をsemantic validationしなければならない。

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
`grounded_text_block`とする。各blockはexactly次の5 fieldをREQUIREDとして持つ。

``` json
{
  "text": "...",
  "source_fact_codes": [],
  "source_components": [],
  "warnings": [],
  "uncertainty": []
}
```

-   `text`はstringとする。
-   `source_fact_codes`はtrusted dynamic enum内のfact codeだけを持つarray of stringとする。
-   `source_components`は§4のregistered Common Judgment componentだけを持つarray of stringとする。
-   `warnings`は22.10のtop-level warning catalogにresolveするwarning IDだけを持つarray of stringとする。
-   `uncertainty`は22.10のtop-level uncertainty catalogにresolveするuncertainty IDだけを持つ
    array of stringとする。
-   astrology claimを含むblockでは、`source_fact_codes`と`source_components`の両方を
    emptyにしてはならない。
-   pure practical adviceであり、engine calculationまたはastrology claimとして表現しない
    blockに限り、両source arrayをemptyにできる。
-   v1.2はblock単位のtraceabilityを要求し、sentence分割によるperfect semantic verificationは
    要求しない。

`future_flow`以外の7 sectionは、次のfieldだけをすべてREQUIREDとして持つ。

``` json
{
  "section_id": "core_personality",
  "title": "本質・性格",
  "facts": ["day_master.stem"],
  "summary": {
    "text": "...",
    "source_fact_codes": ["day_master.stem"],
    "source_components": ["five_elements"],
    "warnings": [],
    "uncertainty": []
  },
  "detail": {
    "text": "...",
    "source_fact_codes": ["day_master.stem"],
    "source_components": ["five_elements"],
    "warnings": [],
    "uncertainty": []
  },
  "evidence": [
    {
      "text": "...",
      "source_fact_codes": ["day_master.stem"],
      "source_components": ["five_elements"],
      "warnings": [],
      "uncertainty": []
    }
  ],
  "interpretation": [
    {
      "text": "...",
      "source_fact_codes": ["day_master.stem"],
      "source_components": ["five_elements"],
      "warnings": [],
      "uncertainty": []
    }
  ],
  "advice": [
    {
      "text": "...",
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

### 22.5 Output contract

successful AI Reading v2 wrapper は次の top-level field をすべて REQUIRED とする。
field omissionを禁止する。

``` json
{
  "schema_version": "ai_reading_v2",
  "engine_version": "1.2",
  "summary": {
    "text": "",
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
      "summary": {"text": "", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "detail": {"text": "", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
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
      "summary": {"text": "", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "detail": {"text": "", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
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
      "summary": {"text": "", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "detail": {"text": "", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
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
      "summary": {"text": "", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "detail": {"text": "", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
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
      "summary": {"text": "", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "detail": {"text": "", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
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
      "summary": {"text": "", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "detail": {"text": "", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
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
      "summary": {"text": "", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "detail": {"text": "", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
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
      "summary": {"text": "", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
      "detail": {"text": "", "source_fact_codes": [], "source_components": [], "warnings": [], "uncertainty": []},
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
  "source_fact_codes": [],
  "source_components": [],
  "warnings": [],
  "uncertainty": []
}
```

非null `consultation_answer`では`text`だけをmodel-authoredとする。source arraysは22.6の
dynamic enum、`warnings` / `uncertainty`は22.10のcatalog IDだけを許可し、trusted validatorが
すべてresolveする。consultation自体をastrology fact sourceとしてはならない。astrology claimは
少なくとも一つのfact/component referenceを必要とする。pure practical adviceはsource arraysを
emptyにできるが、engine calculationとして表現してはならない。

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

自然言語以外では、modelはsection `facts`、各`grounded_text_block`の
`source_fact_codes` / `source_components`、およびsection/block/consultationのwarning ID / uncertainty
IDをtrusted dynamic enumからSELECTできる。これらはmodelによる新規reference生成ではない。

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

1.  non-luckのastrology factual claimが参照するfactは、validated inputの
    `reading_context_v2.facts[].code` に存在しなければならない。luck valueだけは22.12の
    explicit crosswalkに限定したtrusted factual source exceptionを使用できる。
2.  calculation-dependent interpretationを含むblockは、`source_fact_codes`または
    `source_components`の少なくとも一方に1件以上のvalidated referenceを持たなければならない。
3.  fact code / component referenceは、inputからtrusted codeが構築したdynamic enumで
    制約しなければならない。
4.  source referenceはinput内でresolve可能でなければならない。
5.  `interpretation_hints` はtopic/focusを案内できるが、新しいtruthを作れない。
6.  Common Judgment Metadataはcertaintyを制御するが、新しいastrology valueを作れない。
7.  warnings / uncertaintyをfactへ変換してはならない。
8.  consultationはemphasis / practical adviceにだけ使用する。
9.  general practical adviceをengine calculationとして表現してはならない。
10. missing sourceを補完せず、missingのまま扱う。
11. top-level summaryおよびsectionのsummary、detail、evidence、interpretation、adviceに
    含まれるastrology claimは、それを含む`grounded_text_block`のreferenceでtraceできなければ
    ならない。別blockのreferenceを暗黙に流用してはならない。
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

luck-valued astrology claimは、次の三条件をすべて満たす場合だけvalidとする。

1.  claimを含む`grounded_text_block.source_components`がallowed luck componentを持つ。
2.  blockのlocation/scopeにexact matchする`luck_value_source_entry`が存在する。
3.  同entryの`context_path`が本節のallowed Reading Context v2 luck pathへresolveする。

luck exceptionを許可するscopeは、`current_luck` section、`future_flow` section、
`future_flow.yearly[i]`のexactly三つに限定する。top-level `summary`、`core_personality`、`career`、
`wealth`、`relationships`、`health`、`advice`、`consultation_answer`ではluck structured-path exceptionを
禁止する。これらのscopeでastrology factual claimを行う場合は通常のfact/component grounding ruleを
使用し、luck structured pathをvalue sourceとしてはならない。

`current_luck` sectionの`summary`、`detail`、各`evidence`、各`interpretation`、およびastrology-dependent
`advice` blockでluck exceptionを使う場合、各model-selected luck `source_component`はcurrent-luck
crosswalkのexactly one top-level Reading Context luck pathへresolveしなければならない。

`future_flow` sectionのnon-yearly `summary`、`detail`、各`evidence`、各`interpretation`、および
astrology-dependent `advice` blockでluck exceptionを使う場合、選択された`source_component`について
`trusted_catalogs.luck_value_sources`に存在するfuture-flow全year entryのcontext pathをtrusted year順の
ordered setとしてresolveしなければならない。modelはそのordered setのsubset yearを指定できない。
特定yearのclaimは対応する`future_flow.yearly[i]` blockに置かなければならない。
`five_year_luck=[]`の場合、future-flow non-yearly blockはluck exceptionを使用できない。

`future_flow.yearly[i]`の`summary`または`detail` blockでluck exceptionを使う場合、trusted positional
index `i`とtrusted attached yearによって、選択された`source_component`をexactly one
`luck.five_year_luck[i].<component>` pathへresolveする。modelはyear、index、pathを返してはならない。

`source_components`はglobal allowed enumであるが、そのmembershipだけでluck groundingをvalidとしては
ならない。validatorおよびQuality Gateはblock scope、source component、trusted
`luck_value_source_entry`のcrosswalk一致を必ず検証し、scopeに対応するentryがなければinvalidとする。
non-luck source componentには従来のcomponent grounding ruleを維持する。

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
    "source_fact_codes": [],
    "source_components": [],
    "warnings": [],
    "uncertainty": []
  },
  "detail": {
    "text": "...",
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
    各blockの`text`だけであり、yearly entry全体を別のtraceability unitとして扱ってはならない。
-   各blockの`source_fact_codes` / `source_components`は22.6のdynamic enumからmodelがSELECTし、
    trusted validatorがresolveする。modelはreferenceをINVENTできず、trusted codeは意味を推測して
    referenceを生成・補完しない。
-   各blockの`warnings` / `uncertainty`は22.10のtrusted catalog IDだけを許可し、全IDを
    trusted validatorがresolveする。unknown birth timeがyearly claimへ影響する場合は、該当する
    block自身がapplicable uncertainty IDを持たなければならない。
-   astrology claimを含む`summary`または`detail` blockでは、`source_fact_codes`と
    `source_components`の両方をemptyにしてはならない。
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
4.  trusted warning / uncertainty catalog、fact/component dynamic enum、luck value source catalogを
    構築し、trusted attachmentsを構築する。
5.  22.2.3に従ってexact `model_output_schema`を構築する。
6.  22.2.1のexact system constantとcanonical user serializationからexact `messages`を構築する。
7.  exact `messages`と`model_output_schema`を使用してmodelを呼び出す。
8.  model responseをstrict JSON Schema validationする。
9.  schema-valid model payloadをsemantic reference validationし、fact resolution、component resolution、
    luck block scope crosswalk、warning ID、uncertainty ID、section count、future year countを確認する。
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
-   `grounded_text_block`のexact shapeとastrology claimのsource-presence rule
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
v1 pipeline、`tests/golden/v1_1/**`、およびastrology calculation ruleを変更しない。

### 22.16 Phased migration

AI Reading v2は次の順に段階導入する。Big Bang migrationを禁止する。

1.  Phase 1: AI Reading v2 spec freeze
2.  Phase 2: new opt-in `reading_prompt_v2`
3.  Phase 3: new opt-in `reading_generator_v2`
4.  Phase 4: AI Reading v2 unit / four-pillar / three-pillar tests
5.  Phase 5: AI Reading v2 Golden after human review
6.  Phase 6: Quality Gate v2
7.  Phase 7: Auto-Repair v2
8.  Phase 8: ReadingProduct v2
9.  Phase 9: API v2
10. Phase 10: PDF / E2E

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
