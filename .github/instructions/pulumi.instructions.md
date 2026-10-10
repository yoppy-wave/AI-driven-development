---
applyTo: "Pulumi.yaml,Pulumi.*.yaml,.pulumi.version,**/infra/**,**/infrastructure/**,**/*pulumi*.ts,**/*pulumi*.mts,**/*pulumi*.cts"
---

# Pulumi・IaCの開発指示

- Providerは対象クラウド、対象サービス、組織のセキュリティ・運用要件を確認してから、必要最小限をプロジェクト単位で追加する。汎用テンプレートにAWS、Azure、GCP、CloudflareなどのProviderを先行導入しない。クラウド固有の制約が必要になった場合は、このファイルへ混在させず、対象Provider用のinstructionファイルを追加する。
- Pulumi CLIのバージョンはリポジトリルートの`.pulumi.version`を唯一の正とする。Dev ContainerとGitHub Actionsを含む実行環境で同じファイルを参照し、個別設定へバージョンを複製しない。
- Provider、`@pulumi/pulumi`、実行時依存関係は`package.json`で明示し、選択したパッケージマネージャーのロックファイルをコミットする。依存関係の追加・更新では、対象Provider、必要な権限、互換性、更新理由を確認する。
- Stackは環境・用途・権限境界ごとに分離する。実行前に現在のバックエンド、Stack、クラウドアカウントまたはテナント、リージョン、対象プロジェクトを確認し、名前が似た環境を推測で選ばない。
- StateはPulumi Cloudまたは組織が管理するリモートバックエンドで保護し、ローカルの`.pulumi/`やローカルStateをコミットしない。Stateの移行、バックエンド変更、Stack削除は影響範囲と復旧方法を確認してから行う。
- 認証情報、秘密鍵、接続文字列、トークン、パスワードをソース、非暗号化設定、ログ、テストデータ、Stack出力へ平文で残さない。設定値には`pulumi config set --secret`、組織承認済みのSecrets Provider、CIのSecretsを使い、Secret値をログ・エラー・レビューコメントへ出力しない。
- リソース変更前に、該当プロジェクトの依存関係・型検査・lint・テストを実行できる場合は実行し、`pulumi preview --diff`で作成・更新・置換・削除の差分を確認する。変更の適用または削除は明示的な依頼・承認なしに実行しない。
- `pulumi up`、`pulumi destroy`、`pulumi refresh`、State操作の前には、対象Stack、バックエンド、認証先、リージョン、削除・置換されるリソース、依存リソース、バックアップ・復旧手順を確認する。`destroy`は保護対象とデータ保持要件を確認できない場合は実行しない。