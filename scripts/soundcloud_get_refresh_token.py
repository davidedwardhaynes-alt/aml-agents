"""One-time SoundCloud OAuth helper — mints a long-lived refresh_token
that the GitHub Actions cron can use forever after.

Run once locally:
  python scripts/soundcloud_get_refresh_token.py \\
      --client-id $SOUNDCLOUD_CLIENT_ID \\
      --client-secret $SOUNDCLOUD_CLIENT_SECRET \\
      --redirect-uri http://localhost:8888/callback

The script will:
  1. Print the SoundCloud authorise URL — open it in your browser.
  2. SoundCloud redirects back to localhost with ?code=... — the
     script catches the code via a one-shot HTTP server.
  3. Exchanges the code for access_token + refresh_token.
  4. Prints the refresh_token. Add it as the
     SOUNDCLOUD_REFRESH_TOKEN GitHub Actions secret.

Prerequisites:
  - Register an app at https://developers.soundcloud.com (or use an
    existing one). Note the Client ID + Client Secret.
  - Configure http://localhost:8888/callback as an authorised redirect
    URI on the app's settings page.

After this one-time exchange, the daily cron uses the refresh_token
to get fresh access_tokens forever — no further manual steps."""

from __future__ import annotations

import argparse
import http.server
import json
import socketserver
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from typing import Any

SOUNDCLOUD_AUTH_URL = "https://soundcloud.com/connect"
SOUNDCLOUD_TOKEN_URL = "https://api.soundcloud.com/oauth2/token"


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    received_code: str | None = None
    received_error: str | None = None

    # Suppress the default access-log noise
    def log_message(self, *args: Any, **kwargs: Any) -> None:
        return

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            _CallbackHandler.received_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body style='font-family:-apple-system; padding:40px;'>"
                b"<h2>OAuth callback received.</h2>"
                b"<p>You can close this tab and return to the terminal.</p>"
                b"</body></html>"
            )
        elif "error" in params:
            _CallbackHandler.received_error = params["error"][0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                f"<html><body><h2>OAuth error: {params['error'][0]}</h2></body></html>".encode()
            )
        else:
            self.send_response(404)
            self.end_headers()


def _wait_for_callback(host: str, port: int, timeout_s: int = 300) -> str:
    """Spin up a one-shot HTTP server, return the OAuth code or raise."""
    with socketserver.TCPServer((host, port), _CallbackHandler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        deadline = __import__("time").time() + timeout_s
        while __import__("time").time() < deadline:
            if _CallbackHandler.received_code:
                httpd.shutdown()
                return _CallbackHandler.received_code
            if _CallbackHandler.received_error:
                httpd.shutdown()
                raise RuntimeError(f"OAuth error: {_CallbackHandler.received_error}")
            __import__("time").sleep(0.5)
        httpd.shutdown()
        raise TimeoutError("Timed out waiting for OAuth callback")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--client-secret", required=True)
    parser.add_argument(
        "--redirect-uri",
        default="http://localhost:8888/callback",
        help="Must match the redirect URI registered in your "
             "SoundCloud app settings.",
    )
    parser.add_argument("--scope", default="non-expiring")
    args = parser.parse_args()

    parsed = urllib.parse.urlparse(args.redirect_uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8888

    auth_params = {
        "client_id": args.client_id,
        "redirect_uri": args.redirect_uri,
        "response_type": "code",
        "scope": args.scope,
    }
    auth_url = (
        f"{SOUNDCLOUD_AUTH_URL}?{urllib.parse.urlencode(auth_params)}"
    )

    print()
    print("=" * 70)
    print("SoundCloud OAuth bootstrap")
    print("=" * 70)
    print()
    print("Opening this URL in your browser:")
    print(f"  {auth_url}")
    print()
    print(f"Listening for the callback on http://{host}:{port}/...")
    print()

    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    code = _wait_for_callback(host, port, timeout_s=300)
    print(f"  ✓ received OAuth code (length={len(code)})")

    # Exchange the code for tokens
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "client_id": args.client_id,
        "client_secret": args.client_secret,
        "redirect_uri": args.redirect_uri,
        "code": code,
    }).encode()

    req = urllib.request.Request(
        SOUNDCLOUD_TOKEN_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            tokens = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"\nToken exchange failed: {e}")
        return 1

    print()
    print("=" * 70)
    print("✓ SUCCESS — copy these into your GitHub Actions secrets")
    print("=" * 70)
    print()
    print(f"SOUNDCLOUD_CLIENT_ID       = {args.client_id}")
    print(f"SOUNDCLOUD_CLIENT_SECRET   = {args.client_secret}")
    print(f"SOUNDCLOUD_REFRESH_TOKEN   = {tokens.get('refresh_token', '(missing!)')}")
    print()
    print("Add these three at:")
    print("  https://github.com/davidedwardhaynes-alt/aml-agents/settings/secrets/actions")
    print()
    print("After the first cron run, the daily MP3 will appear on your")
    print("SoundCloud profile each morning. The refresh_token is long-lived")
    print("so this is a one-time setup.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
