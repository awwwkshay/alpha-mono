import { createFileRoute } from "@tanstack/react-router";
import { Bot, Loader2, Plus } from "lucide-react";
import { type FormEvent, useCallback, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { CopyConfigButton } from "@/components/copy-config-button";
import { ModelCombobox } from "@/components/model-combobox";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { STUDIO_SYNC_EVENT, createAgent, getAgents, getModels } from "@/lib/api";
import { useApi } from "@/hooks/use-api";

export const Route = createFileRoute("/agents/")({
  component: AgentsRoute,
});

function AgentsRoute() {
  const loadAgents = useCallback(() => getAgents(), []);
  const loadModels = useCallback(() => getModels(), []);
  const agents = useApi(loadAgents);
  const models = useApi(loadModels);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [modelValue, setModelValue] = useState("gemini/gemini-2.0-flash");

  async function handleCreateAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsCreating(true);

    const data = new FormData(event.currentTarget);
    const id = formString(data, "id");
    const name = formString(data, "name");
    const model = formString(data, "model") || modelValue;
    const systemPrompt = formString(data, "system_prompt");
    const description = formString(data, "description");

    try {
      await createAgent({
        id,
        name,
        model,
        system_prompt: systemPrompt,
        ...(description ? { description } : {}),
      });
      event.currentTarget.reset();
      setModelValue("gemini/gemini-2.0-flash");
      window.dispatchEvent(new Event(STUDIO_SYNC_EVENT));
      setDialogOpen(false);
    } catch (createError: unknown) {
      const message = createError instanceof Error ? createError.message : "Could not create agent";
      setError(message);
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <div className="grid gap-5">
      <section className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Agents</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Model-backed workers available to this Clay app.
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="size-4" />
              Agent
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create agent</DialogTitle>
              <DialogDescription>
                Writes a Python agent module into the current app and updates project metadata.
              </DialogDescription>
            </DialogHeader>
            <form className="grid gap-4" onSubmit={(event) => void handleCreateAgent(event)}>
              <div className="grid gap-3 md:grid-cols-2">
                <div className="grid min-w-0 gap-2">
                  <Label htmlFor="agent-id">Agent id</Label>
                  <Input id="agent-id" name="id" required placeholder="sales_assistant" />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="agent-name">Name</Label>
                  <Input id="agent-name" name="name" required placeholder="Sales Assistant" />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="agent-model">Model</Label>
                  <ModelCombobox
                    name="model"
                    value={modelValue}
                    onChange={setModelValue}
                    models={models.status === "ready" ? models.data.map((model) => model.id) : []}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="agent-description">Description</Label>
                  <Input
                    id="agent-description"
                    name="description"
                    placeholder="Qualifies and researches leads"
                  />
                </div>
                <div className="grid gap-2 md:col-span-2">
                  <Label htmlFor="agent-system-prompt">System prompt</Label>
                  <Textarea
                    id="agent-system-prompt"
                    name="system_prompt"
                    required
                    placeholder="You are a sales assistant..."
                  />
                </div>
              </div>
              {error ? <p className="text-sm text-destructive">{error}</p> : null}
              <DialogFooter>
                <Button disabled={isCreating} type="submit">
                  {isCreating ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Plus className="size-4" />
                  )}
                  {isCreating ? "Creating" : "Create agent"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {agents.status === "ready" && agents.data.length > 0 ? (
          agents.data.map((agent) => (
            <Card key={agent.id}>
              <CardHeader>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <CardTitle>{agent.name}</CardTitle>
                    <CardDescription>{agent.id}</CardDescription>
                  </div>
                  <div className="flex flex-wrap justify-end gap-2">
                    <Badge variant="outline">{agent.model ?? "model"}</Badge>
                    <CopyConfigButton
                      config={{
                        agents: {
                          [agent.id]: {
                            name: agent.name,
                            model: agent.model ?? "",
                            description: agent.description,
                            system_prompt: agent.system_prompt ?? "",
                            scorers: agent.scorers ?? {},
                          },
                        },
                      }}
                    />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="line-clamp-4 text-sm text-muted-foreground">
                  {agent.description ?? agent.system_prompt ?? "No prompt configured"}
                </p>
              </CardContent>
            </Card>
          ))
        ) : (
          <Card className="md:col-span-2 xl:col-span-3">
            <CardContent className="flex min-h-40 flex-col items-center justify-center gap-3 text-center">
              <Bot className="size-8 text-muted-foreground" />
              <div>
                <div className="text-sm font-medium">No agents found</div>
                <div className="mt-1 text-sm text-muted-foreground">
                  {agents.status === "error"
                    ? agents.error
                    : "Create an agent to populate this project."}
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </section>
    </div>
  );
}

function formString(data: FormData, key: string) {
  const value = data.get(key);
  return typeof value === "string" ? value.trim() : "";
}
