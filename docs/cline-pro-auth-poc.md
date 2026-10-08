# GitHub Actions × Cline CLI × ChatGPT Pro 認証PoC

検証日: 2026-10-09

## 判定

**FAIL（GitHub-hosted Runnerでの継続運用）**。ローカルではChatGPT Proに紐づく既存のCline認証で、Cline CLIの非対話実行が2回連続で成功した。一方、認証状態をGitHub Actions Secretsへ移し、トークン更新後も使い捨てRunner間で安全かつ確実に維持する方法は確認できなかった。したがって `.github/workflows/cline-poc.yml` は作成せず、Secretsへの認証情報登録とActions実行も行っていない。APIキー方式への切り替えも行っていない。

## Phase 1: ローカル

- Cline CLIの公式[README](https://github.com/cline/cline/blob/main/apps/cli/README.md)は、ChatGPTサブスクリプション向けの `openai-codex`、`cline auth openai-codex`、`--json` による非対話実行を案内している。
- 検証時のnpm公開版は **3.0.70**。開発コンテナの一時領域 `/tmp/cline-poc` に導入し、`cline --version` でも確認した。Node.jsは24.21.0。
- 既存の `openai-codex` 認証がClineの設定に保存されていたため、再ログイン用の `cline auth openai-codex` は実行していない。ブラウザー認証をやり直すと既存の認証状態が変わる可能性があるためである。
- [ローカル検証スクリプト](../scripts/cline_poc.py)で `OPENAI_API_KEY` などのAPIキー環境変数を子プロセスから除外し、`--provider openai-codex --json --auto-approve false` を明示した。README本文をプロンプトに渡し、一時ディレクトリで実行した。2回とも終了コード0で、JSONイベントと応答テキストの存在を確認した。イベント数は順に133、136。応答本文とCLIの生ログは表示していない。
- 認証ファイルの有無・項目名・アクセス権だけを検査した。値は出力していない。ファイル権限はコンテナ内で `600`、所有者は `vscode` だった。
- 認証のない隔離されたClineデータディレクトリでも同じコマンドを実行し、終了コード1・応答なしで停止することを確認した。生のエラー出力は表示していない。

再現する場合は、開発コンテナ内で次を実行する。認証がまだなければ、先に対話式の `cline auth openai-codex` を本人が実行する。

```bash
npm install --prefix /tmp/cline-poc cline@3.0.70
python3 scripts/cline_poc.py inspect
python3 scripts/cline_poc.py run --cli /tmp/cline-poc/node_modules/.bin/cline
```

スクリプトは認証値やモデルの回答を表示しない。成功/失敗、JSONイベント数、応答の有無だけを表示する。

## Phase 2: CI認証方式

Clineの[開発資料](https://github.com/cline/cline/blob/main/apps/cli/DEVELOPMENT.md)によると、認証は通常 `~/.cline/data/settings/providers.json` に保存される。`CLINE_DATA_DIR` や `CLINE_PROVIDER_SETTINGS_PATH` で場所を変更できる。`openai-codex` の設定にはアクセストークン、リフレッシュトークン、有効期限のメタデータが含まれる。[更新処理](https://github.com/cline/cline/blob/main/sdk/packages/core/src/auth/codex.ts)は期限の約5分前から更新を試み、更新応答から**新しいアクセストークンとリフレッシュトークン**を受け取る。[ランタイム側](https://github.com/cline/cline/blob/main/sdk/packages/core/src/runtime/orchestration/runtime-oauth-token-manager.ts)は更新結果をプロバイダー設定に保存する。

GitHub-hosted Runnerは[ジョブごとに新しいVMが作成され、終了後に破棄される](https://docs.github.com/en/actions/how-tos/manage-runners/github-hosted-runners/use-github-hosted-runners)。仮に現在の認証ファイルをSecretへ登録して毎回復元しても、Runner内で更新されたリフレッシュトークンは元のSecretへ自動反映されない。古いトークンがいつまで使えるか、同時実行時にどうなるかもこのPoCでは確認できない。再実行可能性を保証するには別の持続的な認証基盤と更新の同期が必要になる。Secretを書き換えるには[別途Secretsの書き込み権限](https://docs.github.com/en/rest/actions/secrets#create-or-update-a-repository-secret)が必要で、CIに高権限の資格情報を追加することになる。

利用条件についても確証がない。ClineはローカルでのChatGPTサブスクリプション利用を案内しているが、ClineのこのOAuth認証状態をGitHub-hosted Runnerへ移植して永続運用してよいという公式手順は見つからなかった。またOpenAIの[Sign in with ChatGPT利用条件](https://openai.com/policies/sign-in-with-chatgpt-terms/)は、その方式の認証トークンを永続保存する場合、ユーザー管理下のローカル環境に置き、リモートの管理環境に置かないよう定めている。**Clineの `openai-codex` がこの条件の対象かは確認できていない**ため、規約違反と断定はしない。ただし、GitHub Secretsへの認証状態移植を安全かつ条件に適合した方式と判断する根拠もない。

認証ファイルを無条件にコピーする方式は採用しない。アクセス期限切れ後の更新、リフレッシュトークンのローテーション、Runner破棄後の再実行は未検証であり、成功扱いにしない。

## Phase 3・4: 実行しなかった項目

Phase 2が成立していないため、手動起動のGitHub Actionsワークフローは作成していない。GitHub Secretsの追加、Actions実行、Runner上での5分制限・Summary表示・認証エラー停止・連続再実行の検証も未実施。ローカルの認証なし実行が安全に失敗した事実や、認証ありでの連続実行は、Runner破棄後の再実行を証明しない。

既存の `ai-question` / `ai-coding` ワークフローはGitHub Copilot CLI向けのままで、このPoCでは変更していない。ChatGPT Proの認証を使うものではない。

## Issue自動回答へ進む条件

まず、Pro認証をCIで利用できる正式な認証方式と、更新・ローテーションを安全に維持する方法を確認する必要がある。そのうえで、読み取り専用の手動PoCをGitHub-hosted Runnerで2回以上実行し、期限更新後の再実行まで確認する。成立して初めて、`ai-question` ラベルをトリガーにするIssue回答へ拡張する。公開Issueの本文は信用できない入力として扱い、AI実行環境へGitHubの書き込み資格情報を渡さず、回答の投稿は別工程で行う。

追加のOpenAI API従量課金を使わない別案として、本人が管理するローカル環境でClineを実行し、手元の認証状態を維持する方法は検討できる。ただし、それは今回指定されたGitHub-hosted Runnerでの成立を意味しない。
