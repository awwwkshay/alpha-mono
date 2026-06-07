import { createFileRoute } from "@tanstack/react-router";
import { Bot, FlaskConical, Gauge, GitBranch } from "lucide-react";
import { useCallback } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getAgents, getWorkflows } from "@/lib/api";
import { useApi } from "@/hooks/use-api";

export const Route = createFileRoute("/evals/")({
  component: EvalsRoute,
});

function EvalsRoute() {
  const loadAgents = useCallback(() => getAgents(), []);
  const loadWorkflows = useCallback(() => getWorkflows(), []);
  const agents = useApi(loadAgents);
  const workflows = useApi(loadWorkflows);

  const scorerCount =
    agents.status === "ready" && workflows.status === "ready"
      ? [...agents.data, ...workflows.data].reduce(
          (count, source) => count + Object.keys(source.scorers ?? {}).length,
          0,
        )
      : 0;

  return (
    <div className="grid gap-5">
      <section>
        <h1 className="text-2xl font-semibold tracking-normal">Evals</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Evaluation hooks and scorers configured across this Clay app.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <MetricCard icon={Gauge} label="Scorers" value={scorerCount} detail="Configured checks" />
        <MetricCard
          icon={Bot}
          label="Agent sources"
          value={agents.status === "ready" ? agents.data.length : 0}
          detail={agents.status === "error" ? agents.error : "Agents with eval metadata"}
        />
        <MetricCard
          icon={GitBranch}
          label="Workflow sources"
          value={workflows.status === "ready" ? workflows.data.length : 0}
          detail={workflows.status === "error" ? workflows.error : "Workflows with eval metadata"}
        />
      </section>

      {agents.status === "error" || workflows.status === "error" ? (
        <Card>
          <CardContent className="flex min-h-24 items-center justify-center">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <FlaskConical className="size-4" />
              Could not load eval sources.
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

type MetricCardProps = {
  icon: typeof Gauge;
  label: string;
  value: number;
  detail: string;
};

function MetricCard({ icon: Icon, label, value, detail }: MetricCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle>{label}</CardTitle>
        <Icon className="size-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold">{value}</div>
        <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
      </CardContent>
    </Card>
  );
}
