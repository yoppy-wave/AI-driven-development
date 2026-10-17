---
paths:
  - ".github/cicd/**"
  - ".github/workflows/cicd*.yml"
  - ".github/workflows/reusable-*.yml"
  - ".github/scripts/cicd_config.py"
  - ".github/scripts/tests/test_cicd_*.py"
  - ".github/workflows/reusable-aws-cdk.yml"
---

# CI/CD共通基盤の開発指示

- PR起点でクラウド認証情報を使用する操作は、再利用ワークフローの`workflow_call.secrets`で必要な名前を明示し、callerから必要な名前だけを`jobs.<job_id>.secrets`で受け渡す。再利用ワークフロー内でEnvironmentを割り当てたjobは、同名のEnvironment Secretを優先して使用する。
- preview、staging、productionのGitHub Environmentにはrequired reviewersを設定する。PR起点のpreviewはFork以外かつOWNER、MEMBER、COLLABORATORだけを対象にする。
- previewの`deploy`は同一Stackの`diff`成功後に直列実行する。cleanupは現在の設定ではなく、作成時に記録したPR専用Stack、AWSリージョン、commit SHAを使う。
- 再利用ワークフローはGitHub Actionsの仕様に従い、`.github/workflows/`直下に置き、`on.workflow_call`で入力・Secrets・出力を明示する。サブディレクトリへ置かない。
- `.github/cicd/application.json`をCI/CDの有効化契約として扱う。AWS CDK、Preview Environment、各環境へのデプロイは明示的に`true`になるまで無効のままにし、無効時にAWS認証、`cdk deploy`、`cdk destroy`を実行しない。
- PRではテスト・build・設定検証を必ず先行し、クラウド認証が必要なPreview EnvironmentはFork PRで作成しない。`pull_request_target`でPRコードをcheckoutしてSecretsを渡す実装は追加しない。
- PR一時環境はPR番号を含むStack・リソース名に限定し、作成・更新・削除に同じ識別子を使う。自動削除はPR専用Stack以外を拒否し、共有のdev、stg、prodを対象にしない。
- デプロイは信頼済みブランチまたは`workflow_dispatch`からだけ実行する。productionではGitHub Environmentを使い、承認者・Secrets・権限をリポジトリ設定で分離する。
- AWS認証はGitHub Actions OIDCの短期認証を使い、Role ARNは対象GitHub Environmentの`AWS_ROLE_TO_ASSUME` Secretで管理する。AWSアダプター以外へAWS固有のSecretsやURL形式を混在させない。未確定なら有効化せず、必要な設定と人間の確認事項を報告する。