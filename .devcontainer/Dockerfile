# Python, Git, GitHub CLI, Pulumi CLI, common development tools, and the non-root vscode user.
# Node.js is added by the Feature in devcontainer.json.
ARG PYTHON_VERSION=3.12
FROM mcr.microsoft.com/devcontainers/python:${PYTHON_VERSION}-bookworm

USER root

COPY .pulumi.version /tmp/pulumi.version

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH=/opt/pulumi/bin:${PATH}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        build-essential \
        curl \
        git \
        jq \
        ripgrep \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        gh \
    && pulumi_version="$(cat /tmp/pulumi.version)" \
    && case "$(dpkg --print-architecture)" in \
        amd64) pulumi_arch=x64 ;; \
        arm64) pulumi_arch=arm64 ;; \
        *) echo "Unsupported Pulumi architecture: $(dpkg --print-architecture)" >&2; exit 1 ;; \
    esac \
    && pulumi_archive="pulumi-v${pulumi_version}-linux-${pulumi_arch}.tar.gz" \
    && curl --fail --location --silent --show-error \
        "https://github.com/pulumi/pulumi/releases/download/v${pulumi_version}/${pulumi_archive}" \
        --output "/tmp/${pulumi_archive}" \
    && curl --fail --location --silent --show-error \
        "https://github.com/pulumi/pulumi/releases/download/v${pulumi_version}/SHA512SUMS" \
        --output /tmp/pulumi-sha512sums \
    && grep " ${pulumi_archive}$" /tmp/pulumi-sha512sums \
        | sed "s#  #  /tmp/#" \
        | sha512sum --check --status \
    && mkdir -p /opt/pulumi/bin \
    && tar --extract --gzip --file "/tmp/${pulumi_archive}" --directory /opt/pulumi/bin --strip-components=1 \
    && pulumi version \
    && rm -f /tmp/pulumi.version "/tmp/${pulumi_archive}" /tmp/pulumi-sha512sums \
    && rm -rf /var/lib/apt/lists/*

USER vscode
