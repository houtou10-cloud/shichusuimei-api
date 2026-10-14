# Stripeテスト決済・ステージング確認手順

対象は専用ステージングだけである。本番キー、実課金、既存2サービスでは有効化しない。

## Render環境変数

専用サービス単位で次を設定する。秘密値は文書、ログ、Gitへ記録しない。

- `STRIPE_TEST_CHECKOUT_ENABLED=true`
- `STRIPE_TEST_SECRET_KEY`: `sk_test_`で始まるStripeテスト用シークレットキー
- `STRIPE_TEST_PRICE_ID`: 1,980円・JPY・買い切り商品のテスト用Price ID
- `STRIPE_TEST_WEBHOOK_SECRET`: 専用Webhookエンドポイントのテスト用署名シークレット
- `CUSTOMER_ENTITLEMENT_SECRET`: 32文字以上のランダムな専用署名シークレット
- `CUSTOMER_PUBLIC_BASE_URL=https://yakumo-pwa-staging.onrender.com`

既存の`CUSTOMER_ACCESS_CODE`は維持する。テスト決済完了後も、ステージングではアクセスコードを要求する。

## Stripeテストモード設定

1. テストモードで1,980円・JPY・一回払いのPriceを作成する。
2. Webhook送信先を`https://yakumo-pwa-staging.onrender.com/stripe/webhook`にする。
3. 少なくとも`checkout.session.completed`を送信対象にする。
4. Renderへ上記環境変数を設定して手動再デプロイする。
5. `/career-reading`に「テスト決済へ進む」と「実際の料金は請求されません」が表示されることを確認する。

## E2E成功条件

1. Stripe公式テストカードでCheckoutを完了する。
2. `/checkout/success`が支払済み、JPY、1,980円、対象商品をサーバー側で照合する。
3. Secure・HttpOnly・SameSite=Laxの短期鑑定権が発行され、`/app`を開ける。
4. アクセスコードと合成顧客入力で鑑定を実行できる。
5. 鑑定成功後は同じ鑑定権を再使用できない。
6. 鑑定生成が失敗した場合は鑑定権が残り、再試行できる。
7. キャンセル時は未請求と表示し、販売ページへ戻れる。
8. 改ざんCookie、不正金額、不正通貨、異なる商品、未払いSession、無効署名Webhookを拒否する。

## 無効化

`STRIPE_TEST_CHECKOUT_ENABLED=false`へ戻して手動再デプロイする。無効時はStripe APIを呼ばず、従来のステージング鑑定画面とアクセスコード運用へ戻る。

## 現在の制約

使用済み鑑定権とWebhook重複記録はプロセス内メモリで保持する。再起動や複数インスタンスをまたぐ本番運用には永続ストアが必要であり、この状態を本番決済完成とは扱わない。
