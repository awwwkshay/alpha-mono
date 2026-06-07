import { createFileRoute } from "@tanstack/react-router";
import { ListChecks } from "lucide-react";
import { useCallback } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getWorkflows } from "@/lib/api";
import { useApi } from "@/hooks/use-api";

export const Route = createFileRoute("/workflows/steps")({
  component: WorkflowStepsRoute,
});

function WorkflowStepsRoute() {
  const loadWorkflows = useCallback(() => getWorkflows(), []);
  const workflows = useApi(loadWorkflows);

  const hasWorkflows = workflows.status === "ready" && workflows.data.length > 0;

  return (
    <div className="grid gap-5">
      <section>
        <h1 className="text-2xl font-semibold tracking-normal">Steps</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Step definitions across all workflows in this Clay app.
        </p>
      </section>

      <section className="grid gap-4">
        {hasWorkflows ? (
          workflows.data.map((workflow) => (
            <Card key={workflow.id}>
              <CardHeader>
                <CardTitle>{workflow.name}</CardTitle>
                <CardDescription>{workflow.id}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex min-h-12 items-center justify-between rounded-md border px-3">
                  <span className="text-sm text-muted-foreground">Steps</span>
                  <span className="text-sm font-medium">{workflow.step_count ?? 0}</span>
                </div>
              </CardContent>
            </Card>
          ))
        ) : (
          <Card>
            <CardContent className="flex min-h-40 flex-col items-center justify-center gap-3 text-center">
              <ListChecks className="size-8 text-muted-foreground" />
              <div>
                <div className="text-sm font-medium">No steps found</div>
                <div className="mt-1 text-sm text-muted-foreground">
                  {workflows.status === "error"
                    ? workflows.error
                    : "Workflow steps will appear here once workflows are created."}
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </section>
    </div>
  );
}
