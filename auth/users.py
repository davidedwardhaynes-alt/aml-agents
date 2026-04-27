"""Auth helpers — load and save the local credentials YAML.

This is demo-grade auth: bcrypt-hashed passwords stored in a local file.
Not suitable for production multi-tenant deployment. For that, migrate to
Supabase Auth or similar service-backed identity provider.
"""

from pathlib import Path
from typing import Any

import yaml

CREDENTIALS_PATH = Path(__file__).parent / "credentials.yaml"


def load_config() -> dict[str, Any]:
    """Load the credentials YAML. Creates a minimal default if missing."""
    if not CREDENTIALS_PATH.exists():
        return {
            "credentials": {"usernames": {}},
            "cookie": {
                "name": "aml_agents_auth",
                "key": "change-me-in-production",
                "expiry_days": 30,
            },
            "pre-authorized": {"emails": []},
        }
    with open(CREDENTIALS_PATH) as f:
        return yaml.safe_load(f)


def save_config(config: dict[str, Any]) -> None:
    """Persist the updated credentials YAML."""
    with open(CREDENTIALS_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def get_user_profile(config: dict[str, Any], username: str) -> dict[str, str]:
    """Return profile fields used to default the Filing metadata form."""
    user = config.get("credentials", {}).get("usernames", {}).get(username, {})
    return {
        "reporting_institution": user.get("reporting_institution", ""),
        "analyst_name": user.get("analyst_name", ""),
        "mlro_name": user.get("mlro_name", ""),
        "entity_category": user.get("entity_category", "— Select —"),
    }


def update_user_profile(
    config: dict[str, Any],
    username: str,
    *,
    reporting_institution: str | None = None,
    analyst_name: str | None = None,
    mlro_name: str | None = None,
    entity_category: str | None = None,
) -> None:
    """Update a user's profile fields. Caller is responsible for save_config()."""
    users = config.setdefault("credentials", {}).setdefault("usernames", {})
    if username not in users:
        users[username] = {}
    profile = users[username]
    if reporting_institution is not None:
        profile["reporting_institution"] = reporting_institution
    if analyst_name is not None:
        profile["analyst_name"] = analyst_name
    if mlro_name is not None:
        profile["mlro_name"] = mlro_name
    if entity_category is not None:
        profile["entity_category"] = entity_category
