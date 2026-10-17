# AWS CDKアーキテクチャ

AWSリソースはTypeScriptの`ApplicationStack`で定義し、Python Lambdaは`lambda.Code.fromAsset("lambda")`で配布します。Stack名は固定の`app`名前空間を使用し、共有環境は`app-development`、`app-staging`、`app-production`、PR一時環境は`app-pr-<PR番号>`です。

`production`のDynamoDB tableは`RETAIN`、それ以外は`DESTROY`です。Lambda assetにはPythonキャッシュ、pytest cache、単体テストを含めません。

CI/CDの有効化契約は`.github/cicd/application.json`です。すべてのAWS操作は初期状態で無効です。有効化前にpreview / staging / productionのGitHub Environmentへrequired reviewersを設定し、対象環境ごとに最小権限の`AWS_ROLE_TO_ASSUME`をEnvironment Secretとして設定します。

previewはfork外かつOWNER、MEMBER、COLLABORATORのPRだけが対象です。`diff`成功後に`deploy`を直列実行し、同一PRの更新とclose cleanupは同一concurrency groupで最大100件までFIFOキューイングします。実AWS操作直前にはPRのopen状態とhead SHAを再確認します。

cleanupは`pull_request_target`で既定ブランチの管理workflowとして起動し、PRコードをcheckoutまたは実行しません。作成時に記録するworkflow SHAはPR base SHAであり、cleanup時に既定ブランチの祖先であることを検証します。helperは常に保護された既定ブランチからcheckoutして実行します。コメントのPR専用Stack名、リージョン、PR SHA、AWSアカウント、状態を使い、削除前に認証先AWSアカウント、リージョン、Stack名、`app:managed-by=ai-driven-development`、`app:preview-pr=<PR番号>`タグ、Stack状態を確認します。共有Stackは削除対象になりません。`DELETE_IN_PROGRESS`は完了待機後にdestroyedとして記録します。