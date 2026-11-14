ARG DEBIAN_RELEASE=bookworm
FROM debian:${DEBIAN_RELEASE}
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 iproute2 nftables iptables ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY files/warp-native.py /usr/local/libexec/warp-native
COPY tests/network.py /test/network.py
CMD ["python3", "/test/network.py"]
