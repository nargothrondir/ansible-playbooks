#!/usr/bin/env bash
# Disposable local containers only; no WireGuard module, Cloudflare or real inventory.
set -euo pipefail
cd "$(dirname "$0")/.."
release=${1:-bookworm}
case "$release" in bookworm|trixie) ;; *) echo 'Use bookworm or trixie' >&2; exit 1 ;; esac
image="warp-native-network-test:$release"
network="warp-native-test-$$"
receiver="warp-native-receiver-$$"
cleanup() {
    docker rm -f "$receiver" >/dev/null 2>&1 || true
    docker network rm "$network" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker build --build-arg "DEBIAN_RELEASE=$release" -t "$image" -f tests/Dockerfile .
docker network create "$network" >/dev/null
docker run -d --name "$receiver" --network "$network" "$image" python3 -m http.server 8080 >/dev/null
receiver_ip=$(docker inspect --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$receiver")
docker run --rm --cap-add NET_ADMIN --network "$network" -e "TEST_RECEIVER=$receiver_ip" "$image"
