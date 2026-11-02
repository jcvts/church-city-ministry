import os
import subprocess
import sys
from pathlib import Path


def test_api_engine_uses_configured_database_path(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "church_city_kids.db"

    environment = os.environ.copy()
    environment["CHURCH_CITY_KIDS_DB_PATH"] = str(database_path)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from church_city_kids.api.dependencies import engine; "
                "print(engine.url.database)"
            ),
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()) == database_path
