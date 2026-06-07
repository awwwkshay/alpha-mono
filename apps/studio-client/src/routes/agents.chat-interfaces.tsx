import { createFileRoute } from "@tanstack/react-router";
import { Bot, Plug, Plus, Trash2 } from "lucide-react";
import { useCallback, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { InterfaceForm } from "@/components/forms/interface-form";
import {
  STUDIO_SYNC_EVENT,
  type AgentSummary,
  type InterfaceConfig,
  getAgents,
  getStandaloneInterfaces,
  removeAgentInterface,
  removeStandaloneInterface,
} from "@/lib/api";
import { useApi } from "@/hooks/use-api";

export const Route = createFileRoute("/agents/chat-interfaces")({
  component: AgentsChatInterfacesRoute,
});

type FlatInterface = {
  iface: InterfaceConfig;
  agent?: { id: string; name: string };
};

function AgentsChatInterfacesRoute() {
  const loadAgents = useCallback(() => getAgents(), []);
  const loadStandalone = useCallback(() => getStandaloneInterfaces(), []);
  const agents = useApi(loadAgents);
  const standaloneInterfaces = useApi(loadStandalone);
  const [dialogOpen, setDialogOpen] = useState(false);

  function sync() {
    window.dispatchEvent(new Event(STUDIO_SYNC_EVENT));
  }

  async function handleRemove(iface: InterfaceConfig, agentId?: string) {
    try {
      if (agentId) {
        await removeAgentInterface(agentId, iface.id);
      } else {
        await removeStandaloneInterface(iface.id);
      }
      sync();
    } catch {
      // silently ignore
    }
  }

  const agentList: AgentSummary[] = agents.status === "ready" ? agents.data : [];
  const standalone: InterfaceConfig[] =
    standaloneInterfaces.status === "ready" ? standaloneInterfaces.data : [];

  const allInterfaces: FlatInterface[] = [
    ...standalone.map((iface) => ({ iface })),
    ...agentList.flatMap((agent) =>
      (agent.chat ?? []).map((iface) => ({
        iface,
        agent: { id: agent.id, name: agent.name },
      })),
    ),
  ];

  return (
    <div className="grid gap-5">
      <section className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Chat Interfaces</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Chat platform integrations configured in this Clay app.
          </p>
        </div>

        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="size-4" />
              Interface
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add interface</DialogTitle>
              <DialogDescription>
                Configure a chat platform integration. Optionally wire it to an agent now, or save
                it standalone and assign it later.
              </DialogDescription>
            </DialogHeader>
            <InterfaceForm
              agents={agentList}
              onSuccess={() => {
                sync();
                setDialogOpen(false);
              }}
            />
          </DialogContent>
        </Dialog>
      </section>

      <section className="grid gap-4">
        {allInterfaces.length > 0 ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {allInterfaces.map(({ iface, agent }) => (
              <InterfaceCard
                key={agent ? `${agent.id}-${iface.id}` : iface.id}
                iface={iface}
                agent={agent}
                onRemove={() => void handleRemove(iface, agent?.id)}
              />
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="flex min-h-40 flex-col items-center justify-center gap-3 text-center">
              <Plug className="size-8 text-muted-foreground" />
              <div>
                <div className="text-sm font-medium">No interfaces found</div>
                <div className="mt-1 text-sm text-muted-foreground">
                  {agents.status === "error"
                    ? agents.error
                    : "Add a Slack or Telegram interface — no agent needed yet."}
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </section>
    </div>
  );
}

function InterfaceCard({
  iface,
  agent,
  onRemove,
}: {
  iface: InterfaceConfig;
  agent?: { id: string; name: string };
  onRemove: () => void;
}) {
  const isSlack = iface.type === "slack";
  const title = isSlack ? "SlackChat" : "TelegramChat";
  const fields: { label: string; value: string }[] = [];
  fields.push({ label: "Chat app id", value: iface.id });

  if (isSlack) {
    fields.push({ label: "Bot token", value: iface.token ? "Direct value" : iface.token_env });
    fields.push({
      label: "Signing secret",
      value: iface.signing_secret ? "Direct value" : iface.signing_secret_env,
    });
  } else {
    fields.push({ label: "Bot token", value: iface.token ? "Direct value" : iface.token_env });
    fields.push({
      label: "Webhook secret",
      value: iface.secret_token ? "Direct value" : iface.secret_token_env,
    });
    if (iface.base_url) {
      fields.push({ label: "Base URL", value: iface.base_url });
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <Plug className="size-4 text-muted-foreground" />
            <CardTitle className="text-sm">{title}</CardTitle>
          </div>
          <div className="flex items-center gap-1.5">
            {agent ? (
              <Badge variant="outline" className="text-xs">
                <Bot className="size-3" />
                {agent.name}
              </Badge>
            ) : null}
            <Badge variant="secondary" className="text-xs">
              {iface.type}
            </Badge>
            <Button
              variant="ghost"
              size="icon"
              className="size-6 text-destructive hover:text-destructive"
              onClick={onRemove}
              title={`Remove ${title}`}
            >
              <Trash2 className="size-3" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-1.5">
        {fields.map(({ label, value }) => (
          <div key={label} className="grid gap-0.5">
            <span className="text-xs text-muted-foreground">{label}</span>
            <span className="font-mono text-xs">{value}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
