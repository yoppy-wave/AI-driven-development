#!/usr/bin/env bash
# Install Docker Engine from Docker's official Ubuntu repository inside WSL2.
set -euo pipefail

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || fail 'Run with sudo bash scripts/setup-docker-engine-wsl.sh "$USER".'
target_user=${1:-${SUDO_USER:-}}
[[ -n "$target_user" && "$target_user" != root ]] || fail 'Pass the Ubuntu development user as the first argument.'
id "$target_user" >/dev/null 2>&1 || fail "User not found: $target_user"
grep -qi microsoft /proc/sys/kernel/osrelease || fail 'This script is for Ubuntu on WSL2.'
[[ $(ps -p 1 -o comm=) == systemd ]] || fail 'Enable systemd in /etc/wsl.conf and restart this WSL distribution first (see README).'

. /etc/os-release
[[ "$ID" == ubuntu ]] || fail 'This script supports Ubuntu only.'
case "$VERSION_ID" in
  22.04|24.04|26.04) ;;
  *) fail "Check Docker's supported Ubuntu releases before using $VERSION_ID." ;;
esac

# Do not remove another container runtime or override Docker Desktop integration.
conflicts=()
for package in docker.io docker-compose docker-compose-v2 docker-doc docker-buildx podman-docker containerd runc; do
  if [[ $(dpkg-query -W -f='${Status}' "$package" 2>/dev/null || true) == 'install ok installed' ]]; then
    conflicts+=("$package")
  fi
done
[[ ${#conflicts[@]} -eq 0 ]] || fail "Conflicting packages found; review the official migration instructions first: ${conflicts[*]}"
docker_binary=$(command -v docker || true)
for desktop_link in "$docker_binary" /usr/bin/docker /usr/local/bin/docker \
  /usr/local/lib/docker/cli-plugins/docker-buildx /usr/local/lib/docker/cli-plugins/docker-compose; do
  if [[ -L "$desktop_link" && $(readlink "$desktop_link") == /mnt/wsl/docker-desktop/* ]]; then
    fail "Docker Desktop link remains: $desktop_link. Disable WSL integration and quit Desktop; see README for leftover links."
  fi
done

apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker.service containerd.service
usermod -aG docker "$target_user"

printf '\nDocker Engine installed for %s. Reopen your Ubuntu session to apply group membership.\n' "$target_user"
printf 'Then run: docker version && docker compose version && docker run --rm hello-world\n'
