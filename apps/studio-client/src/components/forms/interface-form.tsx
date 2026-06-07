import { useForm } from "@tanstack/react-form";
import { Loader2, Plus } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { FieldGroup } from "@/components/field-group";
import { FieldDescription } from "@/components/ui/field";
import { type AgentSummary, addInterface } from "@/lib/api";
import { SlackInterfaceSchema, TelegramInterfaceSchema } from "@/schemas/interface";

type InterfaceType = "slack" | "telegram";

export function InterfaceForm({
  agents,
  onSuccess,
}: {
  agents: AgentSummary[];
  onSuccess: () => void;
}) {
  const [selectedType, setSelectedType] = useState<InterfaceType>("slack");
  const [selectedAgentId, setSelectedAgentId] = useState("");

  const slackForm = useForm({
    defaultValues: {
      id: "slack_chat",
      token_env: "SLACK_BOT_TOKEN",
      signing_secret_env: "SLACK_SIGNING_SECRET",
    } as {
      id: string;
      token_env: string;
      token?: string;
      signing_secret_env: string;
      signing_secret?: string;
    },
    validators: { onSubmit: SlackInterfaceSchema.omit({ type: true }) },
    onSubmit: async ({ value }) => {
      await addInterface({
        id: value.id,
        type: "slack",
        token_env: value.token_env,
        ...(value.token ? { token: value.token } : {}),
        signing_secret_env: value.signing_secret_env,
        ...(value.signing_secret ? { signing_secret: value.signing_secret } : {}),
        ...(selectedAgentId ? { agent_id: selectedAgentId } : {}),
      });
      onSuccess();
    },
  });

  const telegramForm = useForm({
    defaultValues: {
      id: "telegram_chat",
      token_env: "TELEGRAM_BOT_TOKEN",
      token: "",
      secret_token_env: "TELEGRAM_WEBHOOK_SECRET",
      secret_token: "",
    } as {
      id: string;
      token_env: string;
      token?: string;
      secret_token_env: string;
      secret_token?: string;
      base_url?: string;
    },
    validators: { onSubmit: TelegramInterfaceSchema.omit({ type: true }) },
    onSubmit: async ({ value }) => {
      await addInterface({
        id: value.id,
        type: "telegram",
        token_env: value.token_env,
        ...(value.token ? { token: value.token } : {}),
        secret_token_env: value.secret_token_env,
        ...(value.secret_token ? { secret_token: value.secret_token } : {}),
        ...(value.base_url ? { base_url: value.base_url } : {}),
        ...(selectedAgentId ? { agent_id: selectedAgentId } : {}),
      });
      onSuccess();
    },
  });

  const activeForm = selectedType === "slack" ? slackForm : telegramForm;

  return (
    <form
      className="grid gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        void activeForm.handleSubmit();
      }}
    >
      {/* Optional agent selector */}
      {agents.length > 0 ? (
        <div className="grid gap-1.5">
          <label className="text-sm font-medium">Wire to agent (optional)</label>
          <select
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            value={selectedAgentId}
            onChange={(e) => setSelectedAgentId(e.target.value)}
          >
            <option value="">— None, save standalone —</option>
            {agents.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} ({a.id})
              </option>
            ))}
          </select>
          <p className="text-xs text-muted-foreground">
            Leave blank to save the interface config without attaching it to an agent yet.
          </p>
        </div>
      ) : null}

      {/* Platform tabs */}
      <div className="grid gap-1.5">
        <label className="text-sm font-medium">Platform</label>
        <div className="flex gap-2">
          <Button
            type="button"
            variant={selectedType === "slack" ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedType("slack")}
          >
            Slack
          </Button>
          <Button
            type="button"
            variant={selectedType === "telegram" ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedType("telegram")}
          >
            Telegram
          </Button>
        </div>
      </div>

      {/* Slack fields */}
      {selectedType === "slack" ? (
        <>
          <slackForm.Field name="id">
            {(field) => (
              <FieldGroup label="Chat app id" errors={field.state.meta.errors}>
                <Input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="slack_sales"
                />
                <FieldDescription>
                  Unique id for this SlackChat. Use a different id for each Slack app.
                </FieldDescription>
              </FieldGroup>
            )}
          </slackForm.Field>

          <slackForm.Field name="token_env">
            {(field) => (
              <FieldGroup label="Bot token env var" errors={field.state.meta.errors}>
                <Input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="SLACK_BOT_TOKEN"
                />
                <FieldDescription>
                  Environment variable containing the Slack bot token.
                </FieldDescription>
              </FieldGroup>
            )}
          </slackForm.Field>

          <slackForm.Field name="token">
            {(field) => (
              <FieldGroup label="Bot token value" errors={field.state.meta.errors}>
                <Input
                  type="password"
                  value={field.state.value ?? ""}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="xoxb-..."
                />
                <FieldDescription>
                  Optional. If set, SlackChat uses this value instead of reading the env var.
                </FieldDescription>
              </FieldGroup>
            )}
          </slackForm.Field>

          <slackForm.Field name="signing_secret_env">
            {(field) => (
              <FieldGroup label="Signing secret env var" errors={field.state.meta.errors}>
                <Input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="SLACK_SIGNING_SECRET"
                />
                <FieldDescription>
                  Environment variable containing the Slack signing secret.
                </FieldDescription>
              </FieldGroup>
            )}
          </slackForm.Field>

          <slackForm.Field name="signing_secret">
            {(field) => (
              <FieldGroup label="Signing secret value" errors={field.state.meta.errors}>
                <Input
                  type="password"
                  value={field.state.value ?? ""}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="Slack signing secret"
                />
                <FieldDescription>
                  Optional. If set, SlackChat uses this value instead of reading the env var.
                </FieldDescription>
              </FieldGroup>
            )}
          </slackForm.Field>
        </>
      ) : (
        <>
          <telegramForm.Field name="id">
            {(field) => (
              <FieldGroup label="Chat app id" errors={field.state.meta.errors}>
                <Input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="telegram_sales"
                />
                <FieldDescription>
                  Unique id for this TelegramChat. Use a different id for each Telegram app.
                </FieldDescription>
              </FieldGroup>
            )}
          </telegramForm.Field>

          <telegramForm.Field name="token_env">
            {(field) => (
              <FieldGroup label="Bot token env var" errors={field.state.meta.errors}>
                <Input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="TELEGRAM_BOT_TOKEN"
                />
                <FieldDescription>
                  Environment variable containing the Telegram bot token.
                </FieldDescription>
              </FieldGroup>
            )}
          </telegramForm.Field>

          <telegramForm.Field name="token">
            {(field) => (
              <FieldGroup label="Bot token value" errors={field.state.meta.errors}>
                <Input
                  type="password"
                  value={field.state.value ?? ""}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="Telegram bot token"
                />
                <FieldDescription>
                  Optional. If set, TelegramChat uses this value instead of reading the env var.
                </FieldDescription>
              </FieldGroup>
            )}
          </telegramForm.Field>

          <telegramForm.Field name="secret_token_env">
            {(field) => (
              <FieldGroup label="Webhook secret env var" errors={field.state.meta.errors}>
                <Input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="TELEGRAM_WEBHOOK_SECRET"
                />
                <FieldDescription>Optional — verifies incoming webhook requests.</FieldDescription>
              </FieldGroup>
            )}
          </telegramForm.Field>

          <telegramForm.Field name="secret_token">
            {(field) => (
              <FieldGroup label="Webhook secret value" errors={field.state.meta.errors}>
                <Input
                  type="password"
                  value={field.state.value ?? ""}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="Telegram webhook secret"
                />
                <FieldDescription>
                  Optional. If set, TelegramChat uses this value instead of reading the env var.
                </FieldDescription>
              </FieldGroup>
            )}
          </telegramForm.Field>

          <telegramForm.Field name="base_url">
            {(field) => (
              <FieldGroup label="Public base URL" errors={field.state.meta.errors}>
                <Input
                  value={field.state.value ?? ""}
                  onChange={(e) => field.handleChange(e.target.value || undefined)}
                  onBlur={field.handleBlur}
                  placeholder="https://your-host.com"
                />
                <FieldDescription>
                  Leave blank to read from PUBLIC_URL env var at runtime.
                </FieldDescription>
              </FieldGroup>
            )}
          </telegramForm.Field>
        </>
      )}

      <activeForm.Subscribe
        selector={(s) => ({ isSubmitting: s.isSubmitting, errorMap: s.errorMap })}
      >
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
                {isSubmitting ? "Adding" : "Add interface"}
              </Button>
            </DialogFooter>
          </>
        )}
      </activeForm.Subscribe>
    </form>
  );
}
