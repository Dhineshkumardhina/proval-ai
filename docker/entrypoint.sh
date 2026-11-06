#!/bin/sh
set -e

echo "==> PropVal AI: Validating database connection..."
python -c "
import sys, time
from app.core.config import settings
from app.core.database import engine
from sqlalchemy import text

max_retries = 30
for i in range(max_retries):
    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        print('==> PropVal AI: Database connectivity verified successfully.')
        sys.exit(0)
    except Exception as e:
        if i == max_retries - 1:
            print(f'==> PropVal AI ERROR: Database connection failed after {max_retries} attempts: {e}', file=sys.stderr)
            sys.exit(1)
        print(f'==> PropVal AI: Waiting for database readiness ({i+1}/{max_retries})...')
        time.sleep(2)
"

echo "==> PropVal AI: Executing Alembic database migrations..."
alembic upgrade head

echo "==> PropVal AI: Starting Uvicorn production server on port ${PORT:-8000} (Workers: ${WORKERS:-4})..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WORKERS:-4}"
