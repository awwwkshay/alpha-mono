import { createFileRoute } from "@tanstack/react-router";
import { Plug } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

export const Route = createFileRoute("/agents/interfaces")({
  component: AgentsInterfacesRoute,
});

function AgentsInterfacesRoute() {
  return (
    <div className="grid gap-5">
      <section>
        <h1 className="text-2xl font-semibold tracking-normal">Interfaces</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Interfaces exposed by agents in this Clay app.
        </p>
      </section>

      <section>
        <Card>
          <CardContent className="flex min-h-40 flex-col items-center justify-center gap-3 text-center">
            <Plug className="size-8 text-muted-foreground" />
            <div>
              <div className="text-sm font-medium">No interfaces found</div>
              <div className="mt-1 text-sm text-muted-foreground">
                Interfaces defined in this project will appear here.
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
