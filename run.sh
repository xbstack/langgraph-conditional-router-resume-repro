#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${ROOT_DIR}/.venv"
mkdir -p "${ROOT_DIR}/logs"
if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi
"${VENV_DIR}/bin/pip" install -q -r "${ROOT_DIR}/requirements.txt"
"${VENV_DIR}/bin/python" "${ROOT_DIR}/repro/repro.py" > "${ROOT_DIR}/logs/langgraph-1.2.11-before.json"
"${VENV_DIR}/bin/python" "${ROOT_DIR}/fixed/workaround.py" > "${ROOT_DIR}/logs/langgraph-1.2.11-workaround.json"
"${VENV_DIR}/bin/python" - "${ROOT_DIR}/logs/langgraph-1.2.11-before.json" "${ROOT_DIR}/logs/langgraph-1.2.11-workaround.json" <<'PY'
import json
import sys
from pathlib import Path

before = json.loads(Path(sys.argv[1]).read_text())
fixed = json.loads(Path(sys.argv[2]).read_text())
rows = {(r['saver'], r['failure_location']): r for r in before['results']}
for saver in ('memory', 'sqlite'):
    node = rows[(saver, 'node')]
    route = rows[(saver, 'route')]
    assert node['calls'] == {'node': 2, 'route': 1, 'sink': 1}, node
    assert node['result'] == {'value': 2}, node
    assert route['calls'] == {'node': 1, 'route': 1, 'sink': 0}, route
    assert route['result'] == {'value': 1}, route
    assert route['pending_after'] == [], route

for row in fixed['results']:
    assert row['first_error'] == 'temporary routing dependency failure', row
    assert row['calls'] == {'node': 1, 'router_node': 2, 'selector': 1, 'sink': 1}, row
    assert row['pending_before'] == ['router_node'], row
    assert row['pending_after'] == [], row
    assert row['result']['value'] == 2, row
    assert row['result']['route_decision'] == 'sink', row

print('REPRO_CONFIRMED')
print('WORKAROUND_CONFIRMED')
PY
