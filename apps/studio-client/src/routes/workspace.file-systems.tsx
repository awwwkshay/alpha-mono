import { createFileRoute } from "@tanstack/react-router";
import { FolderTree } from "lucide-react";
import { useCallback } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { CopyConfigButton } from "@/components/copy-config-button";
import { getWorkspaces } from "@/lib/api";
import { useApi } from "@/hooks/use-api";

export const Route = createFileRoute("/workspace/file-systems")({
  component: WorkspaceFileSystemsRoute,
});

function WorkspaceFileSystemsRoute() {
  const loadWorkspaces = useCallback(() => getWorkspaces(), []);
  const workspaces = useApi(loadWorkspaces);

  return (
    <div className="grid gap-5">
      <section>
        <h1 className="text-2xl font-semibold tracking-normal">File Systems</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Storage backends attached to each workspace.
        </p>
      </section>

      <section className="grid gap-4">
        {workspaces.status === "ready" && workspaces.data.length > 0 ? (
          workspaces.data.map((workspace) => {
            const config = workspace.config["filesystem"] ?? {};

            return (
              <div key={workspace.id} className="grid gap-2 rounded-md border p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium">{workspace.id}</div>
                    <div className="text-xs text-muted-foreground">File system config</div>
                  </div>
                  <CopyConfigButton
                    config={{
                      workspaces: {
                        [workspace.id]: { filesystem: config },
                      },
                    }}
                  />
                </div>
                <pre className="max-h-72 overflow-auto rounded-md bg-muted/50 p-3 text-xs">
                  {JSON.stringify(config, null, 2)}
                </pre>
              </div>
            );
          })
        ) : (
          <Card>
            <CardContent className="flex min-h-40 flex-col items-center justify-center gap-3 text-center">
              <FolderTree className="size-8 text-muted-foreground" />
              <div>
                <div className="text-sm font-medium">No file systems configured</div>
                <div className="mt-1 text-sm text-muted-foreground">
                  {workspaces.status === "error"
                    ? workspaces.error
                    : "File system details will appear here when configured."}
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </section>
    </div>
  );
}
