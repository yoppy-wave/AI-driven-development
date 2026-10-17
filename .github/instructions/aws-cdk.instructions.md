---
applyTo: "bin/**,lib/**,lambda/**,.github/workflows/*aws-cdk*.yml,docs/aws-cdk-architecture.md"
---

# AWS CDKの開発指示

- AWSリソースはTypeScriptのCDK Stackで宣言し、LambdaのPython実装は`lambda.Code.fromAsset()`で参照する。独自ハッシュでLambda更新を判定しない。
- PR一時環境は`app-pr-<PR番号>`だけを使用し、共有環境のdestroyを自動化しない。
- AWS認証はGitHub Actions OIDCの短期認証を使い、Role ARNはGitHub Environmentの`AWS_ROLE_TO_ASSUME` Secretで管理する。
- `cdk deploy`、`cdk destroy`、`cdk bootstrap`は人間の明示承認なしに実行しない。