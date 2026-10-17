# AI-driven development

WSL2のUbuntuにDocker Engineを直接インストールし、VS Code Dev Containersで使う開発環境です。Docker Desktopは不要です。Python 3.12、Node.js 24、Git、GitHub CLIを用意し、コンテナに接続した際にClineなどの拡張機能を自動インストールします。

Dockerfileは言語・OSツール、`devcontainer.json`はNode.jsの追加、拡張機能、エディター設定を担当します。初回はフォルダーを開いて **Reopen in Container（コンテナーで再度開く）** を選択してください。通常のフォルダーを開くだけではコンテナの作成や拡張機能の導入は始まりません。

## AWS CDKによるIaC開発の準備

Dev ContainerにはPython、Node.js、Git、GitHub CLIを含めています。依存関係をインストールした後、次でローカル検証します。

```bash
npm ci
python -m pip install -r requirements-dev.txt
npm run typecheck
npm test
python -m pytest
npm run synth
```

AWSリソースはTypeScriptのCDK Stackで定義し、LambdaのPython実装は`lambda.Code.fromAsset()`で参照します。Stack名は`app-development`、`app-staging`、`app-production`、PR一時環境の`app-pr-<PR番号>`に固定します。アカウントID、Role ARN、アクセスキー、接続情報をソースやStack Outputへ書きません。

リソースへ変更を加える前に対象AWSアカウント、リージョン、Stack、変更・削除対象、データのバックアップと復旧方法を確認します。明示的な承認なしに`cdk deploy`、`cdk destroy`、`cdk bootstrap`、AWS認証を実行しません。

## 再利用可能なCI/CD基盤

`.github/workflows/reusable-ci.yml`はクラウド非依存のCI、`.github/workflows/reusable-aws-cdk.yml`はAWS CDK用アダプターです。どちらもGitHub Actionsの`workflow_call`で呼び出す再利用ワークフローであり、仕様に従って`.github/workflows/`直下に置いています。`.github/workflows/cicd.yml`はPR・信頼済みブランチへのpush・手動実行の入口、`.github/workflows/cicd-preview-cleanup.yml`はPR close時の一時環境削除の入口です。

アプリ固有の有効化状態は[`.github/cicd/application.json`](.github/cicd/application.json)で管理します。初期状態ではAWS CDK、PRごとの一時環境、development / staging / productionデプロイをすべて無効にしているため、AWS認証情報が未設定でもクラウド操作は行いません。CIは設定検証と、検出したPython・Node.jsプロジェクトの`test`、任意の`lint`、`typecheck`、`build`、`synth`を実行します。GitHub Actionsのworkflowを編集する際は、Dev ContainerとVS Codeの推奨拡張に含めた公式のGitHub Actions拡張機能で構文・設定のフィードバックを確認します。この構成ではCI上の独立したGitHub Actions構文検証は行いません。

実際に有効化する前に、次を設定してください。

1. `.github/cicd/application.json`の`cdk.enabled`、必要な`deployments`、PR一時環境を使う場合は`previewEnvironmentEnabled`を`true`にする。
2. `preview`、`development`、`staging`、`production`のGitHub Environmentを作成し、対象AWSアカウント・リージョン・Stackに限定したOIDC Role ARNを`AWS_ROLE_TO_ASSUME` **Environment Secret**として設定する。再利用workflowは必要Secretを`workflow_call.secrets`で明示し、callerはこの名前だけを明示的に渡す。実行jobにはEnvironmentを割り当てるため、同名のEnvironment Secretがcallerから渡されたSecretより優先される。
3. `preview`、`staging`、`production`にはrequired reviewersを設定する。特に`preview`はPR起点でクラウド認証情報を使うため、承認なしに実行できないようにする。productionには承認者と必要なdeployment branch policyも設定する。

PR一時環境は`app-pr-<PR番号>`だけを使用します。`preview`の`diff`成功後に同じStackへの`deploy`を直列実行します。Fork PRおよび`OWNER`、`MEMBER`、`COLLABORATOR`以外のPR作成者では、Secretsを使う一時環境作成を実行しません。cleanup対象はCDK deploy前にGitHub Actionsが記録したStack名、リージョン、PR SHA、信頼済みworkflow SHAから復元するため、後続コミットで設定を無効化・変更してもPR close時の削除対象を失いません。cleanupはPRコードを実行せず、CloudFormationのアカウント、リージョン、Stack名、タグ、状態を検証してからPR専用Stackだけを削除します。

## 初回の準備

### 1. WSL2・UbuntuとVS Code

WSL2・Ubuntuがまだない場合は、管理者のPowerShellで次を実行し、要求された場合はWindowsを再起動します。初回のUbuntu起動時にLinuxのユーザー名とパスワードを設定します。

```powershell
wsl --install -d Ubuntu
```

インストール済みの場合はここから進めます。PowerShellの `wsl --list --verbose` でUbuntuのVERSIONが `2` であることを確認します。`1` の場合は `wsl --set-version Ubuntu 2` で変換します。

WindowsにVS Codeをインストールし、PowerShellで次を実行します。`.vscode/extensions.json` にも同じ拡張機能を推奨として登録しています。

```powershell
wsl --set-default Ubuntu
code --install-extension ms-vscode-remote.remote-wsl
code --install-extension ms-vscode-remote.remote-containers
```

VS Codeで `Ctrl+Shift+P` → **Preferences: Open User Settings (JSON)** を開き、既存の設定オブジェクトに次の2項目を追加します。Windows側のフォルダーから操作した場合も、Dev ContainersがUbuntu内のDockerを使うようにする設定です。インストール済みのDocker DesktopがVS Codeから起動されることを避けます。

```json
{
  "dev.containers.executeInWSL": true,
  "dev.containers.executeInWSLDistro": "Ubuntu"
}
```

これはWindows側VS Codeのユーザー設定であり、`.vscode/settings.json` や `devcontainer.json` には入れません。ディストリビューション名を変えている場合は `wsl --list --quiet` の名前に合わせます。

PowerShellで `wsl -d Ubuntu` を実行します。ここからのBashコマンドは、WSLのUbuntuで実行します。

### 2. Ubuntuのsystemdを確認

```bash
ps -p 1 -o comm=
```

`systemd` と表示されれば次へ進めます。違う場合は、`sudo nano /etc/wsl.conf` で既存設定を残したまま次を設定します。既存の `[boot]` があれば、そのセクションの `systemd` を変更します。

```ini
[boot]
systemd=true
```

Ubuntuの作業を保存して終了し、PowerShellで `wsl --terminate Ubuntu` を実行してから `wsl -d Ubuntu` で開き直します。[Microsoftのsystemd手順](https://learn.microsoft.com/windows/wsl/systemd)も参照できます。

### 3. Ubuntu内にDocker Engineをインストール

Ubuntuでこのプロジェクトのフォルダーへ移動し、次を実行します。Windowsの `C:\Users\<Windowsユーザー名>\Documents\ChatGPT\AI-driven-development` は、Ubuntuでは `/mnt/c/Users/<Windowsユーザー名>/Documents/ChatGPT/AI-driven-development` です。

```bash
sudo bash scripts/setup-docker-engine-wsl.sh "$USER"
```

スクリプトは[Docker公式のUbuntu向け手順](https://docs.docker.com/engine/install/ubuntu/)に沿ってAPTリポジトリを登録し、Docker Engine・CLI・Buildx・Composeをインストールします。Ubuntu 22.04 / 24.04 / 26.04を対象とし、systemdによるUbuntu起動時のDocker起動と、指定ユーザーの `docker` グループへの追加を設定します。再実行すると、APTで取得可能な最新版へ更新されることがあります。

`docker` グループはUbuntu内でroot相当の権限を持ちます。会社ではこの利用方式も社内方針に合わせてください。[Dockerのインストール後の手順](https://docs.docker.com/engine/install/linux-postinstall/)に説明があります。

インストール後、グループへの追加をVS Codeにも反映するため、Ubuntu内の作業を保存し、WSL接続中のVS Codeを閉じます。PowerShellでUbuntuを再起動します。

```powershell
wsl --terminate Ubuntu
wsl -d Ubuntu
```

開き直したUbuntuで確認します。

```bash
docker version
docker compose version
docker buildx version
docker run --rm hello-world
```

`docker version` にClientとServerの両方が表示され、`hello-world` が成功すれば準備完了です。Dockerを手動で起動する場合は `sudo systemctl start docker` を使います。

### Docker Desktopを以前使っていた場合

先にDocker Desktopの **Settings → Resources → WSL Integration** で、既定ディストリビューションへの連携とUbuntuへの連携を無効にして適用し、Docker Desktopを終了してください。自動起動も無効にします。Desktop用コンテナ・イメージ・ボリュームはUbuntu内のDocker Engineとは別の保存先であり、自動移行されません。

連携が残った状態では、Ubuntuの `docker` がDesktop用コマンドへのリンクになっていることがあります。導入スクリプトはこれを検出すると停止します。`ls -l /usr/bin/docker` と `docker info` で接続先を確認してください。

連携を無効化して終了した後もリンクが残る場合は、エラーに表示されたファイルを `ls -l` で確認し、リンク先が `/mnt/wsl/docker-desktop/` 配下のものだけを別名に退避して再実行します。CLIのほか、Buildx・Composeのリンクが残ることもあります。Dockerのデータディレクトリを削除する必要はありません。

移行後に `docker-credential-desktop.exe` のエラーが出る場合は、Ubuntuの `~/.docker/config.json` をバックアップし、`"credsStore": "desktop.exe"` の設定を見直します。認証情報や他の設定は保持し、必要なレジストリにはUbuntu側で再ログインしてください。

## 開発環境を開く

1. WSLのUbuntuでこのプロジェクトのフォルダーへ移動し、`code .` を実行します。VS Code左下が **WSL: Ubuntu** になることを確認します。Windows側でフォルダーを開いている場合は、まず `Ctrl+Shift+P` → **WSL: Reopen Folder in WSL** を選択します。
2. VS Codeで `Ctrl+Shift+P` → **Dev Containers: Reopen in Container** を選択します。
3. 初回のイメージ取得・ビルド・拡張機能のインストール完了を待ちます。初回はインターネット接続が必要です。
4. 左下にDev Containerへの接続が表示されたら、新しいターミナルを開きます。

この構成では、WSL接続のウィンドウからDev Containerを開くことでUbuntu内のDocker Engineを使用します。接続の通知が出なくても、上記コマンドから開始できます。WindowsのPowerShellでの `docker` の成否は、この構成の動作確認には使いません。

ファイル操作の性能のため、今後プロジェクトを配置する際は、Windows側の `/mnt/c/...` よりWSL側の `~/projects/...` を推奨します。フォルダーを `~/projects/AI-driven-development` に配置した場合の例:

```bash
cd ~/projects/AI-driven-development
code .
```

コンテナ内のターミナルで確認できます。

```bash
python3 --version
node --version
npm --version
git --version
gh --version
rg --version
.venv/bin/python -m pip --version
whoami
```

Pythonは3.12系、Node.jsは24系、ユーザーは `vscode` になる想定です。プロジェクト直下の `.venv` はコンテナ作成時に生成され、Python拡張もこの環境を使用します。ターミナルで明示的に有効化する場合は `source .venv/bin/activate` を実行します。

Windows側のフォルダーをマウントした際のGitの所有者チェックに対応するため、コンテナ作成時にこのプロジェクトのパスだけを、コンテナ内ユーザーの `safe.directory` に登録します。

### GitとGitHub CLIの初期設定

Dev Container内のターミナルで、コミットに表示する名前とメールアドレスを設定します。`XXXX` は自分の情報に置き換えてください。これらはコンテナ内ユーザーのグローバルGit設定（`~/.gitconfig`）に保存されます。

```bash
git config --global user.name "XXXX"
git config --global user.email "XXXX"
```

続けてGitHub CLIへログインします。対話形式でGitHub.com、使用するGitプロトコル、ブラウザー認証を選び、表示された案内に従います。

```bash
gh auth login
```

完了後は、次でログイン中のアカウントを確認できます。

```bash
gh auth status
```

認証トークンやパスワードはREADME・Git管理対象ファイル・ソースコードに書かないでください。Dev Containerを削除・再作成すると、コンテナ内のGit設定やGitHub CLI認証は失われるため、その場合はこの手順をもう一度実行します。

Windowsなど別の環境で作成済みの `.venv` がある場合は、コンテナを初めて作る前に別名に退避してください。Pythonのバージョンを変更するときも、既存の `.venv` を退避してから再ビルドしてください。

## 含まれる拡張機能

| 拡張機能 | 用途 |
| --- | --- |
| Cline | AIによる開発支援 |
| Python / Pylance / Python Debugger | Pythonの補完・解析・デバッグ |
| Ruff | Pythonの静的解析・整形 |
| ESLint | JavaScript / TypeScriptの静的解析 |
| Prettier | JavaScript / TypeScript / JSONの整形 |

「クライアント」はClineを指している想定で設定しています。別のAI拡張を使う場合は、`.devcontainer/devcontainer.json` の `customizations.vscode.extensions` にある `saoudrizwan.claude-dev` を目的の拡張IDに置き換えます。

Clineはインストール後、サイドバーから利用するプロバイダー・モデルと認証を設定してください。手順は[Clineの公式ドキュメント](https://docs.cline.bot/getting-started/installing-cline)を参照できます。APIキーはDockerfileやGit管理対象の設定ファイルに書かず、Clineの設定画面で入力します。

ESLintのプロジェクト設定やnpmパッケージ、Pythonのアプリ依存関係は、アプリを作る段階で追加します。Ruff拡張は整形・解析用で、ターミナル用の `ruff` コマンドが必要ならPythonの開発依存関係にも追加してください。

## 設定の変更

- Pythonのバージョン: `devcontainer.json` の `build.args.PYTHON_VERSION`。
- Node.jsのバージョン: `devcontainer.json` のNode Featureの `version`。
- OSの追加ツール（GitHub CLIを含む）: `.devcontainer/Dockerfile` の `apt-get install`。
- 自動導入する拡張機能: `devcontainer.json` の `customizations.vscode.extensions`。

変更後は **Dev Containers: Rebuild Container** を実行してください。バージョン指定はPythonのマイナー版とNode.jsのメジャー版までです。同じバージョン帯の更新を取り込むため、ビルド時期によってパッチ版が変わることがあります。

3000・5173・8000番ポートはVS Codeで転送する設定です。サーバー自体はアプリを追加した後に起動してください。

Dockerfileだけを `docker build` した場合、Node.js Feature・拡張機能・`.venv` 作成は適用されません。開発環境の構築にはDev Containersを使用してください。

## GitHub Codespacesで使う場合

このフォルダーをGitHubリポジトリにコミットし、Codespaceを作成すると、`.devcontainer/devcontainer.json` を使って環境を構築できます。Codespaces側にはコンテナを動かす仕組みがあるため、WSLや上記のDocker Engine導入スクリプトの実行は不要です。Clineの認証は利用する環境で設定してください。[GitHubのDev Container設定ガイド](https://docs.github.com/en/codespaces/setting-up-your-project-for-codespaces/adding-a-dev-container-configuration/introduction-to-dev-containers)も参照できます。

## GitHubリポジトリの初回設定

`prod` / `stg` ブランチの作成、直接pushを防ぐRuleset、必須CIなど、GitHub画面上で一度行う設定は[GitHubリポジトリの初回設定](docs/github-repository-setup.md)を参照してください。

## issueの質問にAIで回答する

以下のActionsワークフローはOpenAI APIキー方式です。

[`.github/workflows/ai-question.yml`](.github/workflows/ai-question.yml) は、issueに `ai-question` ラベルを付けたときに起動します。GitHub ActionsのUbuntu 24.04上でPython 3.12、Node.js 24、Cline CLIを用意し、issueのタイトルと本文を質問として渡します。Clineはその時点のソースを調べ、回答を同じissueへコメントします。読み取り以外のツールをフックで止め、作業ツリーが変更された場合も投稿を停止します。

利用前に[OpenAI Platform](https://platform.openai.com/api-keys)でAPIキーを作成し、リポジトリの **Settings → Secrets and variables → Actions** にRepository secret `OPENAI_API_KEY` として登録してください。ChatGPT Proとは別のAPI利用料金が発生します。使用モデルを変える場合はRepository variable `CLINE_MODEL` にOpenAI APIで利用できるモデルIDを設定します。未設定時は `gpt-5.4` を使います。キーをファイルへ書いたり、Gitへコミットしたりしないでください。

ワークフローを既定ブランチに反映し、GitHub上に `ai-question` という名前のラベルを作成してから、質問したいissueへ付けます。既にラベルが付いているissueでは、一度外して付け直すと再実行できます。現在のリポジトリにアプリケーションコードがない質問では、その旨を回答する設定です。Cline CLIの処理が失敗した場合、回答コメントは投稿されません。

## issueからAIに実装させる

[`.github/workflows/ai-coding.yml`](.github/workflows/ai-coding.yml) は、issueに `ai-coding` ラベルを付けたときに起動します。Cline CLIが既存コードとテストを確認して計画を立て、実装と関連チェックを行います。変更があれば `ai-coding/issue-<番号>` ブランチの**ドラフトPR**を作成・更新し、issueをPR本文から参照します。既定ブランチには直接反映しません。変更がない場合はClineの報告をissueにコメントします。

`ai-question` と同じRepository secret `OPENAI_API_KEY` を使い、Repository variable `CLINE_MODEL` でモデルを変更できます。Cline CLIにはPR作成用トークンを渡さず、後続の工程だけがPRを作成します。GitHubの **Settings → Actions → General → Workflow permissions** では、GitHub Actionsによるプルリクエストの作成を許可してください。GitHub上に `ai-coding` ラベルを作成し、ワークフローを既定ブランチへ反映してから利用します。

この自動実装では `.github/` 配下の変更はPR化せず、実行を停止します。ワークフローやAI指示ファイル自体の変更は別途レビューして行ってください。

既定の `GITHUB_TOKEN` で作ったPRのチェックは、GitHubの設定によって実行承認が必要になります。PR作成後のCIも自動実行したい場合は、`contents: write` と `pull-requests: write` の権限を持つPersonal Access TokenをRepository secret `AI_CODING_PR_TOKEN` に登録できます。登録しなければ `GITHUB_TOKEN` を使用します。Cline CLI実行中にはPR作成用トークンを渡さず、PRは必ず人が内容を確認してからマージしてください。実装用Clineはコマンドを実行できるため、APIキーはその実行環境から参照可能です。信頼できる担当者だけが `ai-coding` ラベルを付け、APIキーには利用上限を設定してください。

## pushで既存機能の破壊を検知する

[`.github/workflows/regression.yml`](.github/workflows/regression.yml) は、すべてのブランチへのpush時に、pushされたコミットをテストします。同じブランチへ連続してpushされた場合は、実行中の古いテストをキャンセルして最新のpushを優先します。APIキーなどのSecretsは渡さず、リポジトリは読み取り権限でチェックアウトします。

現在は `.github/scripts/` に実装ファイルと並べて置いた既存テストと、複数ファイルを横断する `tests/` 配下のテストを毎回実行します。Pythonの単一実装・設定ファイル向けテストは実装ファイルと同じディレクトリに `<実装ファイル名>_test.py` として置き、CI/CD workflowなどを横断するテストは `tests/` に置きます。今後アプリを追加した場合は、[回帰テスト実行スクリプト](.github/scripts/run_regression.py) がPythonの `pyproject.toml` / `requirements.txt` と、TypeScriptの `package.json` を探し、各プロジェクトのテストを実行します。Pythonは依存関係を導入してから `pytest`、Node.jsは `test` スクリプト（設定があれば `lint` と `typecheck` も）を使います。Pythonの `*_test.py` またはNode.jsの `test` スクリプトがない場合は失敗させ、テストなしの新機能を見落とさないようにします。Node.jsでは再現可能な依存関係のため、npm・pnpm・Yarnのロックファイルを1つ置いてください。

テストでは、既存の条件・計算・戻り値の破壊、重要な処理の呼び出し削除、複数の入口での判断不一致、APIや型の変更に伴う更新漏れを検知するケースを追加してください。詳しい観点は [共通指示](.github/copilot-instructions.md) と [言語別指示](.github/instructions/) にあります。ワークフローはテストを実行しますが、テストが期待される振る舞いを十分に表しているかはレビューが必要です。DBなどを使う結合テストを追加した際は、必要なサービスと初期データもワークフローに設定してください。

## 会社・チームで利用する際の検討事項：Squidの通信先許可リスト

将来、会社の方針に合わせてプロキシで外部通信を制限する場合の記載例を [`.devcontainer/squid/whitelist.txt`](.devcontainer/squid/whitelist.txt) に置いています。現在はSquidを起動しておらず、このファイルによる通信制限も有効にしていません。

このファイルはSquidの `dstdomain` ACLに読み込ませる想定で、**1行に1つのホスト名**を書きます。Markdown、URL、正規表現ではありません。例えばSquid側では `acl allowed_hosts dstdomain "/etc/squid/whitelist.txt"` のように参照し、許可・拒否の `http_access` ルールと組み合わせます。[SquidのACL説明](https://wiki.squid-cache.org/SquidFaq/SquidAcl)と[ホスト名リストを使う設定例](https://wiki.squid-cache.org/ConfigExamples/Authenticate/Bypass)を参照してください。

この方式は接続先のホスト名を対象とします。HTTPSの `/3/` や `/docs/` などのパスまでは制限できません。ポートを443に限定する設定もリストとは別に必要です。記載したホスト名は説明用であり、会社が承認した通信先を意味しません。

実際に制限するには、Squidの設定・起動、開発コンテナからの通信をプロキシに通す設定、プロキシを経由しない通信を防ぐネットワーク側の設定が必要です。Gitのリモート、npm・PyPI、AIサービス、MCPサーバー、拡張機能の配布元なども用途を確認してから許可先に追加します。

## 公式資料

- [VS Code: Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers)
- [VS Code: WSL内のDocker Engineを使用する構成](https://code.visualstudio.com/remote/advancedcontainers/docker-options)
- [Dev ContainersのPythonイメージ](https://github.com/devcontainers/images/tree/main/src/python)
- [Node.js Feature](https://github.com/devcontainers/features/tree/main/src/node)
