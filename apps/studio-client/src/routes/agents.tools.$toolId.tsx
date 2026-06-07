import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, Circle, Loader2, Save } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CodeEditor } from "@/components/code-editor";
import { STUDIO_SYNC_EVENT, getToolById, saveToolById } from "@/lib/api";
import { useApi } from "@/hooks/use-api";

export const Route = createFileRoute("/agents/tools/$toolId")({
  component: ToolDetailRoute,
});

function ToolDetailRoute() {
  const { toolId } = Route.useParams();
  const loadSource = useCallback(() => getToolById(toolId), [toolId]);
  const source = useApi(loadSource);

  const [content, setContent] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const isDirty = content !== null;

  const editorValue = content ?? (source.status === "ready" ? source.data.content : null) ?? "";

  // Parse schema info from source for the side panel
  const schemaInfo = source.status === "ready" ? parseSchema(source.data.content) : null;

  async function handleSave() {
    setSaving(true);
    setSaveError(null);
    try {
      await saveToolById(toolId, editorValue);
      window.dispatchEvent(new Event(STUDIO_SYNC_EVENT));
      setSavedAt(new Date());
      setContent(null);
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : "Could not save");
    } finally {
      setSaving(false);
    }
  }

  // Cmd+S / Ctrl+S to save
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        if (isDirty && !saving) void handleSave();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  });

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col gap-0 overflow-hidden">
      {/* Toolbar */}
      <header className="flex shrink-0 items-center gap-3 border-b bg-background px-1 py-2">
        <Link to="/agents/tools">
          <Button variant="ghost" size="icon" className="size-8">
            <ArrowLeft className="size-4" />
          </Button>
        </Link>

        <div className="flex min-w-0 flex-1 items-center gap-2">
          <span className="font-mono text-sm font-semibold">{toolId}.py</span>
          {isDirty ? (
            <Circle className="size-2 fill-amber-400 text-amber-400" aria-label="Unsaved changes" />
          ) : null}
        </div>

        {source.status === "ready" ? (
          <span className="hidden truncate font-mono text-xs text-muted-foreground md:block">
            {source.data.source_file}
          </span>
        ) : null}

        <div className="flex shrink-0 items-center gap-2">
          {savedAt && !isDirty ? (
            <span className="text-xs text-muted-foreground">
              Saved {savedAt.toLocaleTimeString()}
            </span>
          ) : null}
          {saveError ? <p className="text-sm text-destructive">{saveError}</p> : null}
          <Button size="sm" onClick={() => void handleSave()} disabled={saving || !isDirty}>
            {saving ? <Loader2 className="size-3.5 animate-spin" /> : <Save className="size-3.5" />}
            {saving ? "Saving" : "Save"}
          </Button>
        </div>
      </header>

      {/* Main layout: schema panel + editor */}
      <div className="flex min-h-0 flex-1">
        {/* Schema sidebar */}
        <aside className="hidden w-64 shrink-0 overflow-y-auto border-r bg-card p-4 md:block">
          {schemaInfo ? (
            <div className="grid gap-4">
              {schemaInfo.inputFields.length > 0 ? (
                <SchemaSection title="Input" fields={schemaInfo.inputFields} />
              ) : (
                <SchemaSection title="Input" empty="No input fields" />
              )}
              {schemaInfo.outputFields.length > 0 ? (
                <SchemaSection title="Output" fields={schemaInfo.outputFields} />
              ) : (
                <SchemaSection title="Output" empty="No output fields" />
              )}
              {schemaInfo.toolName ? (
                <div className="grid gap-1">
                  <p className="text-xs font-medium text-muted-foreground">Tool name</p>
                  <p className="font-mono text-xs">{schemaInfo.toolName}</p>
                </div>
              ) : null}
            </div>
          ) : source.status === "loading" ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="size-4 animate-spin text-muted-foreground" />
            </div>
          ) : null}
        </aside>

        {/* Editor */}
        <div className="flex-1 overflow-auto">
          {source.status === "loading" ? (
            <div className="flex h-full items-center justify-center">
              <Loader2 className="size-6 animate-spin text-muted-foreground" />
            </div>
          ) : source.status === "error" ? (
            <div className="flex h-full items-center justify-center">
              <p className="text-sm text-destructive">Could not load source: {source.error}</p>
            </div>
          ) : (
            <CodeEditor
              value={editorValue}
              onChange={(v) => setContent(v)}
              height="100%"
              fullFeatures
              sourceFile={source.data.source_file}
              className="rounded-none border-none"
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ── Schema panel ───────────────────────────────────────────────────────────────

function SchemaSection({
  title,
  fields,
  empty,
}: {
  title: string;
  fields?: { name: string; type: string; required: boolean }[];
  empty?: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-2 pt-3">
        <CardTitle className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="pb-3">
        {fields && fields.length > 0 ? (
          <div className="grid gap-1.5">
            {fields.map((f) => (
              <div key={f.name} className="flex items-center gap-1.5">
                <code className="font-mono text-xs">{f.name}</code>
                <Badge variant="secondary" className="text-xs">
                  {f.type}
                </Badge>
                {!f.required ? (
                  <Badge variant="outline" className="text-xs">
                    opt
                  </Badge>
                ) : null}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">{empty ?? "No fields"}</p>
        )}
      </CardContent>
    </Card>
  );
}

// ── Schema extraction from source ─────────────────────────────────────────────

type ParsedSchema = {
  inputFields: { name: string; type: string; required: boolean }[];
  outputFields: { name: string; type: string; required: boolean }[];
  toolName: string | null;
};

function parseSchema(source: string): ParsedSchema {
  const inputFields = extractClassFields(
    source,
    /class \w+Input\(BaseModel\):([\s\S]*?)(?:\n\n|\nclass |Z)/,
  );
  const outputFields = extractClassFields(
    source,
    /class \w+Output\(BaseModel\):([\s\S]*?)(?:\n\n|\nclass |Z)/,
  );
  const toolNameMatch = /name=["']([^"']+)["']/.exec(source);
  return {
    inputFields,
    outputFields,
    toolName: toolNameMatch ? toolNameMatch[1] : null,
  };
}

function extractClassFields(
  source: string,
  classPattern: RegExp,
): { name: string; type: string; required: boolean }[] {
  const classMatch = classPattern.exec(source);
  if (!classMatch) return [];

  const body = classMatch[1];
  const fieldPattern = /^\s{4}(\w+):\s*([^\n=#]+?)(\s*=\s*\S+)?\s*(?:#.*)?$/gm;
  const fields: { name: string; type: string; required: boolean }[] = [];

  let m: RegExpExecArray | null;
  while ((m = fieldPattern.exec(body)) !== null) {
    const [, name, rawType, defaultVal] = m;
    if (name === "pass" || name === "model_config") continue;
    const type = rawType.trim().replace(/\s*\|?\s*None$/, "");
    const required = !defaultVal && !rawType.includes("None");
    fields.push({ name, type, required });
  }

  return fields;
}
