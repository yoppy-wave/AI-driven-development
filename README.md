# AI-driven development

WSL2のUbuntuにDocker Engineを直接インストールし、VS Code Dev Containersで使う開発環境です。Docker Desktopは不要です。Python 3.12、Node.js 24、Git、GitHub CLIを用意し、コンテナに接続した際にClineなどの拡張機能を自動インストールします。

Dockerfileは言語・OSツール、`devcontainer.json`はNode.jsの追加、拡張機能、エディター設定を担当します。初回はフォルダーを開いて **Reopen in Container（コンテナーで再度開く）** を選択してください。通常のフォルダーを開くだけではコンテナの作成や拡張機能の導入は始まりません。

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

## 会社・チームで利用する際の検討事項：通信先の許可リスト

会社でAI開発環境を利用する際は、社内方針に沿って、AIがアクセスしてよい外部サイトや通信先を定めることを検討します。現時点では将来の検討事項として記録しており、許可リストや通信制限は導入していません。

記載例は [`docs/examples/whitelist.md`](docs/examples/whitelist.md) にあります。自動適用されない場所に置いています。導入時は内容を編集・レビューしたうえで `.clinerules/whitelist.md` へコピーし、Clineのルールとして有効にしてください。

記載例のファイルには、Clineへの短い指示とURL一覧だけを記載しています。見出しや説明文は必須ではありません。この例は公式ドキュメントの参照・取得を対象とし、会社としての承認済みリストを意味しません。URLは正規表現ではなく、同じHTTPSのホスト・ポートにある記載パス配下を許可する例です。別のサブドメインやポートは含めず、一覧外へのリンクやリダイレクトも事前確認の対象にしています。

Clineでは、例えば `.clinerules/whitelist.md` に許可するURL・ドメインと、一覧外へのアクセス前に確認するルールをMarkdownで記述できます。`whitelist.md` は任意のファイル名です。Clineのルールとして有効にし、Gitで管理することでチームに共有できます。仕組みは[Clineのルールに関する公式ドキュメント](https://docs.cline.bot/customization/cline-rules)を参照してください。

会社で導入する際には、次の運用を決め、必要に応じて実際のルールに追記します。

- 許可範囲と用途、一覧外へのアクセスの承認担当者、リストの変更・レビュー担当。
- 一覧外へのアクセス時に説明する内容（宛先・目的・操作内容・送信する情報）。一度の承認を恒久的な許可にせず、Clineが独断でリストを広げないこと。
- 許可URLであっても、社内のソースコード・認証情報・個人情報などをURLのクエリや送信内容に含めないこと。

Gitのリモートリポジトリ、npm・PyPIなどのパッケージ配布元、AIサービス、MCPサーバー、拡張機能の配布元は、この記載例には含まれていません。実際に必要な通信先と用途を確認し、社内承認後に追加してください。

MarkdownのルールはAIへの行動指示であり、通信を技術的に遮断するものではありません。AIサービスへのAPI通信や、ターミナルで実行するプログラムの通信全体を、このファイルだけで制限することはできません。会社の要件として一覧外への通信を強制的に禁止する場合は、プロキシやファイアウォールなどによる制御も別途設計します。

## 公式資料

- [VS Code: Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers)
- [VS Code: WSL内のDocker Engineを使用する構成](https://code.visualstudio.com/remote/advancedcontainers/docker-options)
- [Dev ContainersのPythonイメージ](https://github.com/devcontainers/images/tree/main/src/python)
- [Node.js Feature](https://github.com/devcontainers/features/tree/main/src/node)
