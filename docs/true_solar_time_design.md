真太陽時・出生地補正 設計仕様書

1. 文書情報

対象プロジェクト: shichusuimei-api

対象機能: 四柱推命における出生地・真太陽時補正

文書種別: 設計仕様書

バージョン: true_solar_time_design_v1

ステータス: design_proposal

実装状態: 未実装

デフォルト方針: 補正なしを維持

将来方針: オプションとして補正機能を追加可能にする

2. 目的

本設計書の目的は、出生地による時刻補正を四柱推命エンジンへ安全に追加するための仕様を先に固定することである。

四柱推命では、出生時刻をどの基準で扱うかについて流派差が存在する。

代表的には次の3方式がある。

標準時をそのまま使用する

経度差のみを補正する

経度差に加えて均時差も補正する

本プロジェクトでは、これらを混在させず、明示的な計算方式として分離する。

既存の命式計算結果を壊さないことを最優先とする。

3. 現行仕様

現行エンジンでは、出生日時は日本標準時として扱う。

出生地は入力として保持しているが、四柱計算そのものには出生地による時刻補正を行っていない。

つまり現行仕様は、

入力出生時刻
    ↓
Asia/Tokyo
    ↓
そのまま四柱計算

である。

現行仕様では、真太陽時補正を行わない。

この契約は既存テスト・既存APIとの互換性のため今後もデフォルトとして維持する。

4. 設計原則

真太陽時補正は、既存の暦計算ロジックへ直接埋め込まない。

補正は独立モジュールとして実装し、四柱計算へ渡す日時を前処理として変換する。

設計イメージは次のとおり。

出生日時
    ↓
出生地
    ↓
time_correction.py
    ↓
補正済み出生日時
    ↓
calculate_four_pillars()

これにより、

標準時

経度補正

真太陽時補正

を切り替え可能にする。

5. 採用する補正モード

将来実装では、以下の3モードを定義する。

5.1 standard

補正を行わない。

mode = "standard"

計算式:

corrected_datetime
=
birth_datetime

既存仕様と完全互換。

デフォルト値はこれとする。

5.2 longitude

出生地経度と日本標準時基準経度との差だけを補正する。

日本標準時の基準経度:

東経135度

地球は24時間で360度回転するため、

経度1度
=
4分

として補正する。

計算式:

longitude_offset_minutes
=
(longitude - 135.0) * 4

補正時刻:

corrected_datetime
=
birth_datetime
+
longitude_offset

例:

東京付近東経139.7度

(139.7 - 135.0) * 4
=
18.8分

したがって、

標準時 12:00
↓
地方平均太陽時 約12:18:48

となる。

5.3 apparent_solar

経度補正に加えて均時差を加味する。

mode = "apparent_solar"

計算式:

corrected_datetime
=
birth_datetime
+
longitude_offset
+
equation_of_time_offset

この方式を本設計では「真太陽時補正」と呼ぶ。

6. 用語整理

標準時

日本標準時をそのまま使う方式。

JST

地方平均太陽時

出生地の経度差のみを補正した時刻。

Local Mean Solar Time

真太陽時

地方平均太陽時に均時差を加えた時刻。

Apparent Solar Time

7. 出生地データ

真太陽時補正には出生地から最低限、

緯度

経度

を取得する必要がある。

ただし、四柱推命の時刻補正で主に必要なのは経度である。

緯度は将来、

天文計算

日の出・南中計算

高度依存計算

等へ拡張する可能性を考慮し保持可能とする。

8. 出生地の入力形式

初期実装では、以下のいずれかを想定する。

8.1 既知の都道府県

例:

愛知県
東京都
石川県
福岡県
北海道

都道府県代表座標を内部テーブルで管理する。

8.2 緯度経度直接指定

将来APIでは、

{
  "birth_place": "愛知県名古屋市",
  "latitude": 35.1815,
  "longitude": 136.9066
}

のような指定を許可できる。

直接指定された緯度経度を都道府県代表値より優先する。

9. 座標取得方針

初期段階では、外部ジオコーディングAPIへ依存しない。

理由:

API障害の影響を受ける

レスポンスが不安定

同じ地名で座標が変わる可能性

テスト再現性が低下する

外部利用料金が発生する可能性

したがって、初期版では内部マスタを推奨する。

例:

PLACE_COORDINATES = {
    "東京都": {
        "latitude": 35.6762,
        "longitude": 139.6503,
    },
    "愛知県": {
        "latitude": 35.1802,
        "longitude": 136.9066,
    },
}

将来、市区町村単位へ拡張可能とする。

10. 推奨モジュール構成

新規ファイル:

engine/time_correction.py

責務:

補正モードの検証

出生地座標取得

経度差計算

経度補正

均時差計算

補正後日時生成

メタデータ生成

11. 推奨Public API

calculate_longitude_offset_minutes

def calculate_longitude_offset_minutes(
    longitude: float,
    standard_meridian: float = 135.0,
) -> float:

戻り値:

分

calculate_equation_of_time_minutes

def calculate_equation_of_time_minutes(
    target_datetime: datetime,
) -> float:

戻り値:

分

apply_time_correction

def apply_time_correction(
    birth_datetime: datetime,
    *,
    longitude: float | None = None,
    mode: str = "standard",
) -> dict:

戻り値イメージ:

{
    "original_datetime": datetime(...),
    "corrected_datetime": datetime(...),
    "mode": "longitude",
    "longitude": 136.9066,
    "standard_meridian": 135.0,
    "longitude_offset_minutes": 7.6264,
    "equation_of_time_minutes": 0.0,
    "total_offset_minutes": 7.6264,
}

12. 補正後日時の扱い

最重要ルール。

補正後日時は、単に時柱計算だけへ使ってはいけない。

補正によって日付が変わった場合、以下すべてを補正後日時から再計算する。

年柱
月柱
日柱
時柱

理由:

標準時 00:05
↓
補正
23:50

となった場合、

時支だけでなく日付そのものが前日になるためである。

13. 日付跨ぎルール

例:

出生日時:
2026-08-11 00:05

補正:
-20分

補正後:
2026-08-10 23:45

この場合、

日柱
=
2026-08-10

として計算する。

時柱も、

2026-08-10の日干
+
23時の子刻

から計算する。

14. 立春跨ぎルール

さらに重要なケース。

例:

標準時:
立春 05:05

補正:
-10分

補正後:
04:55

実際の立春が05:02なら、

標準時では新年扱いだが、補正後では立春前となる可能性がある。

この場合、補正後日時を基準として

年柱
月柱

を判定する。

つまり、出生地補正を有効にした場合は立春・節入り境界にも影響する。

15. 月節入り跨ぎルール

同様に、

標準時:
啓蟄直後

補正後:
啓蟄直前

となれば、

月柱は旧月柱として計算する。

16. 23時・00時境界

現行仕様では、

23:00
=
子刻開始

00:00
=
日柱切替

である。

補正後日時が、

22:58 → 23:05

となれば、時支は亥から子へ変わる。

一方、

00:05 → 23:55

となれば、

日柱は前日

時支は子

時干は前日の日干基準

となる。

17. timezoneの扱い

入力日時は原則として

Asia/Tokyo

で解釈する。

補正後もtimezoneとしてはAsia/Tokyoを保持してよい。

ただし、真太陽時は法定時刻ではないため、timezone offsetそのものを変更するものではない。

つまり、

tzinfo=Asia/Tokyo

は維持し、datetimeの時計表示だけを補正する。

18. API設計案

将来、ChartRequestへ追加する場合は、

solar_time_mode: str = "standard"
latitude: float | None = None
longitude: float | None = None

を想定する。

リクエスト例:

{
  "birth_date": "1984-07-10",
  "birth_time": "22:45",
  "birth_place": "愛知県",
  "gender": "male",
  "solar_time_mode": "standard"
}

経度補正:

{
  "birth_date": "1984-07-10",
  "birth_time": "22:45",
  "birth_place": "愛知県",
  "gender": "male",
  "solar_time_mode": "longitude"
}

真太陽時:

{
  "birth_date": "1984-07-10",
  "birth_time": "22:45",
  "birth_place": "愛知県",
  "gender": "male",
  "solar_time_mode": "apparent_solar"
}

19. レスポンス設計案

レスポンスには補正情報を必ず含める。

例:

{
  "time_correction": {
    "mode": "longitude",
    "original_datetime": "1984-07-10T22:45:00+09:00",
    "corrected_datetime": "1984-07-10T22:52:38+09:00",
    "longitude": 136.9066,
    "standard_meridian": 135.0,
    "longitude_offset_minutes": 7.6264,
    "equation_of_time_minutes": 0.0,
    "total_offset_minutes": 7.6264,
    "date_changed": false
  }
}

20. 計算ルールメタデータ

calculation_rulesにも補正方式を追加する。

例:

{
  "solar_time_mode": "standard",
  "solar_time_correction": false,
  "standard_meridian": 135.0
}

longitude:

{
  "solar_time_mode": "longitude",
  "solar_time_correction": true,
  "standard_meridian": 135.0
}

apparent_solar:

{
  "solar_time_mode": "apparent_solar",
  "solar_time_correction": true,
  "equation_of_time": true,
  "standard_meridian": 135.0
}

21. デフォルト仕様

最重要。

既存ユーザーとの互換性を守るため、

default
=
standard

とする。

つまり、何も指定しなければ現在と同じ結果を返す。

22. 後方互換性

以下は絶対条件。

既存リクエスト:

{
  "birth_date": "1985-07-17",
  "birth_time": "21:50",
  "birth_place": "石川県",
  "gender": "female"
}

は、真太陽時機能追加後も同じ命式を返す。

補正を有効にするには明示的な指定を必要とする。

23. エラー処理

longitude未指定

longitudeモードで経度を解決できない場合:

ValueError

例:

longitude補正には経度が必要です。

不明なmode

例:

solar_time_modeは
standard/longitude/apparent_solar
のいずれかで指定してください。

経度範囲

許容:

-180 <= longitude <= 180

緯度範囲

許容:

-90 <= latitude <= 90

24. 均時差の実装方針

均時差は簡易近似式ではなく、天文学的に再現可能な方法を採用するのが望ましい。

ただし初期実装では、経度補正を先に完成させ、均時差は第2段階とする。

推奨順:

v1
standard
longitude

v2
apparent_solar

理由:

経度補正だけでも境界テスト・日付跨ぎロジックを十分検証できるため。

25. 実装順序

推奨実装順:

Step 1

engine/time_correction.py

を新規作成。

まず、

standard
longitude

のみ実装。

Step 2

単体テスト:

tests/test_time_correction.py

Step 3

境界テスト:

tests/test_time_correction_boundaries.py

Step 4

calculate_four_pillars()へオプション統合。

Step 5

chart.pyへ統合。

Step 6

API Requestへsolar_time_mode追加。

Step 7

レスポンスへtime_correction追加。

Step 8

均時差を追加。

26. 必須テストケース

補正なし

standard

では入力日時と補正後日時が完全一致。

東経135度

longitude = 135.0

では経度補正0分。

東京

東経135度より東なのでプラス補正。

九州西部

東経135度より西なのでマイナス補正。

23時境界

補正前:

22:58

補正後:

23:02

なら、時支が

亥 → 子

へ変化。

00時境界

補正前:

00:05

補正後:

23:55

なら、日柱が前日へ変化。

01時境界

補正前:

00:58

補正後:

01:03

なら、時支が

子 → 丑

へ変化。

立春境界

補正前では立春後、補正後では立春前となるケース。

この場合、

年柱
月柱

の両方が変化すること。

節入り境界

補正によって節入り前後を跨ぐ場合、月柱が変化すること。

27. 推奨テストファイル

tests/test_time_correction.py
tests/test_time_correction_boundaries.py
tests/test_four_pillars_with_time_correction.py
tests/test_chart_time_correction.py
tests/test_api_time_correction.py

28. 既存ゴールデンテストとの関係

既存の、

test_verified_charts_v2.py
test_verified_lichun_boundary.py
test_verified_month_boundaries.py
test_verified_day_boundary.py
test_verified_hour_boundaries.py
test_verified_four_pillar_boundaries.py

は、

solar_time_mode = standard

として扱う。

したがって、真太陽時機能追加後も既存テストは変更しない。

もし変更が必要になった場合は、実装側の後方互換性が壊れている可能性を疑う。

29. AI鑑定との関係

AI鑑定へ渡す命式には、補正方式を必ず含める。

例:

{
  "calculation_rules": {
    "solar_time_mode": "longitude"
  }
}

AIには真太陽時を再計算させない。

AIはエンジンが確定した命式のみを解釈する。

30. 表示文言

ユーザー向けには、専門用語だけでなく意味を併記する。

例:

出生時刻補正:
経度補正あり

入力時刻:
22:45

補正後時刻:
22:52

補正差:
+7分38秒

31. 流派差の表示

補正機能を有効にした場合、以下の注意表示を推奨する。

出生時刻の補正方法は
四柱推命の流派によって異なります。

本鑑定では
指定された補正方式に基づいて
命式を計算しています。

32. 採用方針

本プロジェクトの推奨方針は次のとおり。

標準時
=
デフォルト

経度補正
=
オプション

真太陽時
=
高度オプション

これにより、

既存結果を壊さない

流派差を明示できる

高精度鑑定へ拡張できる

ユーザーが選択できる

という利点がある。

33. 採用しない設計

以下は採用しない。

出生地が入力されたら自動補正

理由:

ユーザーが知らないうちに命式が変化するため。

chart.py内部に経度計算を直書き

理由:

責務が混在するため。

時柱だけ補正

理由:

日付跨ぎ・立春跨ぎ・節入り跨ぎで年柱・月柱・日柱まで変化する可能性があるため。

AIに補正を判断させる

理由:

暦計算は決定論的エンジンで行うべきだから。

34. 最終アーキテクチャ

API Request
    ↓
birth_date
birth_time
birth_place
solar_time_mode
latitude
longitude
    ↓
time_correction.py
    ↓
corrected_birth_datetime
    ↓
year.py
month.py
day.py
hour.py
    ↓
pillars.py
    ↓
chart.py
    ↓
reading_context.py
    ↓
reading_generator.py
    ↓
AI鑑定

35. 完了条件

真太陽時機能v1の完了条件は、以下をすべて満たすこと。

standardで既存結果が完全一致

longitudeが正しく計算される

135度で補正0

東西で補正符号が正しい

23時境界を正しく跨ぐ

00時境界を正しく跨ぐ

日付跨ぎで日柱が変わる

立春跨ぎで年柱・月柱が変わる

節入り跨ぎで月柱が変わる

全pytestがGREEN

APIレスポンスに補正情報が出る

AIが補正計算を再実行しない

36. 結論

真太陽時・出生地補正は、四柱推命エンジンの精度を高める可能性がある一方、流派差と境界処理を伴うため、無条件に導入すべき機能ではない。

本プロジェクトでは、

デフォルト:
standard

追加オプション:
longitude

高度オプション:
apparent_solar

という段階的設計を採用する。

最も重要なのは、補正後日時を「時柱だけ」に使わないことである。

補正後日時は四柱すべての計算入力として扱う。

これにより、日付跨ぎ・立春跨ぎ・節入り跨ぎにも一貫して対応できる。

37. 次の実装ステップ

次に実装するファイル:

engine/time_correction.py

初期実装対象:

standard
longitude

次に作成するテスト:

tests/test_time_correction.py

この2つを完成させた後、四柱エンジンへ統合する。
