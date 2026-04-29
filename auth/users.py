"""Auth helpers — load and save the local credentials YAML.

This is demo-grade auth: bcrypt-hashed passwords stored in a local file.
Not suitable for production multi-tenant deployment. For that, migrate to
Supabase Auth or similar service-backed identity provider.
"""

from __future__ import annotations  # Python 3.9 compatibility for `str | None`

from pathlib import Path
from typing import Any

import yaml

CREDENTIALS_PATH = Path(__file__).parent / "credentials.yaml"
AVATARS_DIR = Path(__file__).parent.parent / "data" / "avatars"


def save_avatar(username: str, data: bytes, ext: str) -> Path:
    """Save a user's profile photo. Replaces any existing avatar for the user."""
    AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    ext = (ext or "png").lower().lstrip(".")
    if ext not in {"png", "jpg", "jpeg"}:
        ext = "png"
    target = AVATARS_DIR / f"{username}.{ext}"
    # Remove any existing avatars with different extensions
    for other_ext in {"png", "jpg", "jpeg"} - {ext}:
        old = AVATARS_DIR / f"{username}.{other_ext}"
        if old.exists():
            old.unlink()
    target.write_bytes(data)
    return target


def get_user_avatar_path(username: str) -> Path | None:
    """Return path to the user's avatar, or None if not set."""
    if not AVATARS_DIR.exists():
        return None
    for ext in ("png", "jpg", "jpeg"):
        path = AVATARS_DIR / f"{username}.{ext}"
        if path.exists():
            return path
    return None


def _config_from_streamlit_secrets() -> dict[str, Any] | None:
    """If running on Streamlit Cloud (or any host with st.secrets configured),
    build the auth config from st.secrets["auth_yaml"] (raw YAML string) or
    st.secrets["credentials"] (dict). Returns None if no secrets present.

    Required secret schema (TOML form in Streamlit Cloud's secrets UI):

        auth_yaml = '''
        credentials:
          usernames:
            demo:
              email: demo@trustsphere.partners
              name: Demo User
              password: $2b$12$...bcrypt-hash...
        cookie:
          name: aml_agents_auth
          key: <random-32+-char-string>
          expiry_days: 30
        pre-authorized:
          emails: []
        '''
    """
    try:
        import streamlit as st  # local import — keeps this module importable
                                # from cron / scripts that don't load streamlit
        # st.secrets behaves like a dict but raises if the secrets file is absent
        secrets = st.secrets
        if "auth_yaml" in secrets:
            return yaml.safe_load(secrets["auth_yaml"])
        if "credentials" in secrets:
            # secrets is a Mapping — coerce to plain dict for streamlit-authenticator
            return {
                "credentials": dict(secrets["credentials"]),
                "cookie": dict(secrets.get("cookie", {
                    "name": "aml_agents_auth",
                    "key": secrets.get("cookie_key", "change-me-in-production"),
                    "expiry_days": 30,
                })),
                "pre-authorized": dict(secrets.get("pre-authorized", {"emails": []})),
            }
    except Exception:
        pass
    return None


def load_config() -> dict[str, Any]:
    """Load the credentials YAML.

    Resolution order:
      1. Local file at auth/credentials.yaml (dev + container with mounted secret)
      2. Streamlit secrets (Streamlit Cloud / hosted demo)
      3. Empty default (no users; users self-register via the login screen)
    """
    if CREDENTIALS_PATH.exists():
        with open(CREDENTIALS_PATH) as f:
            return yaml.safe_load(f)

    secrets_config = _config_from_streamlit_secrets()
    if secrets_config:
        return secrets_config

    return {
        "credentials": {"usernames": {}},
        "cookie": {
            "name": "aml_agents_auth",
            "key": "change-me-in-production",
            "expiry_days": 30,
        },
        "pre-authorized": {"emails": []},
    }


def save_config(config: dict[str, Any]) -> None:
    """Persist the updated credentials YAML.

    On hosted deploys with a read-only filesystem this will fail silently — the
    in-memory config still updates for the current session. Profile changes
    persist across reruns of the same container but not across redeploys; that's
    acceptable for demo. Production should migrate to Supabase Auth.
    """
    try:
        CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CREDENTIALS_PATH, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    except (OSError, PermissionError):
        # Read-only filesystem — common on managed hosts. Silent fail is fine
        # because the in-memory config is the source of truth for this session.
        pass


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
