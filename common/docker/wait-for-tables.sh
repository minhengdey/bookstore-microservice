#!/bin/sh
# Source from service entrypoints when SKIP_MIGRATE=1 and WAIT_FOR_TABLE is set.
if [ -n "$WAIT_FOR_TABLE" ]; then
  echo "Waiting for migrations (tables: $WAIT_FOR_TABLE)..."
  python /app/common/common/wait_for_tables.py
fi
