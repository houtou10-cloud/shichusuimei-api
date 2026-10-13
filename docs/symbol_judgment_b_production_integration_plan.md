# B研究モデル本番組み込み案（顧客Web接続・既定無効）

## 現在の状態

`scripts/symbol_judgment_b_production_adapter.py` に本番 `calculate_chart()` 結果を読み取る研究用境界を実装し、`api/symbol_judgment_reference.py` から顧客Web専用サイドカーとして接続した。Frozen engine・ReadingProduct契約・既存鑑定本文・PDFは変更していない。サーバー側feature flagは既定無効であり、デプロイおよび本番有効化は未実施であるため、本番組み込み完了を意味しない。

保存済み本番計算結果で、命式・現在大運・流年・通常喜忌をB入力へ変換し、B評価と「八雲式・参考評価」表示データまで通ることを確認した。入力はdeepcopyして保持し、元データを変更しない。

## 変換契約

- 四柱: `chart.{year,month,day,hour}.{stem,branch}` を個別に必須とする。`ganzhi` / `pillar` だけから欠損値を推測しない。併記値が天干＋地支と一致しなければhold。
- 通常喜忌: `useful_gods.primary_useful_element`、`secondary_useful_elements`、`support_balance.unfavorable_elements` の明示値だけを使う。欠損・重複はhold。
- 大運: `current_luck.has_current_luck` と `current_luck.current_luck_pillar.{stem,branch}` を使う。
- 流年: `annual_luck.{stem,branch}` を使う。
- 特殊格局: 本番 `pattern_judgment` から推測しない。呼び出し側が検証済みの `explicit_special_structure` を明示した場合だけ渡し、出所を `explicit_caller_input` として記録する。
- 出生時刻不明で時柱がない場合は、現行Bモデルが四柱必須のためhold。時柱を推測しない。

APIの `{success, result}` 形式では `result` を読み取る。変換不能とBモデルholdは「判定保留」、評価例外は「評価エラー」とし、正常記号へ変換しない。機能無効時は参考評価自体を表示しない。最高評価候補は規則未確立のため、顧客Webでは記号を出さず理由付き「判定保留」とする。

## 呼び出し位置と必要な本番変更

### 顧客鑑定経路

接続位置は `api/customer_routes.py` の顧客向けHTML生成後である。Frozenの本文レンダラーが返すHTMLに、独立した参考評価セクションを追加する。通常経路はReadingProductの読み取り専用 `to_dict()` から `engine_result` を取得し、高速経路は既存結果の `chart` を読み取る。

`YAKUMO_B_REFERENCE_EVALUATION_ENABLED` が `1`、`true`、`yes`、`on` のいずれかの場合だけB研究境界を呼ぶ。それ以外・未設定は無効で、アダプターもBモデルも呼ばず、参考評価HTMLも生成しない。研究境界または接続処理の例外はサイドカー内の「評価エラー」として正常記号から区別し、既存鑑定本文を保持する。

### 命式API経路

`api/routes.py` の `/api/v1/chart` は現在 `{success: true, result: calculate_chart(req)}` を返す。組み込む場合も既存 `result` を変更せず、明示的な任意フィールド（例: `research_reference_evaluation`）として追加する。既定無効とし、既存レスポンス契約を維持する。本タスクでは変更していない。

## 結果画面の表示案

見出しは必ず「八雲式・参考評価」とする。命式表・用神・大運表示の後、AI助言とは分離した参考情報セクションとして配置する。

各行に以下を表示する。

- 評価対象
- ◎○△×、または「判定保留」
- 短い日本語理由
- 適用規則
- 採用仮定（原典事実とは別欄）

末尾にモデルバージョン、未対応・不確実性、「研究用の参考評価であり、記号だけで転職・投資その他の意思決定を勧めない」旨を表示する。エラー詳細は顧客向けには安全な理由コードへ限定し、内部ログでは例外型を追跡できるようにする。

## 機能切り替えと元へ戻す方法

- 既定値は無効。
- 無効時は研究アダプターもBモデルも呼び出さず、既存Productと画面をそのまま返す。
- 有効化はサーバー側の明示設定一つに限定し、顧客入力から切り替えさせない。
- 段階導入では内部検証環境 → 管理者限定 → 小割合の順にする。
- 問題時は設定を無効へ戻すだけで、元の計算結果・Product・画面経路へ復帰できる。B評価失敗を既存鑑定失敗へ伝播させない。

研究用関数は `enabled=False` で評価器が一度も呼ばれないことをテスト済みである。

## ステージング起動手順

以下はPowerShellでの例である。リポジトリ直下で実行し、本番環境では実行しない。

### 0. 環境とHTTPS URLの確認

リポジトリの `render.yaml` には `shichusuimei-api` というWebサービス定義と起動コマンドだけがあり、ステージング／本番の区分、RenderサービスID、カスタムドメイン、確定HTTPS URLは記録されていない。検索で見つからないURLをサービス名から推測して試験先にしない。

ステージング管理画面で対象サービスがステージング用であることを所有者に確認し、表示されるHTTPS URLを試験記録へ転記する。次の三点がすべて成立したURLだけを「HTTPS確認先」とする。

1. `https://<確認済みステージングホスト>/` が200で `Shichusuimei API is running.` を返す。
2. `https://<確認済みステージングホスト>/app` が顧客入力画面を返す。
3. ブラウザの証明書エラーがなく、`/app/manifest.webmanifest`、`/app/sw.js`、`/app/apple-touch-icon.png` が同じホストから200で配信される。

現在のリポジトリ情報だけではこのホスト名を確定できないため、HTTPS疎通は未確認である。

### 1. 既定無効で起動

```powershell
Remove-Item Env:YAKUMO_B_REFERENCE_EVALUATION_ENABLED -ErrorAction SilentlyContinue
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

`http://127.0.0.1:8000/app` から同じ入力を実行し、「八雲式・参考評価」が表示されないことを確認する。この状態ではBアダプター・Bモデルを呼ばない。

### 2. ステージングだけで有効化

```powershell
$env:YAKUMO_B_REFERENCE_EVALUATION_ENABLED = "true"
$env:OPENAI_API_KEY = "ステージング用の既存シークレット設定"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

シークレット値をコマンド履歴、文書、ログへ記録しない。起動後に通常時刻、出生時刻不明、変換hold、評価例外を確認し、既存鑑定本文がすべての状態で残ることを確認する。

外部AI接続を使わないローカル検証では、既存Fast Readingの決定論的フォールバックをテスト内で注入する。これは画面接続検証用であり、外部AIの実呼び出し検証を代替完了したことにはしない。

### 3. 無効へ戻す

プロセスを停止してから、次回起動前にflagを削除する。

```powershell
Remove-Item Env:YAKUMO_B_REFERENCE_EVALUATION_ENABLED -ErrorAction SilentlyContinue
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

再起動後、「八雲式・参考評価」がなく、既存鑑定だけが表示されることを確認する。flagはプロセス起動時のサーバー環境設定であり、顧客入力から変更できない。

## 顧客入力から画面表示までの検証手順

1. 顧客入力を既存バリデーションへ通す。
2. 既存 `calculate_chart()` を実行し、結果を保存・ハッシュ比較できる状態にする。
3. feature flag有効時だけ研究アダプターへdeepcopyを渡す。
4. 変換後の四柱・喜忌・現在大運・流年を元結果と項目別に照合する。
5. B評価の記号、理由、適用規則、仮定、hold理由を確認する。
6. 表示用データでholdは「判定保留」、errorは「評価エラー」となり、正常記号と区別されることを確認する。
7. 既存Productの検証、AI鑑定、HTML、PDFが有効・無効の両方で従来どおりであることを回帰確認する。
8. 同一入力でfeature flagを無効に戻し、既存出力と一致することを確認する。

精度評価は別途、独立ラベル付きデータで行う。テスト件数や合格件数を鑑定精度として扱わない。

### 外部AIを使うE2Eの成功条件

1. ステージングのシークレット管理機能へ `OPENAI_API_KEY` を登録し、アプリの実行サービスだけに環境変数として注入する。リポジトリ、起動引数、画面、ログには値を置かない。
2. `OPENAI_READING_MODEL` はステージングで承認済みモデルを明示する。未設定時は現行既定値 `gpt-5` だが、試験結果の再現性のため明示を推奨する。
3. `YAKUMO_B_REFERENCE_EVALUATION_ENABLED=true` はステージングのサーバー環境だけに設定する。
4. `/app` から合成入力を送信し、`/app/reading` が200、既存鑑定本文と「八雲式・参考評価」の両方を表示することを確認する。
5. `FAST_PERF` の `status=success`、`provider_calls=1` と、provider側の成功記録を同じ `request_id` で確認する。レスポンスやログへAPIキー、prompt、provider raw responseが出ていないことも確認する。
6. 同じ手順で出生時刻不明を実行し、既存鑑定を表示したまま参考評価が判定保留になることを確認する。
7. flagを削除して再起動し、同じ入力で参考評価がなく、B境界が呼ばれないことを確認する。

環境変数は `OPENAI_API_KEY`、`OPENAI_READING_MODEL`、任意のB評価切替 `YAKUMO_B_REFERENCE_EVALUATION_ENABLED` の三つである。秘密値はステージングのシークレット管理にだけ保存する。コード既定モデルは `gpt-5` だが、このリポジトリには運用上の「承認済みモデル」を示す記録がない。管理責任者が承認したモデル名を `OPENAI_READING_MODEL` へ明示し、未承認の既定値を承認済みとみなさない。

Fast Readingの重複命式計算待ちはコード固定60秒であり、外部AI provider呼び出し専用の環境変数やアプリ側タイムアウトは未実装である。SDK、Render、上流プロキシそれぞれのタイムアウト値をステージング管理画面と実測ログで確認し、最短の制限値を試験記録へ残す。値が不明な状態をタイムアウト検証完了としない。

外部AI呼び出しが成功し、Quality GateまたはFast Readingの検証を通過し、既存鑑定と参考評価が同時に表示され、機密情報が出力されない場合だけE2E成功とする。AI文章の内容品質確認は別途、人手レビューを必要とする。

### 障害試験と監視

- provider timeout・接続失敗・不正応答: Fast Readingは既存エラー画面と503を返す。`fast customer reading unavailable`、`failure_type`、`failure_stage`、`FAST_PERF status=error` を確認する。現状、provider呼び出し専用のアプリ側タイムアウト値は明示設定されておらず、SDK・上流プロキシの設定に依存するため、ステージングで実測が必要。
- B評価例外: 既存鑑定は200で表示し、参考評価だけ「評価エラー」とする。外部AI成功をB評価失敗で巻き戻さない。
- B評価hold: 既存鑑定は200で表示し、参考評価は正常記号を出さず「判定保留」と理由を表示する。
- 出生時刻不明: 時柱を推測せずholdとする。
- 監視キー: `request_id`、HTTP status、`FAST_PERF status`、`provider_calls`、`failure_type`、`failure_stage`、`chart_elapsed`、`context_elapsed`、`validation_elapsed`、`render_elapsed`、`total_elapsed`。
- full経路を試す場合: `PERF_SUMMARY`、`PROVIDER_PERF`、Quality Gate decision、repair_countも確認する。
- ログ禁止事項: APIキー、prompt本文、provider raw response、顧客相談本文、命式全体を監視ログへ追加しない。

### PC・スマホ表示プレビュー

外部AIを呼ばず、実装本体の命式計算・B評価・顧客レンダラーから合成HTMLを生成する。

```powershell
python scripts/preview_symbol_judgment_b_customer_web.py --output .\tmp\symbol_judgment_b_customer_web_preview.html
```

生成物をブラウザで開き、PC幅1280×800とスマホ幅390×844で確認する。合成入力であること、外部AI文章は既存フォールバックであること、実外部AI E2Eの代替完了ではないことに注意する。生成先は検証用一時領域とし、本番配信物へ含めない。

### iPhone／Android実機のPWA確認

前提は上記で確定したHTTPSステージングURLである。実在顧客の情報は使わず、合成入力で実施する。

#### iPhone（Safari）

1. Safariで `/app` を開き、証明書警告がないことを確認する。
2. 共有メニューから「ホーム画面に追加」を選び、名称とApple Touch Iconが表示されることを確認する。
3. ホーム画面のアイコンから起動し、スタンドアロン表示、入力欄、出生時刻不明、性別の説明を確認する。
4. 通常の合成入力を送信し、二重送信できないこと、生成中案内に架空の割合・残り時間がないことを確認する。
5. 命式、要点、大運・流年、詳細鑑定が文字切れ・ページ全体の横スクロールなしで読めることを確認する。
6. B flag有効時は参考評価、根拠、規則、研究仮定を確認し、holdが△・×にならないことを確認する。

#### Android（Chrome）

1. Chromeで `/app` を開き、インストール可能時に「ホーム画面に追加」ボタンまたはブラウザのインストールメニューが使えることを確認する。
2. 192px／512pxのアイコン、テーマ色、スタンドアロン起動を確認する。
3. iPhone手順4〜6と同じ入力・結果確認を行う。

#### 失敗から再試行

1. ステージングの試験用障害注入または短い上流タイムアウトで503を発生させる。本番設定や実顧客リクエストでは実施しない。
2. タイムアウトとAI失敗が異なる案内になり、入力値が画面に保持されることを確認する。
3. 原因を除去して同じ入力から再送信し、結果画面まで到達することを確認する。
4. B評価だけを例外・holdにした場合は、既存鑑定が表示され、参考評価だけが「評価エラー」または「判定保留」になることを確認する。
5. 機内モードでは鑑定できず、オフライン利用可能と誤表示されないことを確認する。Service WorkerのCache Storageに顧客入力・鑑定結果・認証情報がないことを開発者ツールで確認する。

各実機についてOS、ブラウザ版、画面幅、HTTPS URL、実施日時、HTTP status、`request_id` を記録する。シークレット、相談本文、命式全体は記録しない。

## 障害時契約

- 変換hold: 元データを保持し、欠損・不一致のパスと理由を返す。
- Bモデルhold: 元データとB入力を保持し、記号なしで表示する。
- 評価例外: 研究境界で捕捉し、例外型を識別可能にして記号なしで返す。
- 無効: アダプター結果を生成せず、Bモデルを呼ばない。
- いずれも既存の本番鑑定データを上書きしない。

## 未実施の作業

- ReadingProductスキーマと所有契約への格納（独立サイドカー採用のため未変更）。
- PDFへの表示追加（意図的に対象外）。
- 命式APIレスポンスへの任意研究フィールド追加（既存契約維持のため未変更）。
- 本番feature flag設定と運用監視。
- 本番顧客入力を使ったステージングE2E。

