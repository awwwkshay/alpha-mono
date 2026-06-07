import { createFileRoute } from "@tanstack/react-router";
import { Boxes, FolderTree } from "lucide-react";
import { useCallback } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getProject, getWorkspaces } from "@/lib/api";
import { useApi } from "@/hooks/use-api";

export const Route = createFileRoute("/workspace/")({
  component: WorkspaceRoute,
});

function WorkspaceRoute() {
  const loadProject = useCallback(() => getProject(), []);
  const loadWorkspaces = useCallback(() => getWorkspaces(), []);
  const project = useApi(loadProject);
  const workspaces = useApi(loadWorkspaces);

  return (
    <div className="grid gap-5">
      <section>
        <h1 className="text-2xl font-semibold tracking-normal">Workspace</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Filesystem and sandbox state connected to this project.
        </p>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Project</CardTitle>
            <CardDescription>
              {project.status === "ready" ? project.data.root : "Loading"}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <InfoRow
              label="App reference"
              value={project.status === "ready" ? (project.data.app_ref ?? "None") : ""}
            />
            <InfoRow
              label="Studio model"
              value={
                project.status === "ready" && project.data.has_clay_yaml
                  ? "clay.yaml"
                  : "Not created"
              }
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Workspaces</CardTitle>
            <CardDescription>Runtime workspace definitions</CardDescription>
          </CardHeader>
          <CardContent className="flex min-h-24 flex-col items-center justify-center gap-2 text-center">
            {workspaces.status === "ready" ? (
              <>
                <div className="text-2xl font-semibold">{workspaces.data.length}</div>
                <p className="text-sm text-muted-foreground">
                  {workspaces.data.length === 1 ? "workspace" : "workspaces"} configured
                </p>
              </>
            ) : workspaces.status === "error" ? (
              <p className="text-sm text-destructive">{workspaces.error}</p>
            ) : (
              <Boxes className="size-6 text-muted-foreground" />
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex min-h-11 items-center justify-between gap-3 rounded-md border px-3">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <FolderTree className="size-4" />
        {label}
      </div>
      <div className="max-w-[55%] truncate text-right text-sm font-medium">{value}</div>
    </div>
  );
}
