import { createFileRoute } from "@tanstack/react-router";
import { Bot, FlaskConical, GitBranch } from "lucide-react";
import { useCallback } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getAgents, getWorkflows } from "@/lib/api";
import { useApi } from "@/hooks/use-api";

export const Route = createFileRoute("/evals/scorers")({
  component: EvalScorersRoute,
});

function EvalScorersRoute() {
  const loadAgents = useCallback(() => getAgents(), []);
  const loadWorkflows = useCallback(() => getWorkflows(), []);
  const agents = useApi(loadAgents);
  const workflows = useApi(loadWorkflows);

  const scorerSources =
    agents.status === "ready" && workflows.status === "ready"
      ? [
          ...agents.data.map((agent) => ({
            id: agent.id,
            label: agent.name,
            kind: "Agent",
            icon: Bot,
            scorers: agent.scorers ?? {},
          })),
          ...workflows.data.map((workflow) => ({
            id: workflow.id,
            label: workflow.name,
            kind: "Workflow",
            icon: GitBranch,
            scorers: workflow.scorers ?? {},
          })),
        ]
      : [];

  const hasError = agents.status === "error" || workflows.status === "error";

  return (
    <div className="grid gap-5">
      <section>
        <h1 className="text-2xl font-semibold tracking-normal">Scorers</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Scorer configuration grouped by the agent or workflow that owns it.
        </p>
      </section>

      <section className="grid gap-4">
        {scorerSources.length > 0 ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {scorerSources.map((source) => {
              const scorerEntries = Object.entries(source.scorers);
              const SourceIcon = source.icon;

              return (
                <Card key={`${source.kind}-${source.id}`}>
                  <CardHeader>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <CardTitle>{source.label}</CardTitle>
                        <CardDescription>{source.id}</CardDescription>
                      </div>
                      <Badge variant="outline">
                        <SourceIcon className="size-3" />
                        {source.kind}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {scorerEntries.length > 0 ? (
                      <div className="grid gap-2">
                        {scorerEntries.map(([name]) => (
                          <div
                            key={name}
                            className="flex min-h-10 items-center justify-between rounded-md border px-3"
                          >
                            <span className="truncate text-sm">{name}</span>
                            <Badge variant="secondary">scorer</Badge>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="rounded-md border bg-muted/40 p-3 text-sm text-muted-foreground">
                        No scorers configured.
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        ) : (
          <Card>
            <CardContent className="flex min-h-40 flex-col items-center justify-center gap-3 text-center">
              <FlaskConical className="size-8 text-muted-foreground" />
              <div>
                <div className="text-sm font-medium">No eval sources found</div>
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
