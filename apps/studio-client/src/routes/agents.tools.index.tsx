import { createFileRoute, Link } from "@tanstack/react-router";
import { Bot, Plus, Wrench } from "lucide-react";
import { useCallback, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ToolCreateForm } from "@/components/forms/tool-create-form";
import {
  STUDIO_SYNC_EVENT,
  type AgentSummary,
  type StandaloneTool,
  type ToolSummary,
  getAgents,
  getStandaloneTools,
} from "@/lib/api";
import { useApi } from "@/hooks/use-api";

export const Route = createFileRoute("/agents/tools/")({
  component: AgentsToolsRoute,
});

type FlatTool = {
  tool: ToolSummary | StandaloneTool;
  toolId: string | null;
  agent?: { id: string; name: string };
};

function AgentsToolsRoute() {
  const loadAgents = useCallback(() => getAgents(), []);
  const loadStandalone = useCallback(() => getStandaloneTools(), []);
  const agents = useApi(loadAgents);
  const standaloneTools = useApi(loadStandalone);
  const [createOpen, setCreateOpen] = useState(false);

  function sync() {
    window.dispatchEvent(new Event(STUDIO_SYNC_EVENT));
  }

  const agentList: AgentSummary[] = agents.status === "ready" ? agents.data : [];
  const standalone: StandaloneTool[] =
    standaloneTools.status === "ready" ? standaloneTools.data : [];

  const allTools: FlatTool[] = [
    ...standalone.map((t) => ({ tool: t, toolId: t.tool_id })),
    ...agentList.flatMap((agent) =>
      (agent.tools ?? []).map((tool) => ({
        tool,
        toolId: tool.source_file
          ? (tool.source_file.replace(/\.py$/, "").split("/").pop() ?? null)
          : null,
        agent: { id: agent.id, name: agent.name },
      })),
    ),
  ];

  const isEmpty = allTools.length === 0;

  return (
    <div className="grid gap-5">
      <section className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Tools</h1>
          <p className="mt-1 text-sm text-muted-foreground">Tools configured in this Clay app.</p>
        </div>

        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="size-4" />
              Tool
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Create tool</DialogTitle>
              <DialogDescription>
                Define the schema and execute function. Optionally wire it to an agent now.
              </DialogDescription>
            </DialogHeader>
            <ToolCreateForm
              agents={agentList}
              onSuccess={() => {
                sync();
                setCreateOpen(false);
              }}
            />
          </DialogContent>
        </Dialog>
      </section>

      <section className="grid gap-4">
        {!isEmpty ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {allTools.map(({ tool, toolId, agent }) => (
              <ToolCard
                key={agent ? `${agent.id}-${tool.name}` : (toolId ?? tool.name)}
                tool={tool}
                toolId={toolId}
                agent={agent}
              />
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="flex min-h-40 flex-col items-center justify-center gap-3 text-center">
              <Wrench className="size-8 text-muted-foreground" />
              <div>
                <div className="text-sm font-medium">No tools found</div>
                <div className="mt-1 text-sm text-muted-foreground">
                  {agents.status === "error"
                    ? agents.error
                    : "Create a tool — no agent needed yet."}
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </section>
    </div>
  );
}

const TOOL_CARD_CLASS =
  "flex h-full min-h-40 flex-col cursor-pointer transition-colors hover:border-primary/50";
const TOOL_LINK_CLASS = "block h-full";

type JsonSchema = Record<string, unknown>;
type SchemaField = {
  name: string;
  type: string | null;
};

function ToolCard({
  tool,
  toolId,
  agent,
}: {
  tool: ToolSummary | StandaloneTool;
  toolId: string | null;
  agent?: { id: string; name: string };
}) {
  const isClickable = toolId !== null;
  const inputFields = getSchemaFields(tool.input_schema);
  const outputFields = getSchemaFields(tool.output_schema);

  const inner = (
    <Card className={isClickable ? TOOL_CARD_CLASS : "flex h-full min-h-40 flex-col"}>
      <CardHeader className="min-h-28 pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <Wrench className="size-4 shrink-0 text-muted-foreground" />
            <CardTitle className="text-sm">{tool.name}</CardTitle>
          </div>
          {agent ? (
            <Badge variant="outline" className="shrink-0 text-xs">
              <Bot className="size-3" />
              {agent.name}
            </Badge>
          ) : null}
        </div>
        {tool.description ? (
          <CardDescription className="text-xs">{tool.description}</CardDescription>
        ) : null}
      </CardHeader>
      <CardContent className="mt-auto grid gap-3 pt-0">
        {toolId && !agent ? (
          <Badge variant="outline" className="w-fit font-mono text-xs">
            {toolId}
          </Badge>
        ) : null}
        <SchemaSection label="Inputs" fields={inputFields} emptyLabel="No inputs" />
        <SchemaSection label="Outputs" fields={outputFields} emptyLabel="No outputs" />
      </CardContent>
    </Card>
  );

  if (isClickable) {
    return (
      <Link to="/agents/tools/$toolId" params={{ toolId }} className={TOOL_LINK_CLASS}>
        {inner}
      </Link>
    );
  }

  return inner;
}

function SchemaSection({
  label,
  fields,
  emptyLabel,
}: {
  label: string;
  fields: SchemaField[];
  emptyLabel: string;
}) {
  return (
    <div className="grid max-h-28 gap-1.5 overflow-hidden">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      {fields.length > 0 ? (
        fields.slice(0, 3).map((field) => (
          <div key={field.name} className="flex min-w-0 items-center gap-2">
            <code className="truncate font-mono text-xs">{field.name}</code>
            {field.type ? (
              <Badge variant="secondary" className="shrink-0 text-xs">
                {field.type}
              </Badge>
            ) : null}
          </div>
        ))
      ) : (
        <p className="text-xs text-muted-foreground">{emptyLabel}</p>
      )}
      {fields.length > 3 ? (
        <p className="text-xs text-muted-foreground">+{fields.length - 3} more</p>
      ) : null}
    </div>
  );
}

function getSchemaFields(schema: JsonSchema | null | undefined): SchemaField[] {
  const properties = schema?.properties;
  if (!isRecord(properties)) {
    return [];
  }

  return Object.entries(properties).map(([name, fieldSchema]) => ({
    name,
    type: getSchemaType(fieldSchema),
  }));
}

function getSchemaType(schema: unknown): string | null {
  if (!isRecord(schema)) {
    return null;
  }

  const type = schema.type;
  if (typeof type === "string") {
    return type;
  }
  if (Array.isArray(type)) {
    return type.filter((item): item is string => typeof item === "string").join(" | ");
  }

  const anyOf = schema.anyOf;
  if (Array.isArray(anyOf)) {
    const types = anyOf.map(getSchemaType).filter((item): item is string => Boolean(item));
    return types.length > 0 ? types.join(" | ") : null;
  }

  return null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
