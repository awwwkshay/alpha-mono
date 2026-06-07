import { createFileRoute } from "@tanstack/react-router";
import { useForm } from "@tanstack/react-form";
import { Bot, Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { useCallback, useState } from "react";

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
import {
  STUDIO_SYNC_EVENT,
  type AgentSummary,
  createAgent,
  deleteAgent,
  getAgents,
  getModels,
  updateAgent,
} from "@/lib/api";
import { useApi } from "@/hooks/use-api";
import { AgentCreateSchema, AgentUpdateSchema } from "@/schemas/agent";

export const Route = createFileRoute("/agents/")({
  component: AgentsRoute,
});

function AgentsRoute() {
  const loadAgents = useCallback(() => getAgents(), []);
  const loadModels = useCallback(() => getModels(), []);
  const agents = useApi(loadAgents);
  const models = useApi(loadModels);

  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editAgent, setEditAgent] = useState<AgentSummary | null>(null);

  const modelList = models.status === "ready" ? models.data.map((m) => m.id) : [];

  function sync() {
    window.dispatchEvent(new Event(STUDIO_SYNC_EVENT));
  }

  async function handleDelete(agentId: string) {
    try {
      await deleteAgent(agentId);
      sync();
    } catch {
      // silently ignore
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

        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
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
                Writes a Python agent module into the current app.
              </DialogDescription>
            </DialogHeader>
            <CreateAgentForm
              modelList={modelList}
              onSuccess={() => {
                sync();
                setCreateDialogOpen(false);
              }}
            />
          </DialogContent>
        </Dialog>
      </section>

      {/* Edit dialog */}
      <Dialog
        open={editAgent !== null}
        onOpenChange={(open) => {
          if (!open) setEditAgent(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit agent</DialogTitle>
            <DialogDescription>
              Updates the agent Python module and project metadata.
            </DialogDescription>
          </DialogHeader>
          {editAgent ? (
            <EditAgentForm
              agent={editAgent}
              modelList={modelList}
              onSuccess={() => {
                sync();
                setEditAgent(null);
              }}
            />
          ) : null}
        </DialogContent>
      </Dialog>

      {/* Agent cards */}
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
                  <div className="flex flex-wrap items-center justify-end gap-1.5">
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
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-7"
                      onClick={() => setEditAgent(agent)}
                      title="Edit agent"
                    >
                      <Pencil className="size-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-7 text-destructive hover:text-destructive"
                      onClick={() => void handleDelete(agent.id)}
                      title="Delete agent"
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
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

// ── Create agent form ──────────────────────────────────────────────────────────

function CreateAgentForm({ modelList, onSuccess }: { modelList: string[]; onSuccess: () => void }) {
  const [modelValue, setModelValue] = useState("gemini/gemini-2.0-flash");

  const form = useForm({
    defaultValues: {
      id: "",
      name: "",
      model: "gemini/gemini-2.0-flash",
      system_prompt: "",
    } as { id: string; name: string; model: string; system_prompt: string; description?: string },
    validators: { onSubmit: AgentCreateSchema },
    onSubmit: async ({ value }) => {
      await createAgent({
        id: value.id,
        name: value.name,
        model: value.model || modelValue,
        system_prompt: value.system_prompt,
        ...(value.description ? { description: value.description } : {}),
      });
      onSuccess();
    },
  });

  return (
    <form
      className="grid gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        void form.handleSubmit();
      }}
    >
      <div className="grid gap-3 md:grid-cols-2">
        <form.Field name="id">
          {(field) => (
            <FieldGroup label="Agent id" errors={field.state.meta.errors}>
              <Input
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
                placeholder="sales_assistant"
              />
            </FieldGroup>
          )}
        </form.Field>

        <form.Field name="name">
          {(field) => (
            <FieldGroup label="Name" errors={field.state.meta.errors}>
              <Input
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
                placeholder="Sales Assistant"
              />
            </FieldGroup>
          )}
        </form.Field>

        <form.Field name="model">
          {(field) => (
            <FieldGroup label="Model" errors={field.state.meta.errors}>
              <ModelCombobox
                name="model"
                value={modelValue}
                onChange={(v) => {
                  setModelValue(v);
                  field.handleChange(v);
                }}
                models={modelList}
              />
            </FieldGroup>
          )}
        </form.Field>

        <form.Field name="description">
          {(field) => (
            <FieldGroup label="Description" errors={field.state.meta.errors}>
              <Input
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
                placeholder="Qualifies and researches leads"
              />
            </FieldGroup>
          )}
        </form.Field>

        <div className="md:col-span-2">
          <form.Field name="system_prompt">
            {(field) => (
              <FieldGroup label="System prompt" errors={field.state.meta.errors}>
                <Textarea
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="You are a sales assistant..."
                />
              </FieldGroup>
            )}
          </form.Field>
        </div>
      </div>

      <form.Subscribe selector={(s) => ({ isSubmitting: s.isSubmitting, errorMap: s.errorMap })}>
        {({ isSubmitting, errorMap }) => (
          <>
            {errorMap.onSubmit ? (
              <p className="text-sm text-destructive">{JSON.stringify(errorMap.onSubmit)}</p>
            ) : null}
            <DialogFooter>
              <Button disabled={isSubmitting} type="submit">
                {isSubmitting ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Plus className="size-4" />
                )}
                {isSubmitting ? "Creating" : "Create agent"}
              </Button>
            </DialogFooter>
          </>
        )}
      </form.Subscribe>
    </form>
  );
}

// ── Edit agent form ────────────────────────────────────────────────────────────

function EditAgentForm({
  agent,
  modelList,
  onSuccess,
}: {
  agent: AgentSummary;
  modelList: string[];
  onSuccess: () => void;
}) {
  const [modelValue, setModelValue] = useState(agent.model ?? "gemini/gemini-2.0-flash");

  const form = useForm({
    defaultValues: {
      name: agent.name,
      model: agent.model ?? "gemini/gemini-2.0-flash",
      system_prompt: agent.system_prompt ?? "",
      ...(agent.description ? { description: agent.description } : {}),
    } as { name: string; model: string; system_prompt: string; description?: string },
    validators: { onSubmit: AgentUpdateSchema },
    onSubmit: async ({ value }) => {
      await updateAgent(agent.id, {
        name: value.name,
        model: value.model || modelValue,
        system_prompt: value.system_prompt,
        ...(value.description ? { description: value.description } : {}),
      });
      onSuccess();
    },
  });

  return (
    <form
      className="grid gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        void form.handleSubmit();
      }}
    >
      <div className="grid gap-3 md:grid-cols-2">
        <form.Field name="name">
          {(field) => (
            <FieldGroup label="Name" errors={field.state.meta.errors}>
              <Input
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
              />
            </FieldGroup>
          )}
        </form.Field>

        <form.Field name="model">
          {(field) => (
            <FieldGroup label="Model" errors={field.state.meta.errors}>
              <ModelCombobox
                name="model"
                value={modelValue}
                onChange={(v) => {
                  setModelValue(v);
                  field.handleChange(v);
                }}
                models={modelList}
              />
            </FieldGroup>
          )}
        </form.Field>

        <div className="md:col-span-2">
          <form.Field name="description">
            {(field) => (
              <FieldGroup label="Description" errors={field.state.meta.errors}>
                <Input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                />
              </FieldGroup>
            )}
          </form.Field>
        </div>

        <div className="md:col-span-2">
          <form.Field name="system_prompt">
            {(field) => (
              <FieldGroup label="System prompt" errors={field.state.meta.errors}>
                <Textarea
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  rows={6}
                />
              </FieldGroup>
            )}
          </form.Field>
        </div>
      </div>

      <form.Subscribe selector={(s) => ({ isSubmitting: s.isSubmitting, errorMap: s.errorMap })}>
        {({ isSubmitting, errorMap }) => (
          <>
            {errorMap.onSubmit ? (
              <p className="text-sm text-destructive">{JSON.stringify(errorMap.onSubmit)}</p>
            ) : null}
            <DialogFooter>
              <Button disabled={isSubmitting} type="submit">
                {isSubmitting ? <Loader2 className="size-4 animate-spin" /> : null}
                {isSubmitting ? "Saving" : "Save changes"}
              </Button>
            </DialogFooter>
          </>
        )}
      </form.Subscribe>
    </form>
  );
}

// ── Shared helpers ─────────────────────────────────────────────────────────────

function FieldGroup({
  label,
  errors,
  children,
}: {
  label: string;
  errors: unknown[];
  children: React.ReactNode;
}) {
  const firstError = errors[0];
  const errorMessage =
    firstError != null
      ? typeof firstError === "string"
        ? firstError
        : typeof firstError === "object" && "message" in (firstError as object)
          ? String((firstError as { message: unknown }).message)
          : JSON.stringify(firstError)
      : null;

  return (
    <div className="grid gap-1.5">
      <Label>{label}</Label>
      {children}
      {errorMessage ? <p className="text-xs text-destructive">{errorMessage}</p> : null}
    </div>
  );
}
