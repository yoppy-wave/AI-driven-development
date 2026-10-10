# GitHubリポジトリの初回設定

このテンプレートからリポジトリを作成した後、GitHub上で一度設定する項目をまとめます。リポジトリ内のワークフローやルールファイルだけでは、保護ブランチへの直接push禁止などのサーバー側制限は有効になりません。

## ブランチ構成

次のブランチを作成します。

```text
main                                共通テンプレート・共通設定の基準ブランチ
├─ prod/<案件A>                      案件Aの本番相当・リリース対象
│  └─ stg/<案件A>                    案件Aの統合・検証ブランチ
│     └─ feature/<案件A>/<内容>      案件Aの個別開発ブランチ
└─ prod/<案件B>                      案件Bの本番相当・リリース対象
   └─ stg/<案件B>                    案件Bの統合・検証ブランチ
```

- `main` はテンプレート、共通ルール、共通CI、共通開発環境を管理します。案件固有の実装を常に戻すブランチではありません。
- `prod/<案件>` は案件ごとの本番相当ブランチで、本番へ出す変更だけを受け入れます。
- `stg/<案件>` は案件ごとの開発内容を統合・検証します。
- 実装は `stg/<案件>` を起点に作成した `feature/<案件>/<内容>` または `fix/<案件>/<内容>` ブランチで行います。
- 日常の変更は `feature/<案件>/*` または `fix/<案件>/*` から対応する `stg/<案件>` へのPRで取り込みます。
- リリース可能なまとまりになった時点で、対応する `stg/<案件>` から `prod/<案件>` へのPRを作成します。
- 共通テンプレート、共通ルール、共通CIの変更は、`main` を起点に作業ブランチを作成して `main` 宛てのPRで取り込みます。

案件を開始するときは、`main` を基準に `prod/<案件>` を作成し、そこから `stg/<案件>` を作成します。`main` は既定ブランチとして残します。共通設定を案件へ取り込む場合は、必要な案件の `stg/<案件>` 宛てに `main` からPRを作成して、案件ごとに検証します。

## GitHub Rulesetsの設定

GitHubで **Settings → Rules → Rulesets → New ruleset → New branch ruleset** を開き、`main`、`stg/**`、`prod/**` にそれぞれルールを作成します。Rulesetの名称は、例えば `Protect main`、`Protect staging branches`、`Protect production branches` にします。

### `main` 用Ruleset

対象ブランチを `main` に指定し、少なくとも次を有効にします。

- **Require a pull request before merging**: 有効
- **Block force pushes**: 有効
- **Restrict deletions**: 有効
- **Restrict updates**: 有効にし、直接更新を許可するユーザー・チーム・GitHub Appを必要最小限に限定

### `stg/**` 用Ruleset

対象ブランチを `stg/**` に指定し、少なくとも次を有効にします。

- **Require a pull request before merging**: 有効
- **Block force pushes**: 有効
- **Restrict deletions**: 有効
- **Restrict updates**: 有効にし、直接更新を許可するユーザー・チーム・GitHub Appを必要最小限に限定

必要に応じて、次も有効にします。

- **Require status checks to pass**: `Regression tests / regression`
- **Require approvals**: 少なくとも1件

### `prod/**` 用Ruleset

対象ブランチを `prod/**` に指定し、少なくとも次を有効にします。

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
案件固有の変更:
1. 対象案件の stg/<案件> を最新化する
2. stg/<案件> から feature/<案件>/<内容> または fix/<案件>/<内容> を作成する
3. 作業ブランチで実装・テスト・コミット・pushを行う
4. 作業ブランチから stg/<案件> 宛てのPRを作成する
5. GitHub上でレビュー・CI確認後にPRをマージする
6. stg/<案件> で統合・検証する
7. stg/<案件> から prod/<案件> 宛てのPRを作成する
8. GitHub上でレビュー・CI確認後にPRをマージする

共通基盤の変更:
1. main を最新化する
2. main から chore/<内容> または feature/<内容> を作成する
3. 作業ブランチで実装・テスト・コミット・pushを行う
4. 作業ブランチから main 宛てのPRを作成する
5. GitHub上でレビュー・CI確認後にPRをマージする
```

ローカルで `git merge` を実行せず、マージはGitHub上のPRを通じて人が行います。AIには `.clinerules` で同じ運用を指示しますが、Rulesetは直接pushなどをサーバー側で拒否するための設定です。

## 設定完了チェックリスト

- [ ] `main` 用Rulesetを有効化した
- [ ] `stg/**` 用Rulesetを有効化した
- [ ] `prod/**` 用Rulesetを有効化した
- [ ] 案件ごとに `prod/<案件>` と `stg/<案件>` を作成した
- [ ] `main`、`stg/<案件>`、`prod/<案件>` への直接pushが拒否されることを確認した
- [ ] `feature/<案件>/* → stg/<案件>` と `stg/<案件> → prod/<案件>` のPR作成を確認した
- [ ] 共通基盤の変更を作業ブランチから `main` へのPRで取り込めることを確認した
- [ ] `Regression tests / regression` を必要なRulesetの必須チェックに設定した
- [ ] `feature/<案件>/* → stg/<案件>`、`stg/<案件> → prod/<案件>` のPR運用をチームで共有した