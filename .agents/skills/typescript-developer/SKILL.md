---
name: typescript-developer
description: Use for TypeScript, React, frontend, Vite, Vite+, Node package, route, UI, or test changes in clay-mono, especially apps/studio-client. Follow the Vite+ workflow, use vp commands for linting, formatting, type checks, builds, tests with Vitest, dependency operations, and dev server tasks, and verify local browser behavior when UI changes.
---

# TypeScript Developer

Use this skill before TypeScript, React, frontend, routing, package, build, lint, format, test, or UI behavior changes in `clay-mono`.

## Workflow

Follow the same shape for every change:

1. Analyse the requested behavior and identify the affected app or package.
2. Read local instructions first: root `AGENTS.md`, nearest app `AGENTS.md`, `package.json`, `vite.config.ts`, `tsconfig.json`, and nearby implementation/tests.
3. Explore with `rg` and `rg --files` before editing.
4. Clarify only when multiple plausible implementations would materially change behavior.
5. State the files or file groups to change before editing.
6. Implement with existing project patterns and scoped edits.
7. Verify with the relevant Vite+ commands.
8. Summarize changed files, commands run, and remaining risk.

## Vite+ Rules

- Use `vp` for this app's JavaScript tooling. Do not call `pnpm`, `npm`, `yarn`, `vite`, `vitest`, `tsc`, `eslint`, `prettier`, `oxlint`, or `oxfmt` directly unless local instructions explicitly require it.
- Use `vp check` for the standard format, lint, and TypeScript validation pass.
- Use `vp test` for Vitest tests.
- Use `vp build` for production build verification.
- Use `vp dev` for the Vite dev server. If a `package.json` script named `dev` needs to run instead of the built-in Vite+ dev command, use `vp run dev`.
- Use `vp run <script>` for custom `package.json` scripts that share names with Vite+ built-ins or are not direct Vite+ commands.
- Use `vp add`, `vp remove`, `vp update`, `vp install`, `vp why`, and `vp list` for dependency work.
- Do not install Vitest, Oxlint, Oxfmt, tsdown, Vite, or Vite+ wrapper tools directly; Vite+ provides them.

## Forms (TanStack Form + Zod)

Use `@tanstack/react-form` with Zod (Standard Schema) for all forms. Key patterns:

- Pass the Zod schema to `validators: { onSubmit: mySchema }` on `useForm`.
- **Optional fields**: Zod's `z.string().optional()` produces an optional property type (`field?: string`). The `defaultValues` object must match exactly — use a type assertion to mark optional fields with `?`:
  ```tsx
  defaultValues: {
    name: "",
  } as { name: string; description?: string }
  ```
  Never use `field: undefined as string | undefined` — that creates a *required* property typed `string | undefined`, which is incompatible with `field?: string`.
- For optional Input controls, use `value={field.state.value ?? ""}` and `onChange={(e) => field.handleChange(e.target.value || undefined)}`.
- Do **not** use Zod `.default()` for setting initial values — set defaults in `defaultValues` instead. `.default()` changes the Zod input type to `T | undefined`, which causes Standard Schema type mismatches.
- For form-level submit errors, use `errorMap` not `errors` in `form.Subscribe`:
  ```tsx
  <form.Subscribe selector={(s) => ({ isSubmitting: s.isSubmitting, errorMap: s.errorMap })}>
    {({ isSubmitting, errorMap }) => errorMap.onSubmit ? <p>{String(errorMap.onSubmit)}</p> : null}
  </form.Subscribe>
  ```
- Use the shadcn `Field`, `FieldLabel`, `FieldError` components from `@/components/ui/field` (installed via `npx shadcn@latest add field`). Wrap them in `FieldGroup` from `@/components/field-group`.

## File Naming

- All TypeScript/TSX source files must use **kebab-case**: `my-component.tsx`, `agent-create-form.tsx`, `field-group.tsx`.
- Do **not** use PascalCase filenames (`MyComponent.tsx`) even for React components — name by the file, not the export.
- Schema files go in `src/schemas/` (e.g. `agent.ts`, `interface.ts`, `tool.ts`).
- Form components go in `src/components/forms/` with kebab-case names.

## Studio Client Defaults

For `apps/studio-client`:

- Read `apps/studio-client/AGENTS.md` before work.
- Prefer TanStack Router file routes under `src/routes`.
- Treat `src/routeTree.gen.ts` as generated. Do not hand-edit it unless there is no route generator available and the user specifically needs a temporary local fix.
- Keep UI consistent with existing shadcn-style components under `src/components/ui`, Tailwind classes, and `lucide-react` icons.
- Keep route and navigation changes accessible with real links or anchors rather than inert labels.
- For Monaco-backed Python completion providers, always trigger server completions in `import`/`from` statement contexts, including after whitespace; do not gate import suggestions solely on word, dot, parenthesis, or comma triggers.
- For repeated clickable card grids, always make both the link wrapper and card stretch to `h-full`, and add stable min-height/content caps so cards in the same dashboard row keep equal heights.
- For frontend UI changes, run a local server with `vp dev` when practical and verify the affected screen in the in-app Browser.

## Verification

Default verification for TypeScript/frontend changes:

```bash
vp check
vp test
```

Add these when relevant:

```bash
vp build
vp dev
```

Use `vp test <filters>` or local test filters only when the project supports them; otherwise run `vp test`.

If a `vp` command fails because dependencies are missing, run `vp install` if permitted by local instructions. If the failure appears sandbox or network related, request escalation for the same command.

If verification cannot run, report the exact command, failure reason, and which checks remain unverified.
