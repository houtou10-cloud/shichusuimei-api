# Shichusuimei API

八雲式 四柱推命鑑定エンジンのAPIと顧客向け鑑定画面です。

## 顧客向け鑑定画面

1. `OPENAI_API_KEY` を実行環境に設定します。
2. 必要に応じて `OPENAI_READING_MODEL` を設定します（未設定時は既存Generator既定値）。
3. アプリを起動します。

```powershell
python -m uvicorn main:app --reload
```

ブラウザで `http://127.0.0.1:8000/app` を開くと、生年月日・出生時刻・出生地・性別・相談内容を入力して鑑定できます。出生時刻が不明な場合は、時刻を推測せず「出生時刻が分からない」を選択してください。

画面は既存のv1.2パイプライン（命式計算、Reading Context v2、AI Reading v2、Quality Gate v2、必要時のAuto-Repair v2、PASS-only ReadingProduct v2）を利用します。APIキー、prompt、providerのraw response、内部hashは顧客画面へ出力しません。

販売用PDFをブラウザから保存する場合は、結果画面をChromeで印刷し、詳細設定の「ヘッダーとフッター」をOFFにしてください。
