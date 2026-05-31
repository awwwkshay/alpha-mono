# personal-agent

Personal AI assistant ("Jarvis") connected to Slack via `alpha_chat`. Responds to direct messages and @mentions in channels, with tools for web search, URL summarisation, and date/time lookups, plus workflows for daily briefs and research summarisation.

## Features

- Responds to Slack DMs and @mentions in channels
- Maintains per-conversation message history (up to 10 turns)
- Shows a typing status while generating

### Tools

| Tool                  | What it does                                      |
| --------------------- | ------------------------------------------------- |
| `get_current_datetime` | Returns the current date and time                |
| `web_search`          | Searches the web using DuckDuckGo                 |
| `summarise_url`       | Fetches and summarises a URL                      |

### Workflows

| Workflow              | What it does                                                 |
| --------------------- | ------------------------------------------------------------ |
| `daily_brief`         | Generates a daily summary from configured news sources       |
| `research_summarise`  | Searches, reads, and synthesises a research topic            |

## Setup

```bash
cp .env.example .env
```

Add the following to `.env`:

```
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
GEMINI_API_KEY=...
```

## Running

```bash
uv run personal-agent
```

The server starts on `http://0.0.0.0:8001`. Point your Slack app's **Event Subscriptions** request URL to `https://<your-host>/events`.

## Slack app configuration

Required bot token scopes:

| Scope              | Required for               |
| ------------------ | -------------------------- |
| `chat:write`       | Sending messages           |
| `im:history`       | Reading DMs                |
| `app_mentions:read`| Receiving @mentions        |
| `channels:history` | Reading channel messages   |

Subscribe to these bot events: `message.im`, `app_mention`.

## See also

- [alpha-chat](../../packages/chat/README.md) — Slack integration details
- [alpha-app](../../packages/app/README.md) — the framework this app is built on
