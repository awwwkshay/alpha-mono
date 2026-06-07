import { Field, FieldError, FieldLabel } from "@/components/ui/field";

export function FieldGroup({
  label,
  errors,
  children,
}: {
  label: string;
  errors: unknown[];
  children: React.ReactNode;
}) {
  const isInvalid = errors.length > 0;
  const normalizedErrors = errors
    .filter((e) => e != null)
    .map((e) =>
      typeof e === "string"
        ? { message: e }
        : typeof e === "object" && "message" in (e as object)
          ? (e as { message?: string })
          : { message: JSON.stringify(e) },
    );

  return (
    <Field data-invalid={isInvalid || undefined}>
      <FieldLabel>{label}</FieldLabel>
      {children}
      {isInvalid ? <FieldError errors={normalizedErrors} /> : null}
    </Field>
  );
}
