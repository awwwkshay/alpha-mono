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

## Studio Client Defaults

For `apps/studio-client`:

- Read `apps/studio-client/AGENTS.md` before work.
- Prefer TanStack Router file routes under `src/routes`.
- Treat `src/routeTree.gen.ts` as generated. Do not hand-edit it unless there is no route generator available and the user specifically needs a temporary local fix.
- Keep UI consistent with existing shadcn-style components under `src/components/ui`, Tailwind classes, and `lucide-react` icons.
- Keep route and navigation changes accessible with real links or anchors rather than inert labels.
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
