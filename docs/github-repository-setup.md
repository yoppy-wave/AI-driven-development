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

## チーム開発向け設定ファイル

次のファイルは、すべて `disabled` のRuleset定義またはテンプレートです。現在の一人開発ではGitHubに適用・有効化しません。

```text
.github/rulesets/stg.json
.github/rulesets/prod.json
.github/rulesets/prod-merge-actors.json
.github/CODEOWNERS.example
```

- `stg.json` は、PR、開発者1人以上の承認、CI、force push禁止などの品質ゲートを担当します。
- `prod.json` は、PR、POによるCODEOWNERS承認、CI、force push禁止などの品質ゲートを担当します。
- `prod-merge-actors.json` は、`prod` の更新をリリース責任者に限定するための **Restrict updates** だけを担当します。

`stg.json` と `prod.json` に **Restrict updates** を入れないことが重要です。リリース責任者が更新者制限を通過するための例外権限を、品質ゲートのRulesetへ与えると、PO承認やCIまで回避できるためです。

## 必須ステータスチェック

Ruleset JSONには、既存ワークフローの `name` と job ID から得られる次のcheck contextを指定しています。

| check context | 定義元 |
| --- | --- |
| `Regression tests / regression` | `.github/workflows/regression.yml` の workflow名 `Regression tests`、job ID `regression` |
| `Pull request policy / validate` | `.github/workflows/pull-request-policy.yml` の workflow名 `Pull request policy`、job ID `validate` |

回帰テストはすべてのpushに加え、`stg` または `prod` 宛てのPRでも実行します。Rulesetを有効化する前に、対象ブランチへのPRで両方のcheck contextが実際に表示・成功することを確認してください。workflow名またはjob IDを変更した場合は、Rulesetの必須チェックも更新します。

## PR元ブランチの検証

`.github/workflows/pull-request-policy.yml` は、次を検証します。

- `prod` 宛てPRは、同一リポジトリの `stg` ブランチだけをPR元として許可する。
- `stg` 宛てPRは、`ALLOWED_STG_HEAD_PATTERNS` に指定したパターンだけをPR元として許可する。

このワークフローは `pull_request_target` でベースブランチ側の検証スクリプトを実行します。PRでポリシー検証コード自体を変更して必須チェックを弱めることを防ぐためであり、PR元のコードはcheckout・実行しません。

現在の許可パターンは `feature/*,fix/*` です。将来 `release/*` などを許可する場合は、ワークフローの `ALLOWED_STG_HEAD_PATTERNS` を変更します。

この検証はPRの宛先、PR元ブランチ名、PR元リポジトリを確認します。ブランチ名やGit履歴だけでは「作成時にstgから派生した」という操作履歴を完全には証明できないため、その点はPRレビューと運用で補完します。

## チーム開発への移行と有効化手順

以下はOrganizationリポジトリで、開発者、PO、リリース責任者を分ける手順です。個人所有リポジトリではTeamを使えないため、必要に応じてGitHubユーザーを指定してください。

1. `prod` と `stg` ブランチを作成する。この時点ではRulesetを有効化しない。
2. `.github/CODEOWNERS.example` を `.github/CODEOWNERS` にコピーし、`@YOUR_ORG/product-owners` をPOのvisible TeamまたはPOのGitHubユーザーへ置換する。
3. **CODEOWNERSを含むコミットを先に `prod` ブランチへ配置する。** `prod.json` のCODEOWNERS承認必須を有効にする前に、このファイルが `prod` に存在しなければ、PO承認は要求されない。
4. `stg` / `prod` 宛てのテストPRを作成し、`Regression tests / regression` と `Pull request policy / validate` が成功することを確認する。
5. GitHubの **Settings → Rules → Rulesets** で、`.github/rulesets/stg.json` と `.github/rulesets/prod.json` をインポートする。インポート直後も `disabled` のままであることを確認する。
6. `.github/rulesets/prod-merge-actors.json` をインポートする。インポートされたRulesetのbypass listに、リリース責任者のユーザーまたはTeamを追加し、bypass modeを **For pull requests only** にする。直接pushを許す `Always allow` は選ばない。
7. `stg` 用Rulesetを有効化する。開発者はPRを作成でき、作成者以外の開発者1人以上の承認、必須CI、会話解決を満たしたPRだけをマージできることを確認する。
8. `prod.json` と `prod-merge-actors.json` を有効化する。`prod` のCODEOWNERSにはPOだけを指定し、PO以外の承認ではマージできないことを確認する。

### prod のRuleset組み合わせ

`prod` には次のRulesetが同時に適用されます。

| Ruleset | 担当 | リリース責任者へのbypass |
| --- | --- | --- |
| `Protect prod quality gates` | PR必須、POのCODEOWNERS承認、CI、force push禁止、削除禁止 | なし |
| `Restrict prod merge actors` | `prod` の更新者を限定 | リリース責任者だけ、**For pull requests only** |

リリース責任者は2つ目のRulesetだけをPR上で通過できます。1つ目にはbypassがないため、リリース責任者でもPO承認・必須CI・PR経由を回避できません。PO承認とCIを満たしたPRは、リリース責任者が更新者制限を通過してマージできます。

Rulesetのbypass list、Repository role、TeamのメンバーシップはGitHub側の設定であり、JSONのテンプレートには固定しません。ルールを有効にする前に、管理者を含めて品質ゲートを無条件に回避できるbypassを設定していないことを確認してください。

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

マージはGitHub上のPRを通じて行います。RulesetとPRポリシーは、直接pushや許可されないPR元をサーバー側で拒否するための設定です。

## 設定完了チェックリスト

- [ ] `prod` ブランチを作成した
- [ ] `stg` ブランチを作成した
- [ ] `.github/CODEOWNERS` を `prod` ブランチへ配置した
- [ ] `stg` 用Rulesetを有効化した
- [ ] `prod` 用品質ゲートRulesetを有効化した
- [ ] `prod` 用更新者制限Rulesetを有効化し、リリース責任者をPR限定bypassに設定した
- [ ] `stg` と `prod` への直接pushが拒否されることを確認した
- [ ] `prod` と `stg` へのPR作成を確認した
- [ ] `Regression tests / regression` と `Pull request policy / validate` を必要なRulesetの必須チェックとして確認した
- [ ] `feature/* → stg`、`stg → prod` のPR運用をチームで共有した