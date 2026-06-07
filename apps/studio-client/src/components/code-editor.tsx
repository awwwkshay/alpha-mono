import Editor, { type OnMount } from "@monaco-editor/react";
import type { editor, Position } from "monaco-editor";
import { AlertCircle, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

// ── LSP HTTP client ───────────────────────────────────────────────────────────

type MonacoApi = Parameters<OnMount>[1];

type LspCompletion = {
  label: string;
  kind: number;
  detail: string | null;
  documentation: string | null;
  insert_text: string;
};

type LspHover = {
  signature: string | null;
  documentation: string | null;
};

async function fetchCompletions(
  source: string,
  line: number,
  column: number,
): Promise<LspCompletion[]> {
  try {
    const res = await fetch("/api/lsp/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source, line, column }),
    });
    if (!res.ok) return [];
    return (await res.json()) as LspCompletion[];
  } catch {
    return [];
  }
}

type LspDiagnostic = {
  message: string;
  severity: number;
  start_line: number;
  start_column: number;
  end_line: number;
  end_column: number;
  code: string | null;
};

async function fetchDiagnostics(source: string, sourceFile?: string): Promise<LspDiagnostic[]> {
  try {
    const res = await fetch("/api/lsp/diagnostics", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source, source_file: sourceFile }),
    });
    if (!res.ok) return [];
    return (await res.json()) as LspDiagnostic[];
  } catch {
    return [];
  }
}

async function fetchHover(source: string, line: number, column: number): Promise<LspHover | null> {
  try {
    const res = await fetch("/api/lsp/hover", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source, line, column }),
    });
    if (!res.ok) return null;
    return (await res.json()) as LspHover;
  } catch {
    return null;
  }
}

// ── File parsing (for context-aware trigger chars) ────────────────────────────

function detectCallContext(textBefore: string): string | null {
  let depth = 0;
  for (let i = textBefore.length - 1; i >= 0; i--) {
    const ch = textBefore[i];
    if (ch === ")") {
      depth++;
      continue;
    }
    if (ch === "(") {
      if (depth === 0) {
        const match = /(\w+)\s*$/.exec(textBefore.slice(0, i));
        return match ? match[1] : null;
      }
      depth--;
    }
  }
  return null;
}

function isImportCompletionContext(textBefore: string): boolean {
  const currentLine = textBefore.split("\n").at(-1) ?? "";
  return /^\s*(?:import\s+[\w.]*|from\s+[\w.]+(?:\s+import\s+[\w]*)?)\s*$/.test(currentLine);
}

// ── Clay-specific hover docs ──────────────────────────────────────────────────

const CLAY_HOVER: Record<string, { sig: string; doc: string }> = {
  Input: {
    sig: "class Input(BaseModel)",
    doc: "Typed alias for this tool's input Pydantic model.",
  },
  Output: {
    sig: "class Output(BaseModel)",
    doc: "Typed alias for this tool's output Pydantic model.",
  },
  AppContext: {
    sig: "class AppContext",
    doc: "Clay runtime context. Provides ctx.workspace, ctx.logger, ctx.env.",
  },
};

// ── Provider registration ─────────────────────────────────────────────────────

function registerClayProviders(monaco: MonacoApi) {
  // Hover: Jedi via HTTP, with Clay overrides for known aliases
  monaco.languages.registerHoverProvider("python", {
    async provideHover(model: editor.ITextModel, position: Position) {
      const word = model.getWordAtPosition(position);
      if (!word) return null;

      // Clay-specific overrides first
      const clayInfo = CLAY_HOVER[word.word];
      if (clayInfo) {
        return {
          range: new monaco.Range(
            position.lineNumber,
            word.startColumn,
            position.lineNumber,
            word.endColumn,
          ),
          contents: [{ value: `\`\`\`python\n${clayInfo.sig}\n\`\`\`` }, { value: clayInfo.doc }],
        };
      }

      // Jedi hover
      const hover = await fetchHover(
        model.getValue(),
        position.lineNumber - 1,
        position.column - 1,
      );
      if (!hover?.signature && !hover?.documentation) return null;

      return {
        range: new monaco.Range(
          position.lineNumber,
          word.startColumn,
          position.lineNumber,
          word.endColumn,
        ),
        contents: [
          ...(hover.signature ? [{ value: `\`\`\`python\n${hover.signature}\n\`\`\`` }] : []),
          ...(hover.documentation ? [{ value: hover.documentation }] : []),
        ],
      };
    },
  });

  // Completions: Jedi via HTTP, with context-aware insertion
  monaco.languages.registerCompletionItemProvider("python", {
    triggerCharacters: [".", "(", ",", " "],

    async provideCompletionItems(model: editor.ITextModel, position: Position) {
      const source = model.getValue();
      const textBefore = model.getValueInRange({
        startLineNumber: 1,
        startColumn: 1,
        endLineNumber: position.lineNumber,
        endColumn: position.column,
      });

      const word = model.getWordUntilPosition(position);
      const range = new monaco.Range(
        position.lineNumber,
        word.startColumn,
        position.lineNumber,
        word.endColumn,
      );

      // Only fetch if there's something to complete or a relevant trigger char was used
      const lastChar = textBefore.slice(-1);
      const importCompletion = isImportCompletionContext(textBefore);
      if (!word.word && ![".", "(", ","].includes(lastChar) && !importCompletion) {
        return { suggestions: [] };
      }

      // Detect if cursor is inside a constructor call — use insertText as "arg="
      const callCtx = detectCallContext(textBefore);
      const insideConstructor = callCtx === "Output" || callCtx === "Input";

      const items = await fetchCompletions(source, position.lineNumber - 1, position.column - 1);

      return {
        suggestions: items.map((item) => ({
          label: item.label,
          kind: item.kind,
          detail: item.detail ?? undefined,
          documentation: item.documentation ? { value: item.documentation } : undefined,
          insertText: insideConstructor ? `${item.insert_text}=` : item.insert_text,
          range,
        })),
        // Tell Monaco to not cache — Jedi results are source-dependent
        incomplete: true,
      };
    },
  });
}

// ── Component ─────────────────────────────────────────────────────────────────

type CodeEditorProps = {
  value: string;
  onChange?: (value: string) => void;
  readOnly?: boolean;
  minHeight?: string;
  height?: string;
  className?: string;
  fullFeatures?: boolean;
  sourceFile?: string;
  onMount?: OnMount;
};

const MONACO_OPTIONS: editor.IStandaloneEditorConstructionOptions = {
  language: "python",
  theme: "vs-dark",
  fontSize: 13,
  fontFamily: "JetBrains Mono, Menlo, Monaco, Consolas, monospace",
  tabSize: 4,
  insertSpaces: true,
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  wordWrap: "on",
  automaticLayout: true,
  lineNumbers: "on",
  folding: true,
  bracketPairColorization: { enabled: true },
  suggest: { showKeywords: true, showSnippets: true, showClasses: true, showFunctions: true },
  quickSuggestions: { other: true, comments: false, strings: false },
  parameterHints: { enabled: true },
  hover: { enabled: true, delay: 300 },
  formatOnType: true,
  formatOnPaste: true,
};

let providersRegistered = false;

const DIAGNOSTICS_DEBOUNCE_MS = 800;
const DIAGNOSTICS_MODEL_ID = "clay-py-diagnostics";

export function CodeEditor({
  value,
  onChange,
  readOnly = false,
  minHeight,
  height,
  className,
  fullFeatures = false,
  sourceFile,
  onMount,
}: CodeEditorProps) {
  const monacoRef = useRef<MonacoApi>(null);
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const diagTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [diagnostics, setDiagnostics] = useState<LspDiagnostic[]>([]);
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(false);

  const diagnosticSummary = useMemo(() => {
    const errors = diagnostics.filter((d) => d.severity >= 8).length;
    const warnings = diagnostics.filter((d) => d.severity === 4).length;
    return { errors, warnings };
  }, [diagnostics]);

  const runDiagnostics = useCallback(
    async (editorInstance: editor.IStandaloneCodeEditor, monaco: MonacoApi) => {
      const source = editorInstance.getValue();
      const nextDiagnostics = await fetchDiagnostics(source, sourceFile);
      const model = editorInstance.getModel();
      if (!model) return;
      setDiagnostics(nextDiagnostics);
      monaco.editor.setModelMarkers(
        model,
        DIAGNOSTICS_MODEL_ID,
        nextDiagnostics.map((d) => ({
          severity: d.severity,
          startLineNumber: d.start_line,
          startColumn: d.start_column,
          endLineNumber: d.end_line,
          endColumn: d.end_column,
          message: d.message,
          source: "ty",
          code: d.code ?? undefined,
        })),
      );
    },
    [sourceFile],
  );

  // Run ty diagnostics whenever value changes (debounced)
  useEffect(() => {
    const monaco = monacoRef.current;
    const editorInstance = editorRef.current;
    if (!monaco || !editorInstance) return;

    if (diagTimerRef.current) clearTimeout(diagTimerRef.current);
    diagTimerRef.current = setTimeout(async () => {
      await runDiagnostics(editorInstance, monaco);
    }, DIAGNOSTICS_DEBOUNCE_MS);

    return () => {
      if (diagTimerRef.current) clearTimeout(diagTimerRef.current);
    };
  }, [runDiagnostics, value]);

  const handleMount: OnMount = (editorInstance, monaco) => {
    monacoRef.current = monaco;
    editorRef.current = editorInstance;
    if (!providersRegistered) {
      registerClayProviders(monaco);
      providersRegistered = true;
    }
    void runDiagnostics(editorInstance, monaco);
    onMount?.(editorInstance, monaco);
  };

  const resolvedHeight = height ?? minHeight ?? "200px";

  function handleDiagnosticClick(diagnostic: LspDiagnostic) {
    const editorInstance = editorRef.current;
    if (!editorInstance) return;

    editorInstance.revealLineInCenter(diagnostic.start_line);
    editorInstance.setPosition({
      lineNumber: diagnostic.start_line,
      column: diagnostic.start_column,
    });
    editorInstance.focus();
  }

  return (
    <div
      className={cn("flex min-h-0 flex-col overflow-hidden rounded-md border", className)}
      style={{ height: resolvedHeight }}
    >
      <div className="min-h-0 flex-1">
        <Editor
          height="100%"
          defaultLanguage="python"
          value={value}
          onChange={(v) => onChange?.(v ?? "")}
          options={{ ...MONACO_OPTIONS, readOnly }}
          onMount={handleMount}
          loading={
            <div className="flex h-full items-center justify-center bg-[#1e1e1e] text-xs text-zinc-400">
              Loading editor…
            </div>
          }
        />
      </div>
      {fullFeatures ? (
        <div className="shrink-0 border-t bg-background">
          <button
            type="button"
            className="flex h-9 w-full items-center justify-between gap-3 px-3 text-left text-xs hover:bg-muted/60"
            onClick={() => setDiagnosticsOpen((open) => !open)}
          >
            <span className="flex min-w-0 items-center gap-2">
              <AlertCircle className="size-3.5 text-muted-foreground" />
              <span className="font-medium">Problems</span>
              <span className="text-muted-foreground">
                {diagnostics.length === 0
                  ? "No ty diagnostics"
                  : `${diagnosticSummary.errors} errors, ${diagnosticSummary.warnings} warnings`}
              </span>
            </span>
            {diagnosticsOpen ? (
              <ChevronDown className="size-4 text-muted-foreground" />
            ) : (
              <ChevronUp className="size-4 text-muted-foreground" />
            )}
          </button>
          {diagnosticsOpen ? (
            <div className="max-h-48 overflow-y-auto border-t bg-muted/20">
              {diagnostics.length === 0 ? (
                <div className="px-3 py-4 text-xs text-muted-foreground">
                  No problems found in this file.
                </div>
              ) : (
                <div className="divide-y">
                  {diagnostics.map((diagnostic, index) => (
                    <button
                      key={`${diagnostic.start_line}:${diagnostic.start_column}:${index}`}
                      type="button"
                      className="grid w-full grid-cols-[auto_1fr] gap-x-3 px-3 py-2 text-left text-xs hover:bg-muted"
                      onClick={() => handleDiagnosticClick(diagnostic)}
                    >
                      <span
                        className={cn(
                          "font-mono",
                          diagnostic.severity >= 8
                            ? "text-destructive"
                            : "text-amber-600 dark:text-amber-400",
                        )}
                      >
                        {diagnostic.start_line}:{diagnostic.start_column}
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate">{diagnostic.message}</span>
                        {diagnostic.code ? (
                          <span className="font-mono text-muted-foreground">{diagnostic.code}</span>
                        ) : null}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
