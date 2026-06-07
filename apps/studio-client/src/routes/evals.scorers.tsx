import { createFileRoute } from "@tanstack/react-router";
import { Bot, Gauge, GitBranch } from "lucide-react";
import { useCallback } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getAgents, getWorkflows } from "@/lib/api";
import { useApi } from "@/hooks/use-api";

export const Route = createFileRoute("/evals/scorers")({
  component: EvalScorersRoute,
});

type ScorerItem = {
  name: string;
  config: unknown;
  sourceName: string;
  sourceId: string;
  sourceKind: "Agent" | "Workflow";
  SourceIcon: typeof Bot;
};

function EvalScorersRoute() {
  const loadAgents = useCallback(() => getAgents(), []);
  const loadWorkflows = useCallback(() => getWorkflows(), []);
  const agents = useApi(loadAgents);
  const workflows = useApi(loadWorkflows);

  const scorers: ScorerItem[] =
    agents.status === "ready" && workflows.status === "ready"
      ? [
          ...agents.data.flatMap((agent) =>
            Object.entries(agent.scorers ?? {}).map(([name, config]) => ({
              name,
              config,
              sourceName: agent.name,
              sourceId: agent.id,
              sourceKind: "Agent" as const,
              SourceIcon: Bot,
            })),
          ),
          ...workflows.data.flatMap((workflow) =>
            Object.entries(workflow.scorers ?? {}).map(([name, config]) => ({
              name,
              config,
              sourceName: workflow.name,
              sourceId: workflow.id,
              sourceKind: "Workflow" as const,
              SourceIcon: GitBranch,
            })),
          ),
        ]
      : [];

  const hasError = agents.status === "error" || workflows.status === "error";

  return (
    <div className="grid gap-5">
      <section>
        <h1 className="text-2xl font-semibold tracking-normal">Scorers</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Scorers configured across this Clay app.
        </p>
      </section>

      <section className="grid gap-4">
        {scorers.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {scorers.map((scorer) => (
              <ScorerCard
                key={`${scorer.sourceKind}-${scorer.sourceId}-${scorer.name}`}
                scorer={scorer}
              />
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="flex min-h-40 flex-col items-center justify-center gap-3 text-center">
              <Gauge className="size-8 text-muted-foreground" />
              <div>
                <div className="text-sm font-medium">No scorers found</div>
                <div className="mt-1 text-sm text-muted-foreground">
                  {hasError
                    ? "Could not load agents or workflows."
                    : "Scorers will appear here when configured."}
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </section>
    </div>
  );
}

function ScorerCard({ scorer }: { scorer: ScorerItem }) {
  const { SourceIcon } = scorer;
  const configEntries =
    scorer.config != null && typeof scorer.config === "object" && !Array.isArray(scorer.config)
      ? Object.entries(scorer.config as Record<string, unknown>)
      : [];

  return (
    <Card className="flex h-full min-h-40 flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="text-sm">{scorer.name}</CardTitle>
            <CardDescription className="mt-0.5 truncate">{scorer.sourceName}</CardDescription>
          </div>
          <Badge variant="outline" className="shrink-0">
            <SourceIcon className="size-3" />
            {scorer.sourceKind}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="mt-auto pt-0">
        {configEntries.length > 0 ? (
          <div className="grid gap-1.5">
            {configEntries.slice(0, 4).map(([key, val]) => (
              <div key={key} className="flex min-w-0 items-center gap-2">
                <code className="truncate font-mono text-xs">{key}</code>
                <Badge variant="secondary" className="shrink-0 text-xs">
                  {typeof val}
                </Badge>
              </div>
            ))}
            {configEntries.length > 4 ? (
              <p className="text-xs text-muted-foreground">+{configEntries.length - 4} more</p>
            ) : null}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">No config</p>
        )}
      </CardContent>
    </Card>
  );
}
