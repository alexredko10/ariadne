# Control Planes

## Trusted control plane

```text
Core
Conductor
Model Gateway
Repository Memory
Cache
Ledger
Policy Engine
```

## Semi-trusted execution plane

```text
Runner
```

The Runner may access the container runtime or sandbox backend, but it must not hold model provider credentials or repository push credentials.

## Untrusted execution plane

```text
Agent containers
```

Agent containers receive only scoped context and a sandbox filesystem. They do not receive canonical repository write access.
