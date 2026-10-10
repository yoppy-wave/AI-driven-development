# GitHubリポジトリの初回設定

このテンプレートからリポジトリを作成した後、GitHub上で一度設定する項目をまとめます。リポジトリ内のワークフローやルールファイルだけでは、保護ブランチへの直接push禁止などのサーバー側制限は有効になりません。

## ブランチ構成

次のブランチを作成します。

```text
prod                    本番相当の安定ブランチ
└─ stg                  開発内容を統合・検証するブランチ
   └─ feature/<内容>    個別開発ブランチ
```

- `prod` は本番へ出す変更だけを受け入れます。
- `stg` は複数の開発ブランチを統合して検証します。
- 実装は `stg` を起点に作成した `feature/<内容>` または `fix/<内容>` ブランチで行います。
- 日常の変更は `feature/*` または `fix/*` から `stg` へのPRで取り込みます。
- リリース可能なまとまりになった時点で、`stg` から `prod` へのPRを作成します。

`prod` と `stg` を新規作成する場合は、GitHubのブランチ画面またはローカルGitで作成してリモートへpushします。既存の既定ブランチを残すか、`prod` を既定ブランチに変更するかは、チームの移行方針に合わせて決めてください。

## GitHub Rulesetsの設定

GitHubで **Settings → Rules → Rulesets → New ruleset → New branch ruleset** を開き、`stg` と `prod` にそれぞれルールを作成します。Rulesetの名称は、例えば `Protect stg` と `Protect prod` にします。

### `stg` 用Ruleset

対象ブランチを `stg` に指定し、少なくとも次を有効にします。

- **Require a pull request before merging**: 有効
- **Block force pushes**: 有効
- **Restrict deletions**: 有効
- **Restrict updates**: 有効にし、直接更新を許可するユーザー・チーム・GitHub Appを必要最小限に限定

必要に応じて、次も有効にします。

- **Require status checks to pass**: `Regression tests / regression`
- **Require approvals**: 少なくとも1件

### `prod` 用Ruleset

対象ブランチを `prod` に指定し、少なくとも次を有効にします。

- **Require a pull request before merging**: 有効
- **Require status checks to pass**: `Regression tests / regression`
- **Require approvals**: 少なくとも1件
- **Block force pushes**: 有効
- **Restrict deletions**: 有効
- **Restrict updates**: 有効にし、bypassできるユーザー・チーム・GitHub Appをリリース担当などに限定

チーム運用では、次も推奨します。

- **Dismiss stale pull request approvals when new commits are pushed**
- **Require conversation resolution before merging**
- **Require approval of the most recent reviewable push**

Rulesetのbypass権限は緊急時に必要な担当者だけに付与します。管理者を無条件に除外せず、通常時にもルールが適用される設定を優先してください。

## 必須チェックの選択

`Regression tests / regression` は、`.github/workflows/regression.yml` の回帰テストです。現在はすべてのブランチへのpushで実行されます。

Rulesetで必須チェックに追加する前に、対象リポジトリでこのワークフローを一度成功させ、GitHubのRuleset画面でチェック名を選べることを確認してください。ワークフロー名やjob名を変更した場合は、Rulesetの必須チェックも更新します。

## 日常の開発手順

```text
1. stg を最新化する
2. stg から feature/<内容> または fix/<内容> を作成する
3. 作業ブランチで実装・テスト・コミット・pushを行う
4. 作業ブランチから stg 宛てのPRを作成する
5. GitHub上でレビュー・CI確認後にPRをマージする
6. stg で統合・検証する
7. stg から prod 宛てのPRを作成する
8. GitHub上でレビュー・CI確認後にPRをマージする
```

ローカルで `git merge` を実行せず、マージはGitHub上のPRを通じて人が行います。AIには `.clinerules` で同じ運用を指示しますが、Rulesetは直接pushなどをサーバー側で拒否するための設定です。

## 設定完了チェックリスト

- [ ] `prod` ブランチを作成した
- [ ] `stg` ブランチを作成した
- [ ] `stg` 用Rulesetを有効化した
- [ ] `prod` 用Rulesetを有効化した
- [ ] `stg` と `prod` への直接pushが拒否されることを確認した
- [ ] `prod` と `stg` へのPR作成を確認した
- [ ] `Regression tests / regression` を必要なRulesetの必須チェックに設定した
- [ ] `feature/* → stg`、`stg → prod` のPR運用をチームで共有した