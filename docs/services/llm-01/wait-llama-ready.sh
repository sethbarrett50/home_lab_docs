#!/usr/bin/env bash
set -euo pipefail

LLAMA_SERVER=/home/pooltab/src/llama.cpp/build/bin/llama-server
EXPECTED_IP=192.168.10.162
MAX_ATTEMPTS=60

for ((attempt=1; attempt<=MAX_ATTEMPTS; attempt++)); do
    if /usr/sbin/ip -4 -o addr show dev ens18 |
        /usr/bin/grep -q "inet ${EXPECTED_IP}/"; then

        if devices=$(/usr/bin/timeout 10 "$LLAMA_SERVER" --list-devices 2>&1); then
            if /usr/bin/grep -Eq 'CUDA[0-9]+:.*Quadro P4000' <<< "$devices"; then
                echo "Network address and CUDA P4000 ready"
                exit 0
            fi
        fi
    fi

    echo "Waiting for network address and CUDA GPU: attempt ${attempt}/${MAX_ATTEMPTS}"
    sleep 2
done

echo "ERROR: LLM prerequisites unavailable" >&2
exit 1
