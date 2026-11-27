#!/usr/bin/env bash
# Claude Code Stop hook: runs `make check` whenever Claude is about to finish a turn.
#
# Exit code 2 tells Claude Code to block the stop and hand this script's stderr to
# Claude, which then has to deal with the failure before it can finish.
#
# Loop guard: Claude Code sets "stop_hook_active" to true in the JSON it sends on
# stdin when Claude is already continuing because a Stop hook blocked it. In that
# case a still-failing check is reported as a warning and Claude may stop. Without
# the guard, a failure Claude cannot fix (Docker not running, a test you broke on
# purpose) would keep it working forever (docs/DECISIONS.md, D28).

set -u

input=$(cat)
already_blocked=$(printf '%s' "$input" | jq -r '.stop_hook_active // false' 2>/dev/null || echo false)

cd "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}" || exit 0

# -k: keep going after a failing gate, so one run reports every failure.
# --tb=short: shorter pytest tracebacks, since this output goes into Claude's context.
if output=$(PYTEST_ADDOPTS="--tb=short" make -k check 2>&1); then
    exit 0
fi

if [ "$already_blocked" = "true" ]; then
    echo '{"systemMessage": "make check is still failing. The Stop hook already blocked once this turn, so Claude was allowed to stop."}'
    exit 0
fi

{
    echo "Stop hook: make check failed. Fix the cause, or tell the user why it cannot be fixed."
    echo
    printf '%s\n' "$output" | tail -n 200
} >&2
exit 2
