import { useForm } from "@tanstack/react-form";
import { Loader2, Plus } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ModelCombobox } from "@/components/model-combobox";
import { FieldGroup } from "@/components/field-group";
import { createAgent } from "@/lib/api";
import { AgentCreateSchema } from "@/schemas/agent";

export function AgentCreateForm({
  modelList,
  onSuccess,
}: {
  modelList: string[];
  onSuccess: () => void;
}) {
  const [modelValue, setModelValue] = useState("gemini/gemini-2.0-flash");

  const form = useForm({
    defaultValues: {
      id: "",
      name: "",
      model: "gemini/gemini-2.0-flash",
      system_prompt: "",
    } as { id: string; name: string; model: string; system_prompt: string; description?: string },
    validators: { onSubmit: AgentCreateSchema },
    onSubmit: async ({ value }) => {
      await createAgent({
        id: value.id,
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
        <form.Field name="id">
          {(field) => (
            <FieldGroup label="Agent id" errors={field.state.meta.errors}>
              <Input
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
                placeholder="sales_assistant"
              />
            </FieldGroup>
          )}
        </form.Field>

        <form.Field name="name">
          {(field) => (
            <FieldGroup label="Name" errors={field.state.meta.errors}>
              <Input
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
                placeholder="Sales Assistant"
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

        <form.Field name="description">
          {(field) => (
            <FieldGroup label="Description" errors={field.state.meta.errors}>
              <Input
                value={field.state.value ?? ""}
                onChange={(e) => field.handleChange(e.target.value || undefined)}
                onBlur={field.handleBlur}
                placeholder="Qualifies and researches leads"
              />
            </FieldGroup>
          )}
        </form.Field>

        <div className="md:col-span-2">
          <form.Field name="system_prompt">
            {(field) => (
              <FieldGroup label="System prompt" errors={field.state.meta.errors}>
                <Textarea
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="You are a sales assistant..."
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
                {isSubmitting ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Plus className="size-4" />
                )}
                {isSubmitting ? "Creating" : "Create agent"}
              </Button>
            </DialogFooter>
          </>
        )}
      </form.Subscribe>
    </form>
  );
}
