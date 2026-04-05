#!/usr/bin/env bash
# Launch the Python backend and the Vite frontend dev server together.
# Press Ctrl-C to stop both.

set -m
cd "$(dirname "$0")/.."

cleanup() {
    trap - INT TERM EXIT
    for pid in $(jobs -p); do
        kill -TERM "-$pid" 2>/dev/null || true
    done
    wait 2>/dev/null
}
trap cleanup INT TERM EXIT

python -m backend.main &
npm run dev &

while (( $(jobs -pr | wc -l) == 2 )); do
    sleep 0.5
done
