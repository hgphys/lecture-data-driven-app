"""Render the SA JSON + sheet_id into the TOML expected by Streamlit Cloud.

The output is written to ../private/secrets-for-cloud.toml (outside the git
working tree). Paste its contents into the app's Settings → Secrets panel.

Run from public/:
    uv run python scripts/build_cloud_secrets.py
"""

from __future__ import annotations

import json
from pathlib import Path

_PRIVATE = Path(__file__).resolve().parents[2] / "private"
_KEY = _PRIVATE / "credentials" / "lecture-data-driven-app-abc933c022db.json"
_OUT = _PRIVATE / "secrets-for-cloud.toml"
_SHEET_ID = "1ouiz0yy8CKdmMRwM7HDLpGXYCXcDP_Nb4VCcKmOB7wA"

_FIELDS = [
    "type",
    "project_id",
    "private_key_id",
    "private_key",
    "client_email",
    "client_id",
    "auth_uri",
    "token_uri",
    "auth_provider_x509_cert_url",
    "client_x509_cert_url",
    "universe_domain",
]


def _toml_str(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def main() -> int:
    info = json.loads(_KEY.read_text())
    lines = [f'sheet_id = "{_SHEET_ID}"', "", "[gcp_service_account]"]
    for field in _FIELDS:
        if field in info:
            lines.append(f"{field} = {_toml_str(info[field])}")
    _OUT.write_text("\n".join(lines) + "\n")
    print(f"Wrote {_OUT}")
    print(f"Lines: {len(lines)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
