# alpha-chat

Chat platform integrations for alpha-mono. Provides async clients, FastAPI endpoint builders, and adapter layers for connecting agents to Slack, Telegram, and GitHub.

## Installation

Install from PyPI:

```bash
pip install alpha-chat
```

For local development in this repo:

```bash
uv sync --all-packages
```

To build a distributable wheel:

```bash
uv build --package alpha-chat
```

## What's in this package

### Clients

Thin async wrappers over official SDKs.

| Client           | Wraps                  | Key methods                                              |
| ---------------- | ---------------------- | -------------------------------------------------------- |
| `SlackClient`    | `slack_sdk.WebClient`  | `send_message`, `set_status`, `react`, `open_modal`, `ack_slash_command` |
| `TelegramClient` | `python-telegram-bot`  | `send_message`, `set_webhook`, `delete_webhook`          |
| `GithubClient`   | `PyGithub`             | `get_repo`, `create_issue`, `list_prs`                   |

### Adapters

Bridge between platform events and an `Agent`.

| Adapter            | Handles                                              |
| ------------------ | ---------------------------------------------------- |
| `SlackAdapter`     | `handle_event`, `handle_command`, `handle_action`    |
| `TelegramAdapter`  | `handle_update`                                      |

Adapters maintain per-conversation history (up to 10 turns) and show a typing status while the agent is generating.

### Endpoint builders

FastAPI `APIRouter` factories. All Slack endpoints verify the `X-Slack-Signature` HMAC header before processing.

| Builder                    | Mounts                                      |
| -------------------------- | ------------------------------------------- |
| `build_slack_router`       | `POST /events`, `POST /commands`, `POST /actions` |
| `build_telegram_router`    | `POST /webhook`                             |

### `SlackChat` (declarative integration)

`SlackChat` is a `ChatContract` that lets you declare a Slack integration directly on an `AgentConfig`. `AlphaApp` reads the `chat` list and mounts the correct router automatically — no manual wiring needed.

```python
from alpha_core import AgentConfig
from alpha_chat import SlackChat

AgentConfig(
    name="Jarvis",
    model="gemini/gemini-flash-latest",
    chat=[SlackChat()],
)
```

Required env vars: `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`.

## Manual wiring

For full control, wire the pieces together yourself:

```python
from alpha_chat import SlackClient, SlackAdapter, build_slack_router
from fastapi import FastAPI
import os

slack_client = SlackClient(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
)
adapter = SlackAdapter(agent=my_agent, context=app_context, slack_client=slack_client)

app = FastAPI()
app.include_router(build_slack_router(adapter), prefix="/slack")
```

## Slack setup

1. Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps).
2. Under **OAuth & Permissions**, add bot token scopes:
   - `chat:write` — send messages
   - `im:history` — read DMs
   - `app_mentions:read` — receive @mentions
   - `channels:history` — read channel messages
3. Under **Event Subscriptions**, set the request URL to `https://<your-host>/events` and subscribe to `message.im` and `app_mention` events.
4. Install the app to your workspace and copy the bot token + signing secret to `.env`.

## See also

- [alpha-app](../app/README.md) — runtime framework that can host chat integrations
- [personal-agent](../../apps/personal-agent/README.md) — example app using Slack integration
- [Architecture](../../docs/architecture.md) — chat integration design details
