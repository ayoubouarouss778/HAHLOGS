import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_BASE = "https://stats.pika-network.net/api/clans/"
STATE_FILE = Path("state.json")

GUILD_NAME = os.environ.get("GUILD_NAME", "").strip()
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "").strip()

def http_json(url, method="GET", payload=None, timeout=25):
    data = None
    headers = {"User-Agent": "PikaGuildLogger/1.0"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def fetch_guild():
    if not GUILD_NAME:
        raise RuntimeError("GUILD_NAME is missing.")
    url = API_BASE + urllib.parse.quote(GUILD_NAME, safe="")
    return http_json(url)

def member_name(member):
    if isinstance(member, str):
        return member.strip()
    if not isinstance(member, dict):
        return None

    # Common Pika/API shapes
        user = member.get("user")
    if isinstance(user, dict):
        username = user.get("username")
        if isinstance(username, str) and username.strip():
            return username.strip()
    for key in ("username", "name", "player", "ign"):
        value = member.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            for subkey in ("username", "name", "ign"):
                sub = value.get(subkey)
                if isinstance(sub, str) and sub.strip():
                    return sub.strip()

    profile = member.get("profile")
    if isinstance(profile, dict):
        for key in ("username", "name", "ign"):
            value = profile.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None

def extract_members(data):
    candidates = []
    if isinstance(data, dict):
        if isinstance(data.get("members"), list):
            candidates = data["members"]
        elif isinstance(data.get("clan"), dict) and isinstance(data["clan"].get("members"), list):
            candidates = data["clan"]["members"]
        elif isinstance(data.get("data"), dict) and isinstance(data["data"].get("members"), list):
            candidates = data["data"]["members"]

    names = {n for m in candidates if (n := member_name(m))}
    if not names:
        raise RuntimeError(
            "Could not find guild members in the Pika API response. "
            "The API format may have changed."
        )
    return names

def load_state():
    if not STATE_FILE.exists():
        return None
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return set(data.get("members", []))
    except Exception:
        return None

def save_state(members):
    STATE_FILE.write_text(
        json.dumps(
            {
                "guild": GUILD_NAME,
                "members": sorted(members, key=str.lower),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

def send_embed(title, description, color):
    if not DISCORD_WEBHOOK:
        raise RuntimeError("DISCORD_WEBHOOK is missing.")
    payload = {
        "username": "HAH Logs",
        "embeds": [{
            "title": title,
            "description": description,
            "color": color,
            "footer": {"text": f"PikaNetwork • {GUILD_NAME}"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]
    }
    http_json(DISCORD_WEBHOOK, method="POST", payload=payload)

def main():
    guild = fetch_guild()
    current = extract_members(guild)
    previous = load_state()

    # First run: establish baseline so every existing member isn't announced as "joined".
    if previous is None:
        save_state(current)
        print(f"Initialized {GUILD_NAME} with {len(current)} members.")
        return

    joined = sorted(current - previous, key=str.lower)
    left = sorted(previous - current, key=str.lower)

    for player in joined:
        send_embed(
            "🟢 Guild Member Joined",
            f"**{player}** joined **{GUILD_NAME}**.",
            0x57F287,
        )

    for player in left:
        send_embed(
            "🔴 Guild Member Left",
            f"**{player}** left **{GUILD_NAME}**.",
            0xED4245,
        )

    save_state(current)
    print(f"Members: {len(current)} | Joined: {len(joined)} | Left: {len(left)}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
