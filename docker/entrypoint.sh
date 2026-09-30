#!/bin/sh
set -eu

if [ "${C360_BOOTSTRAP_DEMO:-1}" = "1" ] && [ ! -f "${C360_DATA_DIR}/warehouse.duckdb" ]; then
  echo "No warehouse found. Building the deterministic synthetic demo..."
  python -m customer360 demo --data-dir "${C360_DATA_DIR}" \
    --customers "${C360_DEMO_CUSTOMERS:-1800}" \
    --orders "${C360_DEMO_ORDERS:-36000}" \
    --seed "${C360_DEMO_SEED:-42}"
fi

exec streamlit run app.py \
  --server.address 0.0.0.0 \
  --server.port "${PORT:-8501}" \
  --server.headless true \
  --browser.gatherUsageStats false

