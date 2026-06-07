import { z } from "zod";

const envVar = z
  .string()
  .min(1, "Required")
  .regex(/^[A-Z][A-Z0-9_]*$/, "Must be a valid environment variable name");

const interfaceId = z
  .string()
  .min(1, "Required")
  .regex(/^[a-zA-Z][a-zA-Z0-9_-]*$/, "Use letters, numbers, underscores, or dashes");

const optionalSecret = z.string().optional();

const optionalUrl = z
  .string()
  .refine((val) => val === "" || /^https?:\/\/.+/.test(val), "Must be a valid URL (https://...)")
  .optional();

export const SlackInterfaceSchema = z.object({
  id: interfaceId,
  type: z.literal("slack"),
  token_env: envVar,
  token: optionalSecret,
  signing_secret_env: envVar,
  signing_secret: optionalSecret,
});

export const TelegramInterfaceSchema = z.object({
  id: interfaceId,
  type: z.literal("telegram"),
  token_env: envVar,
  token: optionalSecret,
  secret_token_env: envVar,
  secret_token: optionalSecret,
  base_url: optionalUrl,
});

export const InterfaceSchema = z.discriminatedUnion("type", [
  SlackInterfaceSchema,
  TelegramInterfaceSchema,
]);

export type SlackInterfaceFormData = z.infer<typeof SlackInterfaceSchema>;
export type TelegramInterfaceFormData = z.infer<typeof TelegramInterfaceSchema>;
export type InterfaceFormData = z.infer<typeof InterfaceSchema>;
