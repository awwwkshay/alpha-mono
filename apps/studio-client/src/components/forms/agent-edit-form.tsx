import { useForm } from "@tanstack/react-form";
import { Loader2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ModelCombobox } from "@/components/model-combobox";
import { FieldGroup } from "@/components/field-group";
import { type AgentSummary, updateAgent } from "@/lib/api";
import { AgentUpdateSchema } from "@/schemas/agent";

export function AgentEditForm({
  agent,
  modelList,
  onSuccess,
}: {
  agent: AgentSummary;
  modelList: string[];
  onSuccess: () => void;
}) {
  const [modelValue, setModelValue] = useState(agent.model ?? "gemini/gemini-2.0-flash");

  const form = useForm({
    defaultValues: {
      name: agent.name,
      model: agent.model ?? "gemini/gemini-2.0-flash",
      system_prompt: agent.system_prompt ?? "",
      ...(agent.description ? { description: agent.description } : {}),
    } as { name: string; model: string; system_prompt: string; description?: string },
    validators: { onSubmit: AgentUpdateSchema },
    onSubmit: async ({ value }) => {
      await updateAgent(agent.id, {
        name: value.name,
        model: value.model || modelValue,
        system_prompt: value.system_prompt,
        ...(value.description ? { description: value.description } : {}),
      });
      onSuccess();
    },
  });

  return (
    <form
      className="grid gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        void form.handleSubmit();
      }}
    >
      <div className="grid gap-3 md:grid-cols-2">
        <form.Field name="name">
          {(field) => (
            <FieldGroup label="Name" errors={field.state.meta.errors}>
              <Input
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
              />
            </FieldGroup>
          )}
        </form.Field>

        <form.Field name="model">
          {(field) => (
            <FieldGroup label="Model" errors={field.state.meta.errors}>
              <ModelCombobox
                name="model"
                value={modelValue}
                onChange={(v) => {
                  setModelValue(v);
                  field.handleChange(v);
                }}
                models={modelList}
              />
            </FieldGroup>
          )}
        </form.Field>

        <div className="md:col-span-2">
          <form.Field name="description">
            {(field) => (
              <FieldGroup label="Description" errors={field.state.meta.errors}>
                <Input
                  value={field.state.value ?? ""}
                  onChange={(e) => field.handleChange(e.target.value || undefined)}
                  onBlur={field.handleBlur}
                />
              </FieldGroup>
            )}
          </form.Field>
        </div>

        <div className="md:col-span-2">
          <form.Field name="system_prompt">
            {(field) => (
              <FieldGroup label="System prompt" errors={field.state.meta.errors}>
                <Textarea
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  rows={6}
                />
              </FieldGroup>
            )}
          </form.Field>
        </div>
      </div>

      <form.Subscribe selector={(s) => ({ isSubmitting: s.isSubmitting, errorMap: s.errorMap })}>
        {({ isSubmitting, errorMap }) => (
          <>
            {errorMap.onSubmit ? (
              <p className="text-sm text-destructive">{JSON.stringify(errorMap.onSubmit)}</p>
            ) : null}
            <DialogFooter>
              <Button disabled={isSubmitting} type="submit">
                {isSubmitting ? <Loader2 className="size-4 animate-spin" /> : null}
                {isSubmitting ? "Saving" : "Save changes"}
              </Button>
            </DialogFooter>
          </>
        )}
      </form.Subscribe>
    </form>
  );
}
