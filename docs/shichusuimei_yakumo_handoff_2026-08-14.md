# 四柱推命 八雲｜開発引き継ぎ資料

更新日：2026年8月14日

## 現在地

プロジェクトは `shichusuimei-api`。作業ブランチは
`customer-production-v1`。
顧客向け鑑定書生成パイプラインは実動確認済み。格局修正前の全体テスト実績は
`5986 passed, 462 skipped, 2 xfailed, 1 xpassed`。

## 今回のテーマ

対象命式：1984-07-10 22:45、愛知県、男性。 命式は
`甲子 / 辛未 / 乙巳 / 丁亥`、日主は乙、月支は未。

未の蔵干： - 己 → 偏財 - 丁 → 食神 - 乙 → 比肩

月支主蔵干の己は透干していないが、丁は時干に透出している。

## 原因

旧 `pattern_candidates.py` は「月支主蔵干 → 通変星 →
格局候補」で普通格を選んでいた。 そのため `未 → 己 → 偏財 → 偏財格`
となっていた。
一方、エンジンは丁＝食神、丁の時干透出、食神制殺まで認識できていた。
問題は通変星計算ではなく、普通格候補抽出の取格仕様だった。

## 採用した新仕様

普通格は次の順で選ぶ。 1. 月支の全蔵干を確認 2. 各蔵干の通変星を確認 3.
普通格対象だけを評価 4. 天干へ透出している月支蔵干を優先 5.
複数透干なら主蔵干を優先 6.
主蔵干が非透干なら既存蔵干順位の高い透干蔵干を優先 7.
有効な透干がなければ主蔵干へフォールバック 8.
比肩・劫財など普通格対象外だけなら普通格候補を作らない

月支本来の主蔵干は変更しない。 `month_main_hidden_stem = 己`
を保持し、実際の取格元を `selected_hidden_stem = 丁` として別管理する。

## pattern_candidates.py 修正後

対象命式で以下を確認済み。 - pattern = 食神格 - technical_pattern =
eating_god - source = month_exposed_hidden_stem - month_main_hidden_stem
= 己 - selected_hidden_stem = 丁 - selected_is_main_hidden_stem =
False - ten_god = 食神 - is_exposed = True - exposure_positions =
\['hour'\] - confidence = high

つまり、非透干の己＝偏財より、時干へ透出した丁＝食神を取格元として優先できた。

## pattern_judgment.py 修正

旧後段ロジックには `is_exposed=True`
なら一律「月支主蔵干が天干へ透出」と説明する旧仕様依存が残っていた。
新しい `selected_hidden_stem` / `selected_is_main_hidden_stem`
に対応させた。

修正後： - 食神格 - base_score = 70 - exposure_adjustment = +10 -
special_rule_adjustment = +4 - establishment_score = 84 -
establishment_status = strong - final_judgment =
provisional_established - confidence = high

説明も `selected_month_hidden_stem_exposed` となり、
「格局候補として採用した月支蔵干が天干へ透出しています。」 へ修正済み。

したがって本番ロジックでは、この対象命式を食神格として正常処理できている。

## pytestの現在地

実行：
`pytest tests/test_pattern_candidates.py tests/test_pattern_judgment.py -q`

結果： `17 failed, 159 passed`

主因は本番ロジックではなく、`tests/test_pattern_candidates.py`
のfixtureが旧仕様前提であること。

共通 `make_chart()` は概ね、 - day_stem = 乙 - month_hidden_stems =
\[己, 丁, 乙\] - hour_stem = 丁

旧テストは `month_main_hidden_stem_ten_god`
のラベルだけを人工的に変更していた。
新仕様では実際の全蔵干と透干を見るため、fixture内の丁が食神として時干に透出し、食神格が選ばれる。

そのため以下のような失敗が出た。 - 傷官格 expected → 食神格 actual -
比肩ならNone expected → 食神格 actual - 劫財ならNone expected → 食神格
actual - 非透干 expected → fixture上では丁が実際に透干 - 偏財格 expected
→ 食神格 actual

本番コードを旧テストへ戻してはいけない。テストfixtureを新仕様へ更新する。

## test_pattern_candidates.py の修正方針

A. 普通格parametrize
ラベルだけ差し替えず、日主と蔵干が本当にその通変星になるfixtureを作る。
甲日主の例： - 甲×辛 = 正官 - 甲×庚 = 偏官 - 甲×己 = 正財 - 甲×戊 =
偏財 - 甲×癸 = 印綬 - 甲×壬 = 偏印 - 甲×丙 = 食神 - 甲×丁 = 傷官

B. 比肩・劫財・不明
月支蔵干を1個だけにするなど、他の普通格対象蔵干が偶然透干しないfixtureにする。

C. 非透干テスト `month_hidden_stems=["己"]` のように限定する。

D. standard_only 偏財格だけを確認するなら月支蔵干を `["己"]`
に限定する。

E. month_context 新しく `standard_pattern_sources`
が追加されたため、旧dict完全一致ではなく主要フィールドとsourcesを個別検証する。

F. 実命式回帰 既存 `乙丑 / 癸未 / 乙巳 / 丁亥`
の期待値を偏財格から食神格へ更新。
selected_hidden_stem=丁、source=month_exposed_hidden_stem、is_exposed=True、exposure_positions=\['hour'\]、confidence=high
を確認する。

G. 今回の対象命式回帰 `甲子 / 辛未 / 乙巳 / 丁亥` について、
month_main_hidden_stem=己、selected_hidden_stem=丁、selected_is_main_hidden_stem=False、pattern=食神格、technical_pattern=eating_god、source=month_exposed_hidden_stem、exposure_positions=\['hour'\]
を固定する。

## 直前で止まった作業

アップロード済みの現行 `test_pattern_candidates.py`
を基に、新仕様対応完全版を生成しようとしていた。 修正テキストの
`compile()`
による構文チェックまでは成功したが、`/mnt/data/test_pattern_candidates.py`
への保存で PermissionError が発生した。

次回は別名、例：
`/mnt/data/test_pattern_candidates_exposure_priority_complete.py`
で保存してユーザーへ渡す。

## 次チャットの最優先作業

1.  新仕様対応 `tests/test_pattern_candidates.py` 完全版を完成
2.  ユーザーが既存ファイルへ上書き
3.  `pytest tests/test_pattern_candidates.py tests/test_pattern_judgment.py -q`
4.  失敗が残ればその失敗だけ修正
5.  格局関連が通れば格局問題は終了

ユーザーは「検証は最低限にしたい」と希望しているため、全約6000件のpytestは毎回回さない。

## 格局完了後

PDF鑑定書の商品仕上げへ戻る。 追加予定： - 鑑定した人の名前 - 鑑定日 -
「四柱推命 八雲」

表紙例： 四柱推命鑑定書 佐藤 美咲 様 鑑定日 2026年8月14日 四柱推命 八雲

## 販売設計

販売先：ココナラ ブランド：四柱推命 八雲 コンセプト：
「人生を決めてもらう占い」ではなく「人生を自分で選ぶための四柱推命」
鑑定軸：命式 × 現在のお悩み × 理想の未来 初期価格案：4,000円

## 開発原則

-   命式計算結果をAIに再計算させない
-   AIは計算済みreading_contextを解釈する
-   格局・用神・身強身弱などの計算責任はエンジン側
-   出生時刻不明時は不確実性を保持
-   本番コードをテストに無理やり合わせない
-   仕様変更時はfixtureを意味的に正しく更新
-   対象テスト → 必要なら最後に全体テスト
-   実命式の回帰テストを残す
-   正常機能はできるだけ触らない

## 次チャットでの開始文

「この引き継ぎ資料の続きからお願いします。新しい透干優先の格局仕様に対応した
`tests/test_pattern_candidates.py`
の完全版を作成し、格局関連pytestだけを通すところから再開してください。検証は最低限でお願いします。」
