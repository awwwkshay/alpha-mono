import { createFileRoute } from "@tanstack/react-router";
import { Bot, GitBranch, GitFork, Play } from "lucide-react";
import { useCallback } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getAgents, getProject, getWorkflows } from "@/lib/api";
import { useApi } from "@/hooks/use-api";

export const Route = createFileRoute("/")({
  component: OverviewRoute,
});

function OverviewRoute() {
  const loadProject = useCallback(() => getProject(), []);
  const loadAgents = useCallback(() => getAgents(), []);
  const loadWorkflows = useCallback(() => getWorkflows(), []);
  const project = useApi(loadProject);
  const agents = useApi(loadAgents);
  const workflows = useApi(loadWorkflows);

  const agentCount = agents.status === "ready" ? agents.data.length : 0;
  const workflowCount = workflows.status === "ready" ? workflows.data.length : 0;

  return (
    <div className="grid gap-5">
      <section className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <Badge variant="outline">Studio</Badge>
            <Badge variant="secondary">
              {project.status === "ready" && project.data.has_clay_yaml ? "Synced" : "Local"}
            </Badge>
            <Badge variant="outline">
              <GitFork className="size-3" />
              {project.status === "ready" && project.data.git_branch
                ? project.data.git_branch
                : "No git branch"}
            </Badge>
          </div>
          <h1 className="text-2xl font-semibold tracking-normal">Overview</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            {project.status === "ready" ? project.data.root : "Loading current Clay project"}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <GitBranch className="size-4" />
            New workflow
          </Button>
          <Button>
            <Bot className="size-4" />
            New agent
          </Button>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <MetricCard
          icon={Bot}
          label="Agents"
          value={agentCount}
          detail={agents.status === "error" ? agents.error : "Configured agents"}
        />
        <MetricCard
          icon={GitBranch}
          label="Workflows"
          value={workflowCount}
          detail={workflows.status === "error" ? workflows.error : "Runnable workflow graphs"}
        />
        <MetricCard
          icon={GitFork}
          label="Git branch"
          value={project.status === "ready" && project.data.git_branch ? 1 : 0}
          detail={
            project.status === "ready" && project.data.git_branch
              ? project.data.git_branch
              : "No git repository detected"
          }
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle>Recent activity</CardTitle>
            <CardDescription>Project events from this local session</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3">
              {[
                "Loaded Clay project metadata",
                "Mounted Studio API routes",
                "Prepared workspace sync model",
              ].map((event) => (
                <div
                  key={event}
                  className="flex min-h-11 items-center justify-between rounded-md border px-3"
                >
                  <span className="text-sm">{event}</span>
                  <Badge variant="outline">ok</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Run panel</CardTitle>
            <CardDescription>Workflow execution surface</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <div className="rounded-md border bg-muted/40 p-3 text-sm text-muted-foreground">
              Select a workflow to run it against sample input.
            </div>
            <Button className="w-full">
              <Play className="size-4" />
              Run selected workflow
            </Button>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

type MetricCardProps = {
  icon: typeof Bot;
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
