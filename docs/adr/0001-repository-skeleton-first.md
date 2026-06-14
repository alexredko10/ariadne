# ADR 0001: Start with the repository skeleton

Date: 2026-06-14
Status: Accepted

## Context

The platform spans multiple services, shared contracts, documentation, frontend, infrastructure, and agent briefs. Starting with implementation before structure would create unclear ownership and inconsistent naming.

## Decision

The first development step is a Git repository skeleton with docs, services, packages, placeholder tests, and agent briefs.

## Consequences

Positive:

- clear module boundaries from day one
- safer parallel development
- easier onboarding
- better review discipline

Negative:

- no user-visible product feature is completed in the first commit
