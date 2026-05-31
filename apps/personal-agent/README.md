# personal-agent

Personal AI assistant connected to Slack via `alpha_chat`.

## Setup

Set the following environment variables in `.env`:

```
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
ANTHROPIC_API_KEY=...
```

## Running

```bash
personal-agent
```

The server starts on `http://0.0.0.0:8000`. Point your Slack app's event subscription URL to `https://<your-host>/events`.

Required Slack scopes: `chat:write`, `im:history`, `app_mentions:read`, `channels:history`.
