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
