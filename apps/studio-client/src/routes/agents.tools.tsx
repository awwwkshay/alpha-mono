import { createFileRoute } from "@tanstack/react-router";
import { Wrench } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

export const Route = createFileRoute("/agents/tools")({
  component: AgentsToolsRoute,
});

function AgentsToolsRoute() {
  return (
    <div className="grid gap-5">
      <section>
        <h1 className="text-2xl font-semibold tracking-normal">Tools</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Tools available to agents in this Clay app.
        </p>
      </section>

      <section>
        <Card>
          <CardContent className="flex min-h-40 flex-col items-center justify-center gap-3 text-center">
            <Wrench className="size-8 text-muted-foreground" />
            <div>
              <div className="text-sm font-medium">No tools found</div>
              <div className="mt-1 text-sm text-muted-foreground">
                Tools defined in this project will appear here.
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
