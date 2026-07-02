#!/usr/bin/env bash
#
# No-docker path for the cross-instance failover demo: two local solara backends sharing a
# local Redis, behind a local Caddy round-robin proxy. Ctrl-C stops everything.
#
# Prerequisites (see README.md):
#   - a running Redis            (redis-server --maxmemory-policy noeviction)
#   - the redis-cli tool         (for the reachability check below)
#   - Caddy 2                    (https://caddyserver.com/docs/install)
#   - solara with the redis extra:  pip install 'solara[redis]'
#
# Then:  ./run.sh   and open  http://localhost:8000

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Shared state config. The SAME secret on both backends is MANDATORY: envelopes are HMAC-signed
# and a mismatch silently fails every cross-instance restore. Override via the environment.
export SOLARA_STATE_BACKEND="${SOLARA_STATE_BACKEND:-redis}"
export SOLARA_STATE_URL="${SOLARA_STATE_URL:-redis://localhost:6379/0}"
export SOLARA_STATE_SECRET_KEYS="${SOLARA_STATE_SECRET_KEYS:-demo-shared-secret-change-me}"

# 1. Redis must be reachable.
if ! command -v redis-cli >/dev/null 2>&1; then
	echo "redis-cli not found. Install Redis (e.g. 'brew install redis' or 'apt install redis-tools')." >&2
	exit 1
fi
if ! redis-cli ping >/dev/null 2>&1; then
	echo "Redis does not answer PING at localhost:6379. Start it first, e.g.:" >&2
	echo "  redis-server --maxmemory-policy noeviction" >&2
	exit 1
fi

# 2. Caddy must be installed.
if ! command -v caddy >/dev/null 2>&1; then
	echo "caddy not found. Install Caddy 2 (https://caddyserver.com/docs/install)." >&2
	exit 1
fi

# 3. solara must be installed.
if ! command -v solara >/dev/null 2>&1; then
	echo "solara not found. Install it with:  pip install 'solara[redis]'" >&2
	exit 1
fi

pids=()
cleanup() {
	echo
	echo "Shutting down..."
	for pid in "${pids[@]:-}"; do
		kill "$pid" 2>/dev/null || true
	done
	wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting solara backend on :8765 ..."
solara run "$HERE/app.py" --host localhost --port 8765 --production &
pids+=($!)

echo "Starting solara backend on :8766 ..."
solara run "$HERE/app.py" --host localhost --port 8766 --production &
pids+=($!)

echo "Starting Caddy round-robin on :8000 ..."
caddy run --config "$HERE/Caddyfile" &
pids+=($!)

echo
echo "Open http://localhost:8000  (Ctrl-C to stop)"
wait
