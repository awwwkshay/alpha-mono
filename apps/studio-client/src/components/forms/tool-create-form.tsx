import { useForm } from "@tanstack/react-form";
import { Loader2, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { CodeEditor } from "@/components/code-editor";
import { FieldGroup } from "@/components/field-group";
import { FieldDescription } from "@/components/ui/field";
import { type AgentSummary, createTool } from "@/lib/api";
import {
  PYTHON_TYPE_OPTIONS,
  ToolCreateSchema,
  type ToolFieldData,
  generateExecuteTemplate,
} from "@/schemas/tool";

export function ToolCreateForm({
  agents,
  onSuccess,
}: {
  agents: AgentSummary[];
  onSuccess: () => void;
}) {
  const [inputFields, setInputFields] = useState<ToolFieldData[]>([]);
  const [outputFields, setOutputFields] = useState<ToolFieldData[]>([
    { name: "result", type: "str", required: true },
  ]);

  const form = useForm({
    defaultValues: {
      tool_id: "",
      name: "",
      description: "",
      execute_body: generateExecuteTemplate([], [{ name: "result", type: "str", required: true }]),
      input_fields: [] as ToolFieldData[],
      output_fields: [{ name: "result", type: "str", required: true }] as ToolFieldData[],
    } as {
      tool_id: string;
      name: string;
      description: string;
      execute_body: string;
      input_fields: ToolFieldData[];
      output_fields: ToolFieldData[];
      agent_id?: string;
    },
    validators: { onSubmit: ToolCreateSchema },
    onSubmit: async ({ value }) => {
      await createTool({
        tool_id: value.tool_id,
        name: value.name,
        description: value.description,
        execute_body: value.execute_body,
        input_fields: value.input_fields,
        output_fields: value.output_fields,
        ...(value.agent_id ? { agent_id: value.agent_id } : {}),
      });
      onSuccess();
    },
  });

  function refreshTemplate(newInput: ToolFieldData[], newOutput: ToolFieldData[]) {
    form.setFieldValue("execute_body", generateExecuteTemplate(newInput, newOutput));
    form.setFieldValue("input_fields", newInput);
    form.setFieldValue("output_fields", newOutput);
  }

  function addInputField() {
    const updated = [...inputFields, { name: "", type: "str" as const, required: true }];
    setInputFields(updated);
    refreshTemplate(updated, outputFields);
  }

  function addOutputField() {
    const updated = [...outputFields, { name: "", type: "str" as const, required: true }];
    setOutputFields(updated);
    refreshTemplate(inputFields, updated);
  }

  function updateInputField(i: number, patch: Partial<ToolFieldData>) {
    const updated = inputFields.map((f, idx) => (idx === i ? { ...f, ...patch } : f));
    setInputFields(updated);
    refreshTemplate(updated, outputFields);
  }

  function updateOutputField(i: number, patch: Partial<ToolFieldData>) {
    const updated = outputFields.map((f, idx) => (idx === i ? { ...f, ...patch } : f));
    setOutputFields(updated);
    refreshTemplate(inputFields, updated);
  }

  function removeInputField(i: number) {
    const updated = inputFields.filter((_, idx) => idx !== i);
    setInputFields(updated);
    refreshTemplate(updated, outputFields);
  }

  function removeOutputField(i: number) {
    const updated = outputFields.filter((_, idx) => idx !== i);
    setOutputFields(updated);
    refreshTemplate(inputFields, updated);
  }

  return (
    <form
      className="grid gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        void form.handleSubmit();
      }}
    >
      {/* Optional agent selector */}
      {agents.length > 0 ? (
        <form.Field name="agent_id">
          {(field) => (
            <FieldGroup label="Wire to agent (optional)" errors={field.state.meta.errors}>
              <select
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={field.state.value ?? ""}
                onChange={(e) => field.handleChange(e.target.value || undefined)}
                onBlur={field.handleBlur}
              >
                <option value="">— None, save standalone —</option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name} ({a.id})
                  </option>
                ))}
              </select>
              <FieldDescription>
                Leave blank to save the tool without attaching it to an agent yet.
              </FieldDescription>
            </FieldGroup>
          )}
        </form.Field>
      ) : null}

      <div className="grid gap-3 md:grid-cols-2">
        <form.Field name="tool_id">
          {(field) => (
            <FieldGroup label="Tool id" errors={field.state.meta.errors}>
              <Input
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
                placeholder="get_weather"
              />
            </FieldGroup>
          )}
        </form.Field>

        <form.Field name="name">
          {(field) => (
            <FieldGroup label="Display name" errors={field.state.meta.errors}>
              <Input
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
                placeholder="Get Weather"
              />
            </FieldGroup>
          )}
        </form.Field>
      </div>

      <form.Field name="description">
        {(field) => (
          <FieldGroup label="Description" errors={field.state.meta.errors}>
            <Input
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              placeholder="Fetches current weather for a location."
            />
          </FieldGroup>
        )}
      </form.Field>

      {/* Input schema fields */}
      <SchemaFieldBuilder
        label="Input fields"
        description="Fields the caller must pass to this tool."
        fields={inputFields}
        onAdd={addInputField}
        onUpdate={updateInputField}
        onRemove={removeInputField}
      />

      {/* Output schema fields */}
      <form.Field name="output_fields">
        {(field) => (
          <SchemaFieldBuilder
            label="Output fields"
            description="Fields returned by this tool."
            fields={outputFields}
            onAdd={addOutputField}
            onUpdate={updateOutputField}
            onRemove={removeOutputField}
            error={
              field.state.meta.errors[0] != null
                ? typeof field.state.meta.errors[0] === "string"
                  ? field.state.meta.errors[0]
                  : "At least one output field is required"
                : undefined
            }
          />
        )}
      </form.Field>

      {/* Execute function editor */}
      <form.Field name="execute_body">
        {(field) => (
          <FieldGroup label="Execute function" errors={field.state.meta.errors}>
            <FieldDescription>
              Edit{" "}
              <code className="font-mono text-xs">
                async def _execute(inp: Input, ctx: AppContext) → Output
              </code>
              . The template updates automatically as you add fields.
            </FieldDescription>
            <CodeEditor
              value={field.state.value}
              onChange={(v) => field.handleChange(v)}
              minHeight="180px"
              fullFeatures
            />
          </FieldGroup>
        )}
      </form.Field>

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
                {isSubmitting ? "Creating" : "Create tool"}
              </Button>
            </DialogFooter>
          </>
        )}
      </form.Subscribe>
    </form>
  );
}

function SchemaFieldBuilder({
  label,
  description,
  fields,
  onAdd,
  onUpdate,
  onRemove,
  error,
}: {
  label: string;
  description: string;
  fields: ToolFieldData[];
  onAdd: () => void;
  onUpdate: (i: number, patch: Partial<ToolFieldData>) => void;
  onRemove: (i: number) => void;
  error?: string;
}) {
  return (
    <div className="grid gap-2">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium leading-none">{label}</p>
          <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={onAdd}>
          <Plus className="size-3.5" />
          Add field
        </Button>
      </div>

      {fields.length > 0 ? (
        <div className="grid gap-1.5">
          <div className="grid grid-cols-[1fr_130px_60px_24px] gap-2 px-1 text-xs text-muted-foreground">
            <span>Name</span>
            <span>Type</span>
            <span>Required</span>
            <span />
          </div>
          {fields.map((f, i) => (
            <div key={i} className="grid grid-cols-[1fr_130px_60px_24px] items-center gap-2">
              <Input
                value={f.name}
                onChange={(e) => onUpdate(i, { name: e.target.value })}
                placeholder="field_name"
                className="h-8 font-mono text-xs"
              />
              <select
                value={f.type}
                onChange={(e) => onUpdate(i, { type: e.target.value as ToolFieldData["type"] })}
                className="flex h-8 w-full rounded-md border border-input bg-transparent px-2 text-xs shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                {PYTHON_TYPE_OPTIONS.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <div className="flex justify-center">
                <input
                  type="checkbox"
                  checked={f.required}
                  onChange={(e) => onUpdate(i, { required: e.target.checked })}
                  className="size-4 cursor-pointer"
                />
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="size-6 text-muted-foreground hover:text-destructive"
                onClick={() => onRemove(i)}
              >
                <Trash2 className="size-3" />
              </Button>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">No fields defined yet.</p>
      )}

      {error ? <p className="text-xs text-destructive">{error}</p> : null}
    </div>
  );
}
