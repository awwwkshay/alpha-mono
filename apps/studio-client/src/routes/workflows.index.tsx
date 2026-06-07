import { createFileRoute } from "@tanstack/react-router";
import { GitBranch, Plus } from "lucide-react";
import { useCallback } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CopyConfigButton } from "@/components/copy-config-button";
import { getWorkflows } from "@/lib/api";
import { useApi } from "@/hooks/use-api";

export const Route = createFileRoute("/workflows/")({
  component: WorkflowsRoute,
});

function WorkflowsRoute() {
  const loadWorkflows = useCallback(() => getWorkflows(), []);
  const workflows = useApi(loadWorkflows);

  return (
    <div className="grid gap-5">
      <section className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Workflows</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Typed execution graphs wired into the local Clay app.
          </p>
        </div>
        <Button>
          <Plus className="size-4" />
          Workflow
        </Button>
      </section>

      <section className="grid gap-4">
        {workflows.status === "ready" && workflows.data.length > 0 ? (
          workflows.data.map((workflow) => (
            <Card key={workflow.id}>
              <CardHeader>
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <CardTitle>{workflow.name}</CardTitle>
                    <CardDescription>{workflow.description ?? workflow.id}</CardDescription>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="outline">{workflow.input_schema ?? "Input"}</Badge>
                    <Badge variant="outline">{workflow.output_schema ?? "Output"}</Badge>
                    <CopyConfigButton
                      config={{
                        workflows: {
                          [workflow.id]: {
                            name: workflow.name,
                            description: workflow.description,
                            input_schema: workflow.input_schema,
                            output_schema: workflow.output_schema,
                            steps: workflow.step_count ?? 0,
                            scorers: workflow.scorers ?? {},
                          },
                        },
                      }}
                    />
                  </div>
                </div>
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
              <GitBranch className="size-8 text-muted-foreground" />
              <div>
                <div className="text-sm font-medium">No workflows found</div>
                <div className="mt-1 text-sm text-muted-foreground">
                  {workflows.status === "error"
                    ? workflows.error
                    : "Create a workflow to start composing steps."}
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </section>
    </div>
  );
}
