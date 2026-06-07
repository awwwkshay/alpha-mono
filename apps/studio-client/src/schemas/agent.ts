import { z } from "zod";

export const AgentCreateSchema = z.object({
  id: z
    .string()
    .min(1, "Agent id is required")
    .regex(/^[a-z0-9_]+$/, {
      message: "Id must be lowercase letters, numbers, or underscores",
    }),
  name: z.string().min(1, "Name is required"),
  model: z.string().min(1, "Model is required"),
  system_prompt: z.string().min(1, "System prompt is required"),
  description: z.string().optional(),
});

export const AgentUpdateSchema = z.object({
  name: z.string().min(1, "Name is required"),
  model: z.string().min(1, "Model is required"),
  system_prompt: z.string().min(1, "System prompt is required"),
  description: z.string().optional(),
});

export type AgentCreateFormData = z.infer<typeof AgentCreateSchema>;
export type AgentUpdateFormData = z.infer<typeof AgentUpdateSchema>;
