"""Validate the standalone schema in a disposable PostgreSQL container (Docker required)."""
import subprocess
import time
import uuid
from pathlib import Path

root = Path(__file__).resolve().parents[1]
name = 'scholarship-schema-check-' + uuid.uuid4().hex[:10]

def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kwargs)

try:
    run(['docker', 'run', '--detach', '--rm', '--network', 'none', '--name', name,
         '-e', 'POSTGRES_HOST_AUTH_METHOD=trust', 'postgres:16.8-alpine'])
    for _ in range(30):
        ready = subprocess.run(['docker', 'exec', name, 'pg_isready', '-U', 'postgres'], capture_output=True)
        if ready.returncode == 0:
            break
        time.sleep(0.5)
    else:
        raise RuntimeError('Temporary PostgreSQL did not become ready')
    for file in ['schema/scholarships.sql', 'tests/schema_checks.sql']:
        result = run(['docker', 'exec', '-i', name, 'psql', '-U', 'postgres', '-v', 'ON_ERROR_STOP=1'], input=(root / file).read_text())
        print(result.stdout)
finally:
    subprocess.run(['docker', 'rm', '-f', name], capture_output=True)
