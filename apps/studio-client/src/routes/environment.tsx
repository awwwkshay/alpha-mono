import { useForm } from "@tanstack/react-form";
import { createFileRoute } from "@tanstack/react-router";
import { Loader2, Plus, Save } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { STUDIO_SYNC_EVENT, getEnvVars, updateEnvVars } from "@/lib/api";
import { useApi } from "@/hooks/use-api";

export const Route = createFileRoute("/environment")({
  component: EnvironmentRoute,
});

function EnvironmentRoute() {
  const loadEnvVars = useCallback(() => getEnvVars(), []);
  const envVars = useApi(loadEnvVars);
  const [items, setItems] = useState<Record<string, EnvEditorItem>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (envVars.status !== "ready") return;
    setItems(Object.fromEntries(envVars.data.map((item) => [item.key, item])));
  }, [envVars]);

  const keys = Object.keys(items).sort();
  const addVariableForm = useForm({
    defaultValues: {
      key: "",
      value: "",
      description: "",
    },
    validators: { onSubmit: EnvVariableSchema },
    onSubmit: async ({ value }) => {
      const key = normalizeEnvVarName(value.key);
      const nextItems = {
        ...items,
        [key]: {
          key,
          value: value.value,
          description: value.description.trim() || null,
        },
      };
      const savedItems = await updateEnvVars(nextItems);
      setItems(envItemsByKey(savedItems));
      addVariableForm.reset();
      setError(null);
      window.dispatchEvent(new Event(STUDIO_SYNC_EVENT));
    },
  });

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const payload = { ...items };
      const savedItems = await updateEnvVars(payload);
      setItems(envItemsByKey(savedItems));
      window.dispatchEvent(new Event(STUDIO_SYNC_EVENT));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save environment variables");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid gap-5">
      <section className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-normal">Environment</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage this project&apos;s local `.env` values. Saving also updates `.env.example` with
            the same keys and blank values.
          </p>
        </div>
        <Button onClick={() => void handleSave()} disabled={saving}>
          {saving ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
          Save
        </Button>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Variables</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          {envVars.status === "loading" ? (
            <div className="flex min-h-40 items-center justify-center">
              <Loader2 className="size-5 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <>
              <div className="grid overflow-hidden rounded-md border">
                <div className="grid grid-cols-[minmax(12rem,1fr)_minmax(0,1fr)_minmax(0,2fr)] gap-3 border-b bg-muted/40 px-3 py-2 text-xs font-medium uppercase tracking-normal text-muted-foreground">
                  <div>Name</div>
                  <div>Value</div>
                  <div>Description</div>
                </div>
                {keys.map((key) => (
                  <div
                    key={key}
                    className="grid grid-cols-[minmax(12rem,1fr)_minmax(0,1fr)_minmax(0,2fr)] items-center gap-3 border-b px-3 py-3 last:border-b-0"
                  >
                    <label className="font-mono text-sm text-foreground">{key}</label>
                    <Input
                      type="password"
                      value={items[key]?.value ?? ""}
                      onChange={(event) =>
                        setItems((current) => ({
                          ...current,
                          [key]: {
                            key,
                            value: event.target.value,
                            description: current[key]?.description ?? null,
                          },
                        }))
                      }
                    />
                    <Input
                      value={items[key]?.description ?? ""}
                      onChange={(event) =>
                        setItems((current) => ({
                          ...current,
                          [key]: {
                            key,
                            value: current[key]?.value ?? "",
                            description: event.target.value || null,
                          },
                        }))
                      }
                      placeholder="Description"
                    />
                  </div>
                ))}
                <form
                  className="grid gap-3 border-t bg-muted/20 px-3 py-3"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void addVariableForm.handleSubmit();
                  }}
                >
                  <div className="grid gap-2 md:grid-cols-[1fr_1fr_2fr]">
                    <addVariableForm.Field name="key">
                      {(field) => (
                        <Input
                          value={field.state.value}
                          onBlur={field.handleBlur}
                          onChange={(event) =>
                            field.handleChange(normalizeEnvVarName(event.target.value))
                          }
                          placeholder="NEW_ENV_VAR"
                        />
                      )}
                    </addVariableForm.Field>
                    <addVariableForm.Field name="value">
                      {(field) => (
                        <Input
                          type="password"
                          value={field.state.value}
                          onBlur={field.handleBlur}
                          onChange={(event) => field.handleChange(event.target.value)}
                          placeholder="Value"
                        />
                      )}
                    </addVariableForm.Field>
                    <addVariableForm.Field name="description">
                      {(field) => (
                        <Input
                          value={field.state.value}
                          onBlur={field.handleBlur}
                          onChange={(event) => field.handleChange(event.target.value)}
                          placeholder="Description"
                        />
                      )}
                    </addVariableForm.Field>
                  </div>
                  <addVariableForm.Subscribe
                    selector={(state) => ({
                      canSubmit: state.canSubmit,
                      errorMap: state.errorMap,
                      isSubmitting: state.isSubmitting,
                    })}
                  >
                    {({ canSubmit, errorMap, isSubmitting }) => (
                      <>
                        {errorMap.onSubmit ? (
                          <p className="text-sm text-destructive">
                            Environment variable names must start with a letter and use A-Z, 0-9, or
                            underscores.
                          </p>
                        ) : null}
                        <Button
                          className="justify-self-end"
                          type="submit"
                          variant="outline"
                          disabled={!canSubmit || isSubmitting}
                        >
                          <Plus className="size-4" />
                          Add
                        </Button>
                      </>
                    )}
                  </addVariableForm.Subscribe>
                </form>
              </div>
            </>
          )}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}

type EnvEditorItem = {
  key: string;
  value: string;
  description?: string | null;
};

const ENV_VAR_NAME_PATTERN = /^[A-Z][A-Z0-9_]*$/;

const EnvVariableSchema = z.object({
  key: z.string().min(1).regex(ENV_VAR_NAME_PATTERN),
  value: z.string(),
  description: z.string(),
});

function normalizeEnvVarName(value: string) {
  return value
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^[^A-Z]+/, "");
}

function envItemsByKey(items: EnvEditorItem[]) {
  return Object.fromEntries(items.map((item) => [item.key, item]));
}
