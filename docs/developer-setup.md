# 開発者セットアップ

この文書は、新しく参加する開発者が自分の端末とアカウントを準備し、Dev Container内で開発を始めるまでの手順です。GitHub・AWSのプロジェクト初期設定は[GitHubリポジトリの初回設定](github-repository-setup.md)、日々の作業は[開発ガイド](development-guide.md)を参照してください。

認証情報、APIキー、パスワードをソースコード、Git管理対象ファイル、READMEへ保存しないでください。

## 準備の分担

| 各開発者が手動で準備するもの | Dev Containerが準備するもの |
| --- | --- |
| WSL2、Linuxディストリビューション、Docker Engine、VS Code | Python 3.12系の開発環境 |
| VS CodeのWSL / Dev Containers拡張機能 | Node.js 24系 |
| GitHubアカウント、Git設定、GitHub CLI認証 | Git、GitHub CLI、`rg`などのツール |
| リポジトリのclone | プロジェクト直下の`.venv` |
| ClineなどのAIツールに対する個人の認証 | Cline、Python、Ruff、ESLint、Prettier、GitHub Actions拡張機能 |
| 会社のプロキシ・証明書・ネットワーク要件への対応 | このリポジトリで定義したVS Code設定とポート転送 |

## 1. 端末とアカウントの準備

### WSL2、Docker Engine、VS Code

Windowsでローカル開発する場合は、WSL2、Linuxディストリビューション、Docker Engine、VS Codeを**各自で手動インストール**します。このリポジトリはOSやDocker Engineの導入を自動化しません。Docker Desktopは必須ではありません。

- [MicrosoftのWSLインストールガイド](https://learn.microsoft.com/windows/wsl/install)
- [Docker EngineのUbuntu向け公式手順](https://docs.docker.com/engine/install/ubuntu/)
- [Dockerのインストール後の手順](https://docs.docker.com/engine/install/linux-postinstall/)（Dockerを非rootユーザーで利用する場合）
- [VS CodeのDev Containers利用ガイド](https://code.visualstudio.com/docs/devcontainers/containers)

VS Codeには、少なくともWSL拡張機能とDev Containers拡張機能を導入します。`.vscode/extensions.json`にも推奨拡張機能として登録されています。

### GitHubアカウントとGit

プロジェクト管理者からリポジトリへのアクセスを受け、cloneする**前に**privateリポジトリへのアクセス権限と認証方法を確認します。HTTPSではOSやGit Credential Managerなどの認証機構、SSHではGitHubアカウントへ登録したSSH鍵を使ってcloneします。WSLホスト側にGitHub CLIを必ずインストールする必要はありません。

WSLホスト側のGit認証は`git clone`や`git push`で使う認証であり、Dev Container内の`gh auth login`はGitHub CLIでIssueやPRを操作するための認証です。別の環境として扱い、それぞれ必要な場所で設定します。認証トークンや秘密鍵をソースコード、Git管理対象ファイル、シェル履歴へ保存しないでください。

Gitの表示名とメールアドレスを設定します。以下はDev Container内で設定する例です。

```bash
git config --global user.name "あなたの名前"
git config --global user.email "あなたのメールアドレス"
```

## 2. ローカルでのリポジトリ取得とDev Container起動

WSL側のファイルシステムにcloneします。ファイル操作性能のため、Windows側の`/mnt/c/...`ではなく、たとえば`~/projects/...`を推奨します。

```bash
mkdir -p ~/projects
cd ~/projects
git clone <リポジトリのURL>
cd AI-driven-development
code .
```

VS Code左下が **WSL: Ubuntu** など、WSL接続であることを確認します。Windows側でフォルダーを開いた場合は、まず `Ctrl+Shift+P` → **WSL: Reopen Folder in WSL** を選択します。

次に `Ctrl+Shift+P` → **Dev Containers: Reopen in Container** を選択します。初回はイメージの取得、コンテナのビルド、拡張機能のインストールがあるため、インターネット接続が必要です。通常のフォルダーを開くだけでは、コンテナ作成や拡張機能の導入は始まりません。

コンテナ接続後、`.venv`は自動作成され、Python拡張機能はこの環境を使います。ターミナルで明示的に有効化する場合は次を実行します。

```bash
source .venv/bin/activate
```

Windowsなど別環境で作成済みの`.venv`がある場合は、初回作成前に別名へ退避してください。Pythonバージョンを変える場合も、既存の`.venv`を退避してからコンテナを再ビルドします。

## 3. GitHub Codespacesを利用する場合

GitHub Codespacesでも、リポジトリにある`.devcontainer/devcontainer.json`を利用して開発環境を作成できます。Codespacesを利用する場合、ローカルのWSL2とDocker Engineのセットアップは不要です。

1. GitHub上で対象リポジトリを開き、開発するブランチを選択します。
2. **Code → Codespaces** を開き、**Create codespace** を選択します。
3. ブラウザーまたはVS CodeでCodespaceを開き、環境構築の完了を待ちます。
4. [GitHub公式ドキュメント](https://docs.github.com/en/codespaces/developing-in-a-codespace/creating-a-codespace-for-a-repository)を参照し、組織の利用・課金方針と利用可能な作成方法を確認します。

CodespaceはローカルのDev Containerとは別の実行環境です。ClineなどのAIツールの認証は、利用する環境ごとに設定してください。認証情報をリポジトリへ保存しない方針はCodespacesでも同じです。

## 4. コンテナと個人認証の確認

コンテナ内の新しいターミナルで、環境を確認します。

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

Pythonは3.12系、Node.jsは24系、ユーザーは`vscode`になる想定です。コンテナ作成時に、現在のワークスペースだけをGitの`safe.directory`へ登録します。

Dev ContainerまたはCodespace内でGitHub CLIを使う場合はログインします。対話画面でGitHub.com、利用するGitプロトコル、ブラウザー認証を選びます。

```bash
gh auth login
gh auth status
```

Dev ContainerまたはCodespaceを削除・再作成すると、コンテナ内のGit設定とGitHub CLI認証は失われる場合があります。その場合は再設定してください。

## 5. AI開発ツールの準備

Dev ContainerはCline拡張機能を自動インストールします。インストール後、VS Codeのサイドバーから利用するプロバイダー、モデル、認証を各自で設定します。手順は[Clineの公式ドキュメント](https://docs.cline.bot/getting-started/installing-cline)を参照してください。

APIキーはClineの設定画面など、個人の安全な認証領域へ入力します。Dockerfile、`.devcontainer/`配下、Git管理対象の設定ファイル、コミットには保存しません。別のAI拡張機能を使う場合は、個人環境で追加するか、プロジェクトとして標準化する必要がある場合は管理者・チームで検討します。

## 6. 依存関係と初回検証

アプリケーション依存関係はDev Containerでは自動導入しません。コンテナ内で次を実行します。

```bash
npm ci
python -m pip install -r requirements-dev.txt
npm run typecheck
npm test
python -m pytest
npm run synth
```

現在のリポジトリには、AWS CDKのTypeScript構成、Lambdaサンプル、Python・TypeScriptのテストがあります。AWS操作は初期状態で無効です。`cdk deploy`、`cdk destroy`、`cdk bootstrap`、AWS認証は、対象アカウント、リージョン、Stack、変更・削除対象、復旧方法を確認した明示承認なしに実行しません。

`Dockerfile`だけを`docker build`しても、Node.js Feature、VS Code拡張機能、`.venv`作成は適用されません。開発環境の構築にはDev Containersを使用してください。`devcontainer.json`やDockerfileを変更した場合は **Dev Containers: Rebuild Container** を実行します。

## 7. 会社ネットワーク・プロキシの確認

会社環境では、clone、Dockerイメージ取得、VS Code拡張機能、npm、PyPI、GitHub CLI、AIサービスへの通信が許可されているかを確認します。プロキシ、独自CA証明書、VPN、パッケージレジストリの設定が必要な場合は、会社の手順に従って各自の環境へ設定します。

`.devcontainer/squid/whitelist.txt`は、将来Squidで通信先を制限するときの記載例です。現在はSquidを起動しておらず、このファイルによる通信制限も有効ではありません。実際に導入する場合は、プロキシ設定、コンテナの通信経路、プロキシ迂回の防止、Git・npm・PyPI・AIサービス・拡張機能配布元などの許可先を、組織の承認を得て設計します。

## 開発開始チェックリスト

- [ ] ローカル開発の場合、WSL2、Linux、Docker Engine、VS Code、WSL / Dev Containers拡張機能を手動で準備した
- [ ] clone前にprivateリポジトリへのアクセス権限と、HTTPSまたはSSHの認証を確認した
- [ ] ローカル開発の場合、WSL側のファイルシステムへリポジトリをcloneし、VS CodeでWSL接続後にDev Containerを起動できた
- [ ] Codespacesを利用する場合、GitHub上でCodespaceを作成し、既存のDev Container定義による環境構築を完了した
- [ ] コンテナ内でPython 3.12系、Node.js 24系、Git、GitHub CLIを確認できた
- [ ] Gitの表示名・メールアドレスを設定し、`gh auth status`でGitHub認証を確認した
- [ ] Clineなど利用するAIツールの個人認証を完了し、認証情報をリポジトリへ保存していない
- [ ] `npm ci`と`python -m pip install -r requirements-dev.txt`が成功した
- [ ] `npm run typecheck`、`npm test`、`python -m pytest`、`npm run synth`が成功した
- [ ] 必要なプロキシ、VPN、証明書、通信許可を確認した