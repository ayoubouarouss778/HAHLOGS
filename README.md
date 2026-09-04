# HAH Logs

HAH Logs — a free PikaNetwork guild join/leave logger using GitHub Actions and a Discord webhook.

## Setup

1. Create a new GitHub repository and upload all files from this project.
2. In Discord, open the channel you want for guild logs:
   **Edit Channel → Integrations → Webhooks → New Webhook → Copy Webhook URL**.
3. In the GitHub repository go to:
   **Settings → Secrets and variables → Actions**.
4. Under **Secrets**, create:
   - Name: `DISCORD_WEBHOOK`
   - Value: your Discord webhook URL
5. Under **Variables**, create:
   - Name: `GUILD_NAME`
   - Value: your exact PikaNetwork guild name
6. Go to **Actions → HAH Logs → Run workflow** once.
   The first run only saves the current guild member list and sends no join/leave messages.
7. After that, GitHub Actions checks automatically every 5 minutes.

## Notes

- `state.json` stores the last known guild roster.
- Do not put your Discord webhook URL directly inside the code.
- GitHub scheduled workflows can sometimes start a few minutes late.
- If PikaNetwork changes its API response format, the workflow may need a small parser update.
