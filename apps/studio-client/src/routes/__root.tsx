import { Link, Outlet, createRootRoute } from "@tanstack/react-router";
import {
  Bot,
  Boxes,
  Check,
  FlaskConical,
  FolderTree,
  Gauge,
  GitBranch,
  KeyRound,
  LayoutDashboard,
  ListChecks,
  Loader2,
  PanelLeft,
  Plug,
  RefreshCw,
  Search,
  SquareTerminal,
  Wrench,
} from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { STUDIO_SYNC_EVENT, syncProject } from "@/lib/api";

const navItems = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/environment", label: "Environment", icon: KeyRound },
  {
    to: "/agents",
    label: "Agents",
    icon: Bot,
    children: [
      { to: "/agents/tools", label: "Tools", icon: Wrench },
      { to: "/agents/chat-interfaces", label: "Chat Interfaces", icon: Plug },
    ],
  },
  {
    to: "/workflows",
    label: "Workflows",
    icon: GitBranch,
    children: [{ to: "/workflows/steps", label: "Steps", icon: ListChecks }],
  },
  {
    to: "/workspace",
    label: "Workspaces",
    icon: Boxes,
    children: [
      { to: "/workspace/file-systems", label: "File systems", icon: FolderTree },
      { to: "/workspace/sandboxes", label: "Sandboxes", icon: SquareTerminal },
    ],
  },
  {
    to: "/evals",
    label: "Evals",
    icon: FlaskConical,
    children: [{ to: "/evals/scorers", label: "Scorers", icon: Gauge }],
  },
] as const;

export const Route = createRootRoute({
  component: StudioLayout,
});

function StudioLayout() {
  const [syncState, setSyncState] = useState<"idle" | "syncing" | "synced" | "error">("idle");

  async function handleSync() {
    setSyncState("syncing");
    try {
      await syncProject();
      window.dispatchEvent(new Event(STUDIO_SYNC_EVENT));
      setSyncState("synced");
      window.setTimeout(() => setSyncState("idle"), 1800);
    } catch {
      setSyncState("error");
    }
  }

  return (
    <div className="min-h-svh bg-background">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r bg-card md:block">
        <div className="flex h-16 items-center gap-2 border-b px-5">
          <div className="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <GitBranch className="size-4" />
          </div>
          <div>
            <div className="text-sm font-semibold leading-none">Clay Studio</div>
            <div className="mt-1 text-xs text-muted-foreground">Local project</div>
          </div>
        </div>
        <nav className="grid gap-1 p-3">
          {navItems.map((item) => (
            <div key={item.to} className="grid gap-1">
              <Link
                to={item.to}
                activeOptions={{ exact: true }}
                className="flex h-9 items-center gap-2 rounded-md px-3 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground [&.active]:bg-secondary [&.active]:font-medium [&.active]:text-foreground"
              >
                <item.icon className="size-4" />
                {item.label}
              </Link>
              {"children" in item ? (
                <div className="grid gap-1 pl-6">
                  {item.children.map((child) => (
                    <Link
                      key={child.to}
                      to={child.to}
                      className="flex h-8 items-center gap-2 rounded-md px-3 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground [&.active]:bg-secondary [&.active]:font-medium [&.active]:text-foreground"
                    >
                      <child.icon className="size-3.5" />
                      {child.label}
                    </Link>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </nav>
      </aside>

      <div className="md:pl-64">
        <header className="sticky top-0 z-10 flex h-16 items-center gap-3 border-b bg-background/90 px-4 backdrop-blur md:px-6">
          <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open navigation">
            <PanelLeft className="size-4" />
          </Button>
          <div className="relative max-w-md flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="bg-card pl-9"
              placeholder="Search agents, workflows, files"
              type="search"
            />
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void handleSync()}
            disabled={syncState === "syncing"}
          >
            {syncState === "syncing" ? (
              <Loader2 className="size-4 animate-spin" />
            ) : syncState === "synced" ? (
              <Check className="size-4" />
            ) : (
              <RefreshCw className="size-4" />
            )}
            {syncState === "syncing" ? "Syncing" : syncState === "synced" ? "Synced" : "Sync"}
          </Button>
        </header>

        <main className="mx-auto w-full max-w-7xl px-4 py-5 md:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
