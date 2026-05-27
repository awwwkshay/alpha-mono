# Requirements Gathering Guide

This file defines how to ask clarifying questions before planning a feature. Read it before Step 3 of the feature development workflow.

---

## Purpose

The goal of requirements gathering is to eliminate the decisions that would force a rewrite mid-implementation. You are not trying to gather every detail upfront — you are trying to identify the constraints that most affect the design. Ask only what you cannot reasonably infer from the request and the codebase.

---

## Before asking anything — do the codebase work first

Requirements questions must be informed by the code. Before composing any question:

1. Read the files that will be touched by this feature
2. Understand the existing interfaces, data models, and config schemas in scope
3. Identify what the feature plugs into, extends, or replaces
4. Note any patterns already established for similar functionality

Questions asked without this context will be too broad, too obvious, or already answered by the code. Do not ask about things you can determine by reading the files.

---

## What to ask about

Ask only in the categories that are genuinely ambiguous for this feature. Skip any category that is already clear.

### 1. Scope boundary

The single most important question. Establish exactly where this feature starts and stops.

- What is the entry point for this feature — who calls it and from where?
- What is the expected output — a return value, a side effect, both?
- Is there anything that looks related but is explicitly **not** part of this feature?
- Should this change any existing public interfaces, or only add new ones?

**Why this matters**: Scope creep is the main reason implementations balloon. An unclear boundary leads to changes in files that should not be touched.

### 2. Data and schemas

For any feature that introduces or modifies data structures:

- What are the exact fields, types, and constraints for new models?
- Are any fields optional? What are the defaults?
- Does any existing schema need to be extended, or should a new one be created?
- Will this data be serialised, persisted, or passed across a boundary (e.g. to an LLM, to a file)?

**Why this matters**: Changing a Pydantic schema after other code depends on it creates a cascade of fixes. Get the shape right before writing anything.

### 3. Integration with existing code

For any feature that extends or wraps something already in the codebase:

- Should this follow the existing pattern for similar things (e.g. new step type, new filesystem backend, new sandbox backend), or does it intentionally deviate?
- Does it need to be registered anywhere (e.g. a factory function, a config discriminator, an `__init__.py` export)?
- Will the existing tests for the code it touches still pass without modification?

**Why this matters**: The alpha-python codebase has established patterns (contracts, config-to-runtime factories, `__all__` exports). A feature that doesn't follow them creates inconsistency that is expensive to clean up.

### 4. Async and concurrency

For any feature that involves I/O or runs alongside other operations:

- Should this be `async def` or sync? (Default: async for anything that does I/O)
- Can multiple instances of this run concurrently, or must they be serialised?
- Are there shared resources (file handles, sandbox processes, LLM sessions) that need coordination?
- What is the timeout or cancellation behaviour?

**Why this matters**: Adding `async` to a sync function later cascades through all callers. Decide upfront.

### 5. Error handling

For any feature that can fail in more than one way:

- What are the distinct failure modes? (e.g. invalid input vs. external service failure vs. timeout)
- Should each failure mode raise a different exception type, or is one exception with a message sufficient?
- Should errors be caught and surfaced to the caller, or propagate up?
- Is partial success a valid outcome, or is this all-or-nothing?

**Why this matters**: Defining error types upfront determines whether callers can distinguish failures. Changing exception types after the fact is a breaking change.

### 6. Configuration

For any feature that introduces configurable behaviour:

- What parameters need to be configurable? What are the types and valid ranges?
- Should configuration be a new Pydantic model, or added to an existing one?
- Are there sensible defaults for all fields, or are some required?
- Does this configuration need to be validated at construction time (like `WorkflowConfig` does)?

**Why this matters**: Config shape is part of the public API. If it changes, all callers change.

### 7. Lifecycle and ownership

For any feature that owns resources (processes, connections, file handles):

- Who is responsible for setup and teardown?
- Should this implement the async context manager protocol (`__aenter__` / `__aexit__`)?
- What happens if teardown is not called (crash, signal)?

**Why this matters**: Resource leaks are hard to find after the fact. Ownership must be clear before implementation.

### 8. Testing requirements

For any feature where the test surface is non-obvious:

- Are there specific scenarios or edge cases that must have test coverage?
- Should tests use real I/O (integration tests) or mocked dependencies (unit tests)?
- Is there existing test infrastructure (fixtures, helpers) to reuse?

**Why this matters**: Writing tests after the fact often reveals that the code is structured in a way that makes testing hard. Knowing the test requirements shapes the implementation.

---

## How to ask questions

### Be specific, not open-ended

Vague questions produce vague answers. Reference the actual code.

```text
# Bad
How should errors be handled?

# Good
If execute_command times out, should LocalSandbox raise TimeoutError directly
or wrap it in a SandboxExecutionError? The current code raises TimeoutError —
should the new feature follow the same pattern?
```

### Show your assumption, ask for correction

This is faster than open-ended questions and surfaces your understanding for the user to validate.

```text
I'm assuming this should follow the same factory pattern as _build_filesystem
in workspace.py — a new config model (e.g. RedisConfig) that maps to a
new contract implementation. Is that right, or should this be wired up differently?
```

### Group questions by topic

Present questions in logical groups, not as a flat list of ten items. This makes it easier for the user to answer in context and spot gaps.

### Cap the question count

Aim for **3–6 questions** per feature. If you have more than 6 questions, you either have not read the codebase thoroughly enough, or the scope is too large and should be split.

If you find yourself writing more than 6 questions, stop and re-read the code. At least half of those questions are likely already answered.

---

## What not to ask

- **Things already answered by the request**: If the user said "add a Redis filesystem backend", don't ask "should this be a filesystem backend?".
- **Things already answered by the code**: If the codebase already has a pattern for registering backends, don't ask whether there should be a registration mechanism.
- **Style and formatting preferences**: These are defined in `python_code_style.md`. Never ask about naming conventions, line length, or import style.
- **Hypothetical future requirements**: Only ask about what is needed now. Do not ask "should this be extensible for future storage backends?" unless extensibility was mentioned.
- **Implementation details you can decide yourself**: If the choice does not affect the interface or the caller, make a decision and state it in the plan. Only escalate decisions that have externally visible consequences.

---

## Output of requirements gathering

Before writing the plan, you should be able to answer all of the following from the request, the codebase, and the user's answers:

- [ ] What is the exact scope boundary — what files will change, what will not?
- [ ] What are the data shapes (new models, modified fields)?
- [ ] How does this integrate with existing code — what does it plug into?
- [ ] Is it sync or async?
- [ ] What are the failure modes and how do they surface?
- [ ] What configuration does it need?
- [ ] Who owns setup and teardown (if applicable)?
- [ ] What must be tested?

If any of these is still unknown after asking questions, note it explicitly as an open question in the plan rather than making a silent assumption.
