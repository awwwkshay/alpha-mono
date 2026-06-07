import { z } from "zod";

const PYTHON_TYPES = [
  "str",
  "int",
  "float",
  "bool",
  "list[str]",
  "list[int]",
  "dict[str, str]",
  "dict[str, Any]",
  "Any",
] as const;

export type PythonType = (typeof PYTHON_TYPES)[number];
export const PYTHON_TYPE_OPTIONS: PythonType[] = [...PYTHON_TYPES];

export const ToolFieldSchema = z.object({
  name: z
    .string()
    .min(1, "Field name is required")
    .regex(/^[a-z_][a-z0-9_]*$/, "Must be a valid Python identifier (snake_case)"),
  type: z.enum(PYTHON_TYPES),
  description: z.string().optional(),
  required: z.boolean(),
});

export const ToolCreateSchema = z.object({
  tool_id: z
    .string()
    .min(1, "Tool id is required")
    .regex(/^[a-z0-9_]+$/, "Id must be lowercase letters, numbers, or underscores"),
  name: z.string().min(1, "Name is required"),
  description: z.string().min(1, "Description is required"),
  input_fields: z.array(ToolFieldSchema),
  output_fields: z.array(ToolFieldSchema).min(1, "At least one output field is required"),
  execute_body: z
    .string()
    .min(1, "Execute function body is required")
    .refine(
      (v) => v.includes("async def _execute"),
      'Must define an "async def _execute" function',
    ),
});

export type ToolFieldData = z.infer<typeof ToolFieldSchema>;
export type ToolCreateFormData = z.infer<typeof ToolCreateSchema>;

export function generateExecuteTemplate(
  inputFields: ToolFieldData[],
  outputFields: ToolFieldData[],
): string {
  const inpHints = inputFields
    .map((f) => `    #   inp.${f.name}: ${f.required ? f.type : `${f.type} | None`}`)
    .join("\n");

  const outArgs = outputFields
    .map((f) => {
      const defaultVal = defaultForType(f.type);
      return `        ${f.name}=${defaultVal},`;
    })
    .join("\n");

  const inputSection = inpHints ? `\n    # Input fields:\n${inpHints}\n` : "";

  return `async def _execute(inp: Input, ctx: AppContext) -> Output:${inputSection}
    return Output(
${outArgs}
    )`;
}

function defaultForType(type: string): string {
  if (type === "str") return '""';
  if (type === "int") return "0";
  if (type === "float") return "0.0";
  if (type === "bool") return "False";
  if (type.startsWith("list")) return "[]";
  if (type.startsWith("dict")) return "{}";
  return "None";
}
