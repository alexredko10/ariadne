# ADR 0003: State-First Agent Architecture

**Status:** Accepted

**Date:** 2026-06-19

## Context

Event-driven architectures create systems where behavior is distributed
across async callbacks, queue handlers, retry logic, hidden side effects,
and implicit state mutations.  For human developers this is already
difficult to debug, test, and audit.  For AI agents, it is exponentially
harder: agents need stable anchors, explicit entities, clear transition
rules, visible invariants, transaction boundaries, and testable checkpoints.

State-First architecture models software behaviour as:

```
State(t) → Transition(Command/Event) → State(t+1) → Verification
```

Not as:

```
Event handler → async side effect → callback → hidden mutation
```

UI / API / Report must be derived from state: `View = F(State)`.

If the UI is a pure function of state, agents can reason about behaviour
without simulating a timeline of asynchronous side effects.

## Decision

**Ariadne adopts State-First as the default architecture principle.**

### Core principle

```
Events at the boundary.  State at the core.
```

Events are not banned.  Events must produce a state projection before
agents reason about business behaviour.

### State-First definition

A module is State-First if:

1. Persistent facts live in an explicit State Store.
2. Algorithms are stateless except for temporary local variables.
3. All durable changes happen through named transitions.
4. Transitions have declared inputs, outputs, preconditions, postconditions,
   and invariants.
5. Events are treated as inputs to transitions, not as the primary logic
   model.
6. Every transition can be replayed, tested, logged, and verified.

### Transition graph model

```
Command / External Event
  → Input Validation
  → Transition Function
  → State Mutation
  → Invariant Check
  → State Snapshot / Trace
  → UI / API / Report = F(State)
```

### Annotation extensions

The existing `@ariadne-*` annotation system is extended with:

| Annotation              | Purpose                                      |
|-------------------------|----------------------------------------------|
| `@ariadne-state`        | Declare a persistent entity / state store    |
| `@ariadne-transition`   | Declare a named state transition             |
| `@ariadne-invariant`    | (reuse) Declare an invariant rule            |
| `@ariadne-register`     | Declare a read-only register / derived view  |
| `@ariadne-derived-view` | Declare a view function `View = F(State)`    |

### Agent rules

1. **Do not hide durable state inside algorithms.**
   If data must persist across requests or restarts, declare it as a
   StateEntity.

2. **Do not create implicit persistent state without declaring it.**
   File writes, database inserts, and external storage mutations must be
   registered as named transitions.

3. **Do not introduce async event chains when a state transition suffices.**
   If a synchronous transition can express the logic, prefer it over
   event cascades.

4. **Do not mutate state outside named transitions.**
   State mutations outside declared transitions are contract violations.

5. **Do not bypass invariant checks.**
   Invariant bypass is a CRITICAL severity contract violation.

6. **Do not implement business behaviour only as side effects.**
   Business logic must be traceable through explicit transitions.

7. **Prefer explicit transition functions with testable pre/postconditions.**
   Transitions are the unit of testing for state changes.

### Event exception policy

Events remain appropriate for:

- external integrations
- message queues
- notifications
- outbox patterns
- event sourcing
- audit streams
- cross-service propagation
- eventual consistency
- long-running sagas

**However:** If an event-driven subsystem has no state projection, it must
be marked as **HIGH RISK** for AI modification.

### State-First vs Event-Driven

| Property              | State-First                  | Event-Heavy                  |
|-----------------------|------------------------------|------------------------------|
| Debuggability         | High — inspect state after   | Low — trace async chain      |
| Testability           | High — test transitions      | Low — mock event bus         |
| Auditability          | High — state traces          | Low — distributed logs       |
| Agent reasoning       | Natural — explicit anchors   | Hard — hidden mutations      |
| Transaction boundary  | Declared                     | Implicit / missing           |
| Recovery              | Replay transitions           | Replay events with handling  |
| Invariant enforcement | Before/after transition      | Distributed / best effort    |

## Consequences

### Positive

- Agents operate on explicit state snapshots and transitions.
- Invariants are verifiable and testable.
- State traces enable audit and recovery.
- Easier to resume interrupted workflows.
- UI/API/Report derived from state (`View = F(State)`) is more testable.

### Negative

- Requires upfront state modelling effort.
- Event-driven subsystems need state projections before modification.
- Existing event-heavy codebases need gradual migration.
- Not suitable for all integration patterns.

## Relationship to existing contracts

- Model Gateway JWT contract is preserved.
- `apply-gate.schema.yml` is preserved.
- Existing `@ariadne-*` annotation system is extended, not replaced.
- `state_first_context` will become part of future TaskSubgraph output.
- No `state_core/` implementation in this PR.
- Events are not banned.

## Future work

- `state_model_extractor` — extract StateEntity definitions from source
- `transition_graph_builder` — build transition graph from `@ariadne-transition`
- `invariant_registry` — collect and verify invariants
- `state_trace_builder` — build state traces from transitions
- `event_to_state_folder` — project event streams into state snapshots
- `state_verifier` — verify state invariants automatically
- Artifact generation for: `state_model.json`, `transition_graph.json`,
  `invariant_registry.json`, `state_trace.json`
