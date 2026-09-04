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
    headers = {"User-Agent": "HAH-Logs/1.0"}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")

        if not body.strip():
            return {}

        return json.loads(body)


def fetch_guild():
    if not GUILD_NAME:
        raise RuntimeError("GUILD_NAME is missing.")

    guild_url = API_BASE + urllib.parse.quote(GUILD_NAME, safe="")
    return http_json(guild_url)


def get_member_name(member):
    if isinstance(member, str):
        return member.strip()

    if not isinstance(member, dict):
        return None

    # Current Pika member format
    account = member.get("user")

    if isinstance(account, dict):
        username = account.get("username")

        if isinstance(username, str) and username.strip():
            return username.strip()

    # Other possible formats
    for key in ("username", "name", "ign"):
        value = member.get(key)

        if isinstance(value, str) and value.strip():
            return value.strip()

    player = member.get("player")

    if isinstance(player, str) and player.strip():
        return player.strip()

    if isinstance(player, dict):
        for key in ("username", "name", "ign"):
            value = player.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

    return None


def extract_members(data):
    members = None

    if isinstance(data, dict):
        if isinstance(data.get("members"), list):
            members = data["members"]

        elif isinstance(data.get("clan"), dict):
            clan = data["clan"]

            if isinstance(clan.get("members"), list):
                members = clan["members"]

        elif isinstance(data.get("data"), dict):
            info = data["data"]

            if isinstance(info.get("members"), list):
                members = info["members"]

    if members is None:
        raise RuntimeError(
            "Pika API responded, but HAH Logs could not find the member list."
        )

    names = set()

    for member in members:
        name = get_member_name(member)

        if name:
            names.add(name)

    if not names:
        raise RuntimeError(
            "Pika API returned a member list, but no usernames could be read."
        )

    return names


def load_state():
    if not STATE_FILE.exists():
        return None

    try:
        saved = json.loads(STATE_FILE.read_text(encoding="utf-8"))

        # Empty starter state = first run
        if not saved.get("updated_at"):
            return None

        return set(saved.get("members", []))

    except Exception:
        return None


def save_state(members):
    state = {
        "guild": GUILD_NAME,
        "members": sorted(members, key=str.lower),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    STATE_FILE.write_text(
        json.dumps(state, indent=2) + "\n",
        encoding="utf-8"
    )


def send_embed(title, description, color):
    if not DISCORD_WEBHOOK:
        raise RuntimeError("DISCORD_WEBHOOK is missing.")

    payload = {
        "username": "HAH Logs",
        "embeds": [
            {
                "title": title,
                "description": description,
                "color": color,
                "footer": {
                    "text": f"PikaNetwork • {GUILD_NAME}"
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ],
    }

    http_json(
        DISCORD_WEBHOOK,
        method="POST",
        payload=payload
    )


def main():
    guild_data = fetch_guild()
    current_members = extract_members(guild_data)
    previous_members = load_state()

    if previous_members is None:
        save_state(current_members)
        print(
            f"HAH Logs initialized successfully with "
            f"{len(current_members)} members."
        )
        return

    joined = sorted(
        current_members - previous_members,
        key=str.lower
    )

    left = sorted(
        previous_members - current_members,
        key=str.lower
    )

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

    save_state(current_members)

    print(
        f"Members: {len(current_members)} | "
        f"Joined: {len(joined)} | "
        f"Left: {len(left)}"
    )


if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
