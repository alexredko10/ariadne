# Ariadna Product Master Prompt Source

Source type: preserved uploaded strategic prompt.
Purpose: authoritative source artifact for PR 0137 Product Architecture Roadmap Unlock.
Status: source input, not implementation plan.

---

# Master Prompt for Ariadna Product / Lead Architect

You are the Product Architect and Lead System Architect for **Ariadna**.

Your task is to produce a roadmap-oriented architecture and product development proposal for Ariadna.

Do not skim the context diagonally. Read and integrate the whole conceptual direction.

Ariadna is not a chatbot wrapper.
Ariadna is not just an agent loop.
Ariadna is not only an IDE plugin.
Ariadna is not only GRACE, PCAM, or Rubrics.

Ariadna is a **runtime substrate for controlled AI-assisted software and business-process production**.

The product must combine:

```text
coding runtime
role-based agents
CLI-owned state
admissible proof references
context engineering
GRACE-style inline contracts
PCAM/PBS purpose decomposition
rubric-based evaluation
Decision Core
State-First architecture
visual phase gates
artifact workspace UI
model routing
human-in-the-loop control
```

Your job is to turn this into a coherent product roadmap.

---

# 1. Core Product Identity

Ariadna should be designed as a **runtime package + artifact workspace + agent orchestration substrate**.

The central idea:

```text
Agent may generate.
Runtime must verify.
Human owns the root purpose.
Artifacts make intermediate meaning visible.
```

Ariadna must not treat the LLM as the source of truth.

The source of truth is:

```text
runtime state
frozen acceptance criteria
admissible proof refs
context packs
state models
transition graphs
rubrics
verified artifacts
audit logs
human approvals
```

The model is replaceable.

The substrate is durable.

---

# 2. Product Philosophy

Use this as the main philosophy:

```text
Ariadna Context Core makes the project understandable.
State Core makes behavior traceable.
PCAM makes purpose explicit.
PBS decomposes purpose.
Decision Core compares hypotheses.
Rubrics make behavior verifiable.
Runtime CLI owns state and proof.
Artifacts make work controllable.
Model Router keeps models replaceable.
Human operator owns final meaning.
```

Ariadna should help operators control agents that can create specs, code, dashboards, ETL transformations, reports, tests, visualizations, and business artifacts at high speed.

The main danger is not that the agent cannot write code.

The main danger is that the agent writes a lot of plausible code/specs/artifacts that satisfy its own inferred assumptions rather than the real product purpose.

Therefore Ariadna must be built around:

```text
bounded phases
visual gates
runtime-captured proofs
independent review
drift detection
human approvals
```

---

# 3. Primary Workflow

The default Ariadna workflow for coding should be:

```text
Task
→ Specification
→ Visual Design / Diagrams
→ Implementation
→ Proof Collection
→ Independent Review
→ Fixes
→ Finalization
```

The default Ariadna workflow for business ETL / artifact-driven tasks should be:

```text
Task
→ Data Import
→ Diagnostic Artifact
→ Human Correction
→ Transformation
→ Visual Validation
→ OLAP / Dashboard Review
→ Report Generation
→ Final Approval
```

The important point:

Agents do not directly write trusted artifacts.

Agents propose.

Runtime CLI writes, captures, freezes, indexes, verifies, and accepts artifacts.

---

# 4. Runtime CLI as Source of Truth

Design Ariadna around a CLI/runtime package.

The runtime owns:

```text
run state
phase state
artifact registry
acceptance criteria
proof references
command captures
gate status
handoff packets
final reports
context cache
summary cache
```

Agents may request runtime commands, but only the runtime mutates trusted state.

Suggested commands:

```text
ariadna task init
ariadna spec draft
ariadna spec freeze
ariadna visual build
ariadna implement start
ariadna proof capture
ariadna proof search
ariadna gate check
ariadna review run
ariadna fix start
ariadna artifact open
ariadna artifact accept
ariadna state show
ariadna finalize
```

The runtime must enforce:

```text
no implementation before frozen criteria
no finalization without admissible proof refs
no gate transition without handoff packet
no root-purpose change without human approval
```

---

# 5. Admissible Proof References

Ariadna must distinguish agent claims from admissible evidence.

Agent output is not proof.

Accepted proof types:

```text
runtime-captured command output
runtime-captured test output
runtime-captured linter/type-check output
runtime-captured static analysis
bounded proof-search captures
runtime-accepted file refs
runtime-accepted diff refs
runtime-accepted data refs
runtime-accepted artifact refs
runtime-accepted state refs
```

Rejected proof types:

```text
agent says tests pass
agent summarizes terminal output without capture
uncaptured command output
stale session summary
LLM confidence
old markdown report
unbounded search claim
reference not tied to current product state
reference not tied to frozen acceptance criteria
```

Every proof ref must be tied to:

```text
run_id
phase_id
product_state_hash
acceptance_criteria_id
captured artifact path
timestamp
command/tool identity
```

Design a `proof_index.json` schema.

---

# 6. Cache and Summary Policy

Ariadna may maintain cache and summary files for recovery.

But:

```text
cache is not source of truth
summary is not proof
agent memory is not proof
previous run report is not proof
```

Cache helps resume interrupted work.

Final claims require current admissible proof refs.

Design:

```text
run_summary.md
phase_summary.md
context_cache.json
last_known_state.json
artifact_index.json
proof_index.json
```

But clearly mark summaries as non-authoritative.

---

# 7. Role-Based Agent Design

Separate roles by responsibility.

Do not design one omnipotent agent.

Suggested roles:

```text
Orchestrator
Specifier
Visual Architect
Decision Architect
Coder
Proof Collector
Reviewer
Fixer
Finalizer
Context Agent
Rubric Judge
Security Reviewer
Data/ETL Agent
Dashboard Agent
```

Role principles:

```text
Coder cannot be final reviewer.
Agent cannot notarize its own proof.
Reviewer must check proof admissibility.
Orchestrator routes phases but does not invent product truth.
Context Agent maintains context but cannot silently change Gold context.
```

Each role must receive a structured contract:

```json
{
  "run_id": "",
  "phase_id": "",
  "role": "",
  "purpose": {},
  "pbs_node": {},
  "frozen_acceptance_criteria": [],
  "context_pack": {},
  "state_model": {},
  "transition_graph": {},
  "rubric": {},
  "allowed_actions": [],
  "forbidden_actions": [],
  "stop_conditions": [],
  "required_outputs": []
}
```

---

# 8. PCAM / PBS Layer

PCAM means **Purpose-Centric Agent Methodology**.

PBS means **Purpose Breakdown Structure**.

Ariadna must not let agents execute from vague natural language.

User request should become:

```text
root purpose
business goal
technical goal
non-goals
constraints
risks
success definition
human approval triggers
purpose tree
local execution nodes
```

Design artifacts:

```text
purpose.json
pbs.json
non_goals.json
risk_policy.json
human_approval_policy.json
```

Every task, artifact, proof, rubric, and decision must reference a `purpose_id`.

Agents may propose purpose refinements, but may not silently change root purpose.

---

# 9. GRACE-Style Inline Contracts

Ariadna should use GRACE-style inline semantic contracts, but the product name remains Ariadna.

Core finding to incorporate:

Inline contracts near code are more useful to agents than detached MD session reports.

Reason:

```text
inline contracts are read together with code
external docs may be ignored
session MD files become historical snapshots
agents may treat stale session reports as current architecture
```

Design principle:

```text
Operational knowledge must live at the closest stable point to the thing it governs.
```

If a rule belongs to a function, put it near the function.

If it belongs to a transition, put it near the transition.

If it belongs to a domain, put it into Gold context with symbol/file bindings.

Ariadna anchors:

```text
@ariadna-domain auth
@ariadna-risk security
@ariadna-invariant auth.refresh_token.rotation.atomic
@ariadna-owner auth-session
@ariadna-state Invoice
@ariadna-transition invoice.post
@ariadna-register stock
@ariadna-derived-view invoice.total

@pcam-purpose preserve-session-security
@pcam-non-goal do-not-weaken-token-validation
@pcam-stop-condition request-human-approval-on-auth-semantics
```

Important empirical recommendations from GRACE A/B tests:

```text
1. Inline contracts help medium models more than frontier models.
2. Strong models may solve small codebases without visible gain, but inline contracts are almost free.
3. Value comes from passive reading near code, not necessarily grep navigation.
4. Agents rarely grep anchors unless primed.
5. Do not force anchor-first navigation; make it optional.
6. KEYWORDS should include domain words and symptom phrases from real tasks.
7. Put dense contracts in “logic traps” and counterintuitive code.
8. Full annotation is not always required; targeted annotation may preserve much of the value.
9. External injection of contracts helps architecture understanding but may hurt bug localization.
10. Contract sweep is useful for detecting drift between code and documentation.
```

Design modules:

```text
documentation_core/
  inline_anchor_extractor
  contract_linter
  contract_sweep
  stale_doc_detector
  doc_authority_classifier
  doc_to_gold_context_refiner
```

Session reports should be Bronze context, not authoritative Gold context.

---

# 10. Bronze / Silver / Gold Context Layer

Borrow the context-layer principle from GitHub Qubot-like architecture.

Ariadna must treat context as a production asset.

Context should be:

```text
versioned
owned
cached
invalidated
tested
reviewed
auditable
```

Use three levels.

## Bronze Context

Raw or historical data:

```text
raw files
raw docs
session reports
agent notes
logs
git history
scratchpads
temporary research notes
```

Bronze is not authoritative.

## Silver Context

Normalized machine-usable context:

```text
symbol index
file-symbol map
import graph
call graph
test graph
state candidates
transition candidates
context packs
semantic chunks
embeddings
recent-change clusters
```

## Gold Context

Curated trusted operational context:

```text
inline contracts
invariants
domain rules
state models
transition graphs
rubrics
routing policies
security rules
human approval triggers
stable prompt blocks
forbidden patterns
```

Gold context changes require review and context evals.

---

# 11. Ariadna Context Core

Design Ariadna Context Core as a first-class subsystem.

It must not be “top 10 similar chunks”.

It must produce structured context packs:

```json
{
  "context_pack_id": "",
  "purpose_id": "",
  "relevant_files": [],
  "relevant_symbols": [],
  "related_tests": [],
  "configs": [],
  "invariants": [],
  "state_entities": [],
  "transitions": [],
  "recent_changes": [],
  "risk_notes": [],
  "missing_context": [],
  "task_subgraph": {
    "nodes": [],
    "edges": []
  },
  "lineage": []
}
```

Context Compiler should answer:

```text
Which files matter?
Which symbols matter?
Which tests matter?
Which state entities matter?
Which transitions matter?
Which invariants matter?
Which policies matter?
What context is missing?
What should the agent not do?
```

---

# 12. Context Eval Framework

Every change to context or agent configuration must be tested.

Context evals should run when changing:

```text
context packs
anchors
invariants
state models
transition graphs
rubrics
stable prompt blocks
model routing rules
agent prompts
tool contracts
context compiler logic
```

Metrics:

```text
context recall
context precision
required invariant recall
required test recall
symbol recall
irrelevant context ratio
risk classification accuracy
token efficiency
latency
cost
regression count
```

Design:

```text
context_eval_case.json
context_eval_report.md
context_eval_baseline.json
```

Context is not documentation.

Context is infrastructure.

---

# 13. State-First Architecture

Ariadna should prefer State-First designs for business logic.

Core rule:

```text
Events at the boundary.
State at the core.
Transitions are the unit of change.
Invariants are the unit of safety.
State traces are the unit of verification.
```

Agents reason better when they see:

```text
State(t)
→ Transition(Command/Event)
→ State(t+1)
→ Verification
```

rather than hidden async event cascades.

State-First definition:

```text
1. Durable facts live in explicit state stores.
2. Algorithms are stateless except temporary local variables.
3. Durable changes happen through named transitions.
4. Transitions declare inputs, outputs, reads, writes, preconditions, postconditions, invariants.
5. Events are inputs to transitions, not the primary reasoning model.
6. Every transition can be replayed, logged, tested, and verified.
```

Artifacts:

```text
state_model.json
transition_graph.json
state_trace.json
invariant_registry.json
```

Event-driven systems are allowed, but must expose:

```text
state projection
transition graph
replay strategy
idempotency strategy
audit trace
```

Event-driven systems without state projection are high-risk for agent modification.

---

# 14. Rubrics as Rewards Runtime Layer

In MVP, Rubrics as Rewards are not real RL training.

They are runtime contracts and evaluation rules.

Rubrics define:

```text
essential criteria
important criteria
optional criteria
pitfalls
evidence requirements
stop conditions
related invariants
human approval triggers
```

Design:

```text
rubric_pack.json
rubric_judge_report.json
```

Rubric Judge output:

```json
{
  "purpose_id": "",
  "verdict": "pass | warning | fail | needs_human_review",
  "essential_passed": true,
  "important_passed": false,
  "pitfalls_triggered": [],
  "evidence_summary": "",
  "required_fixes": [],
  "human_approval_required": false
}
```

Rules:

```text
If essential fails, task is not complete.
If critical pitfall triggers, pipeline stops.
If evidence is insufficient, verdict is needs_human_review.
```

Future compatibility:

Runtime rubrics and judge reports may later become eval/training data for RL, GRPO/PPO-like optimization, or model selection.

---

# 15. Decision Core / GRM-Style Hypothesis Evaluation

Ariadna should not ask the model “what is the best answer?” directly.

Instead:

```text
Problem
→ Candidate Hypotheses
→ Generated Principles
→ Weighted Criteria
→ Critiques
→ Scores
→ Principle Sampling
→ Voting / Meta-Judge
→ Selected Decision
→ Execution Contract
```

This is inspired by GRM / Self-Principled Critique / reward-modeling style evaluation.

Decision Core is for runtime governance, not model training.

Artifacts:

```text
hypotheses.json
principle_pack.json
hypothesis_scores.json
decision_report.json
meta_judge_report.json
```

Use this especially for:

```text
architecture decisions
state-first vs event-driven choices
model routing
refactoring strategy
security-sensitive design
ETL transformation choices
UI artifact strategy
cost-quality tradeoffs
```

Meta-Judge should check:

```text
Were hypotheses diverse?
Were principles relevant?
Were weights reasonable?
Was one answer favored too early?
Were risks omitted?
Is human approval required?
```

---

# 16. Model Routing

Ariadna must support multi-model routing.

Do not hardcode:

```text
always Claude
always DeepSeek
always Gemini
always local SLM
```

Route by role, cost, risk, context stress, tool stability, and proof requirements.

Suggested role mapping:

```text
Architect / high-level reviewer:
  premium frontier model

Decision Core / principle sampling:
  strong reasoning model, possibly independent reviewer model

Worker coder:
  cheap coding LLM

Tester / proof collector:
  local SLM or cheap coding model

UI prototype:
  model strong in frontend/design taste

Verifier:
  deterministic tools + independent model

Final reviewer:
  different failure profile from coder
```

Important trend:

Small coding SLMs and NVFP4/local deployments may become very useful for:

```text
test generation
proof collection
boilerplate code
OpenAPI-based tests
local static checks
narrow coding tasks
```

But they should run inside Ariadna runtime where context, criteria, and proofs are system-owned.

SLM does not need to be universal intelligence.

It can be an excellent specialized executor.

Design:

```text
model_capability_profile.json
context_stress_profile.json
model_routing_report.json
cost_tracker.json
```

---

# 17. Long-Context and Vector Compression Rules

Ariadna should account for what LLMs store well in vector-like representations.

Easy for models:

```text
semantic concepts
references to learned concepts
custom concepts from context
relationships between concepts
summaries
approximate feature intensity
known textual patterns
```

Hard for models:

```text
exact quotes
rare identifiers
new names unlike training distribution
precise numbers beyond 2–3 digits
character-level details
```

Therefore Ariadna should not rely on raw long context.

Use:

```text
explicit anchors
symbol IDs
file-line refs
state IDs
transition IDs
exact proof refs
runtime-captured outputs
structured context packs
```

Long-context strategy:

```text
do not dump raw 100k tokens
compress into structured task subgraph
preserve exact references outside vectors
route exactness through runtime refs
```

---

# 18. Visual Gate / Mermaid Layer

Ariadna must include visual control before large code generation.

Reason:

Agents generate text and code faster than humans can read.

Human control must be visual, not only textual.

Use Mermaid as cheap bird’s-eye view.

Required visual artifacts depending on task:

```text
Requirement Diagram
Flowchart
Sequence Diagram
State Diagram
Class Diagram
ER Diagram
C4 / Architecture Diagram
Block Diagram
Kanban
Gantt
Mindmap
Timeline
Quadrant Chart
Radar Chart
Sankey
Packet Diagram
TreeView
```

Rule:

```text
If the agent cannot diagram the solution, it should not implement it.
If the human cannot understand the diagram in 2–3 minutes, implementation should not start.
```

Design:

```text
visual_artifacts/
  requirement_diagram.mmd
  state_diagram.mmd
  sequence_diagram.mmd
  architecture_diagram.mmd
  data_model.mmd
  risk_matrix.mmd
  implementation_kanban.mmd
  final_traceability.mmd
```

Visual Gate status:

```json
{
  "visual_gate": {
    "required": true,
    "required_diagrams": [
      "requirement",
      "state",
      "sequence",
      "architecture"
    ],
    "human_review_required": true,
    "status": "pending"
  }
}
```

Mermaid is not post-code documentation.

Mermaid is a phase gate before code.

---

# 19. Agent Progress Observatory

Long autonomous coding is unsafe without phase gates.

Use an observability layer.

Default policy:

```text
0–15 minutes:
  agent may work in sandbox/worktree

after 15 minutes:
  checkpoint required
  progress dashboard required
  drift check required

30+ minutes:
  allowed only with approved phase spec and bounded scope

2+ hours:
  allowed mainly for read-only diagnostics, tests, fuzzing, benchmarks, analysis

2+ hours with code-writing rights:
  forbidden without special human approval and phase gates
```

Design modules:

```text
observability/
  iteration_snapshot
  progress_dashboard
  drift_detector
  risk_heatmap
  phase_gate
  autonomy_budget
```

Artifacts:

```text
iteration_snapshot.json
progress_dashboard.md
requirement_drift_report.json
phase_gate_report.json
risk_heatmap.json
test_coverage_delta.json
context_delta.json
agent_decision_log.json
```

Key dashboard questions:

```text
What was the phase goal?
What did the agent actually do?
Which files changed?
How many lines changed?
Which entities appeared?
Which invariants were touched?
Which tests were added?
Which decisions did the agent make by itself?
Where did the agent drift from the spec?
Which risks increased?
What requires human approval?
```

---

# 20. Artifact Workspace UI

Ariadna’s UI should not be only chat.

Ariadna should use an **agent-driven artifact workspace**.

Core pattern:

```text
Chat = intent and dialogue
Runtime = state and execution
Artifacts = visual control and manual correction
Reports = audit and handoff
```

For ETL/ERP/business systems:

```text
User asks
→ agent runs runtime
→ runtime produces artifact
→ human validates/corrects
→ runtime stores accepted state
→ next transformation continues
```

Artifacts can include:

```text
folder picker
import error table
bar chart
pie chart
OLAP cube
mapping table
manual classification UI
WBS tree
Gantt chart
resource dashboard
boss dashboard
site report gallery
state transition view
proof view
Mermaid diagram viewer
```

Do not design artifacts as hallucinated UI.

Each artifact must be tied to:

```text
data_ref
state_ref
run_id
phase_id
source dataset
model/agent that proposed it
confidence
human edits
accepted/rejected status
```

---

# 21. Suggested Interface Borrowing

Borrow interface ideas from existing products, but adapt them to Ariadna.

## From Claude Artifacts / ChatGPT Canvas

Borrow:

```text
chat + artifact side-by-side
temporary generated UI
interactive review of generated outputs
artifact versioning
```

Ariadna adaptation:

```text
artifacts must be runtime-bound, not just generated HTML
each artifact has data refs, proof refs, and acceptance state
```

## From Claude Code / Cursor

Borrow:

```text
agentic coding workflow
tool calls
diffs
terminal outputs
subagents
permissions
worktrees
```

Ariadna adaptation:

```text
runtime owns artifacts and proof refs
agents cannot self-certify
phase gates are explicit
```

## From GitHub Qubot

Borrow:

```text
context layer
query/execution engine
markdown report in PR
offline eval framework
context as first-class asset
```

Ariadna adaptation:

```text
repository/context warehouse instead of data warehouse
coding/test/verifier engines instead of SQL engines
context evals for code tasks
```

## From Retool / Streamlit / Superset / Metabase / Power BI

Borrow:

```text
fast dashboards
tables
filters
charts
OLAP-like exploration
business artifact galleries
```

Ariadna adaptation:

```text
dashboards generated per phase and tied to runtime state
manual corrections become accepted state transitions
```

## From Linear / Jira / Trello / Kanban

Borrow:

```text
task states
phase boards
owners
progress visibility
```

Ariadna adaptation:

```text
Kanban is generated from PBS and phase gates, not manually maintained only
```

## From Mermaid / PlantUML / C4

Borrow:

```text
diagram-as-code
diffable visualizations
architecture diagrams
sequence/state/requirement diagrams
```

Ariadna adaptation:

```text
visual diagrams become gate artifacts, not decorative documentation
```

## From Palantir Foundry / Ontology-like systems

Borrow:

```text
semantic layer
operational objects
lineage
governed actions
data provenance
```

Ariadna adaptation:

```text
software project ontology:
files, symbols, states, transitions, invariants, tests, proofs, artifacts
```

---

# 22. Recommended Ariadna UI Layout

Design a 4-zone workspace.

## 1. Left Panel: Conversation and Run Timeline

Contains:

```text
operator chat
agent messages
phase timeline
runtime events
handoff notices
warnings
human approval requests
```

The chat is not the product.

The chat is the control channel.

## 2. Center Panel: Active Artifact Canvas

Shows the current artifact:

```text
Mermaid diagram
diff viewer
test report
OLAP cube
mapping table
Gantt chart
dashboard
folder picker
manual correction UI
proof report
```

Artifacts should be tabbed and versioned.

## 3. Right Panel: Runtime State / Gates / Proofs

Shows:

```text
current phase
acceptance criteria
gate status
proof refs
state hash
changed files
risk level
model routing
confidence/provenance
human approval requirements
```

This panel is crucial.

It prevents the UI from becoming just “pretty generated screens”.

## 4. Bottom Panel: Commands / Logs / Captures

Shows:

```text
runtime commands
captured test output
tool calls
CLI logs
proof capture output
warnings
replay links
```

This is where admissible evidence lives.

## Top Navigation

```text
Project
Run
Phase
Artifact Gallery
Context
State
Proofs
Reports
Settings
```

---

# 23. Artifact Gallery

Ariadna should provide a gallery of artifact templates.

Examples:

```text
Coding:
  requirement diagram
  architecture diagram
  state diagram
  sequence diagram
  diff review
  test report
  proof index
  risk heatmap

ETL / ERP:
  file import wizard
  anomaly table
  resource cost chart
  OLAP cube
  WBS tree
  Gantt chart
  mapping table
  boss dashboard
  site report

Agent Management:
  phase dashboard
  drift report
  model routing report
  context pack viewer
  rubric judge report
  autonomy budget monitor
```

The artifact gallery should be searchable by task type.

---

# 24. Construction Estimate ETL Use Case

Use this as a canonical product demo.

Scenario:

```text
construction estimates
→ import
→ detect broken positions
→ classify resources/operations
→ remove or correct low-value broken resources
→ build resource cost charts
→ build WBS
→ build preliminary Gantt
→ map estimate positions to WBS works
→ verify costs by WBS/resource/technology groups
→ manually correct concrete structure mapping by zones
→ recompute
→ OLAP check
→ boss dashboard
→ site reports
```

The UI should support this dialogue:

```text
operator asks for folder picker
runtime imports estimates
agent detects format errors
artifact shows broken resources and costs
operator removes low-value errors
runtime recomputes checksums
artifact shows resource distribution
agent builds WBS and Gantt
operator validates structure
agent maps estimate positions to works
OLAP cube checks mappings
operator manually fixes capture-zone mapping
runtime recomputes
boss dashboard generated
site reports generated
```

This use case demonstrates Ariadna’s key idea:

```text
The agent transforms data.
The human validates meaning.
Artifacts make intermediate meaning visible.
Runtime records accepted state.
```

---

# 25. Product Roadmap

Produce a staged roadmap.

## Phase 0: Product and Architecture Blueprint

Deliver:

```text
product vision
architecture principles
runtime ownership model
UI concept
artifact model
security model
roadmap
```

## Phase 1: Runtime CLI MVP

Deliver:

```text
run state
artifact registry
phase state
acceptance criteria freeze
proof capture
gate check
final report
```

## Phase 2: Artifact Workspace MVP

Deliver:

```text
chat + artifact canvas
artifact registry
Mermaid viewer
markdown report viewer
proof viewer
manual accept/reject
```

## Phase 3: Coding Runtime Flow

Deliver:

```text
task → spec → implementation → proof → review → fix → finalization
agent role contracts
independent review
proof refs
phase gates
```

## Phase 4: Ariadna Context Core

Deliver:

```text
symbol extraction
context packs
context cache
inline anchor extraction
Bronze/Silver/Gold context
context invalidation
context evals
```

## Phase 5: GRACE-Style Contracts

Deliver:

```text
inline contract schema
KEYWORDS/domain magnets
contract lint
contract sweep
logic trap annotation
doc authority classifier
```

## Phase 6: State Core

Deliver:

```text
state_model.json
transition_graph.json
state_trace.json
invariant_registry.json
state-first verifier
event-to-state projection policy
```

## Phase 7: PCAM/PBS

Deliver:

```text
purpose extractor
PBS builder
purpose.json
pbs.json
non-goals
human approval triggers
```

## Phase 8: Rubrics as Runtime Contracts

Deliver:

```text
rubric_pack.json
rubric generator
rubric judge
rubric_judge_report.json
pitfall stop logic
evidence requirements
```

## Phase 9: Decision Core

Deliver:

```text
hypothesis generator
principle generator
principle sampler
hypothesis scorer
voting engine
meta-judge
decision_report.json
```

## Phase 10: Model and Tool Router

Deliver:

```text
model capability profiles
context stress profiler
tool registry
tool permission model
model routing report
cost tracker
fallback policy
```

## Phase 11: Agent Progress Observatory

Deliver:

```text
15-minute checkpoints
iteration snapshots
progress dashboards
drift detector
risk heatmap
autonomy budget
```

## Phase 12: ETL / ERP Artifact Demo

Deliver canonical demo:

```text
construction estimate import
diagnostic artifact
resource charts
WBS artifact
Gantt artifact
mapping artifact
OLAP cube
boss dashboard
site reports
```

## Phase 13: Dataset / Eval Export

Deliver:

```text
execution trace export
rubric eval export
decision trace export
model routing performance logs
context eval baselines
failure case library
```

---

# 26. Security and Permissions

Ariadna must not give agents uncontrolled write access.

Rules:

```text
no production secrets
no Docker socket mount
no privileged containers
no silent CI/CD changes
no protected file changes without approval
no audit log deletion
no agent identity equal to human identity
```

Use:

```text
sandboxed worktrees
permissioned tools
runtime command logging
artifact lineage
human approval for high-risk actions
```

High-risk areas:

```text
auth
payments
permissions
PII
security policies
production configs
data deletion
state model changes
migration logic
```

---

# 27. Non-Goals

Do not design Ariadna as:

```text
one giant autonomous agent
a chatbot wrapper
a generic LangChain clone
a replacement for all IDEs
a model-specific Claude/Gemini/DeepSeek product
a system where agent claims equal proof
a system where markdown session reports are authoritative
a system that encourages overnight write-access coding without gates
```

---

# 28. Required Output From You

Produce a roadmap-oriented architecture proposal with:

```text
1. Product positioning.
2. Core architecture.
3. Runtime CLI design.
4. Artifact workspace UI design.
5. Role-based agent model.
6. Proof-ref model.
7. Context architecture.
8. GRACE-style inline contract strategy.
9. PCAM/PBS strategy.
10. State-First strategy.
11. Rubrics as Rewards runtime strategy.
12. Decision Core strategy.
13. Model routing strategy.
14. Visual gate strategy.
15. Observability/autonomy budget.
16. ETL/ERP artifact use case.
17. Approximate interface wireframe description.
18. Roadmap phases.
19. Risks and non-goals.
20. First 10 concrete implementation issues.
```

Do not produce generic advice.

Every recommendation must be tied to Ariadna’s product goal:

```text
controlled AI-assisted production with runtime-owned state, artifacts, proofs, context, and human-verifiable decisions.
```

---

# 29. First 10 Concrete Issues to Propose

At the end, propose the first 10 implementation issues.

They should likely include:

```text
1. Define Ariadna Runtime State schema.
2. Implement artifact registry.
3. Implement frozen acceptance criteria.
4. Implement proof_ref capture model.
5. Implement phase gate checker.
6. Implement Mermaid Visual Gate artifact.
7. Implement 4-panel Artifact Workspace UI prototype.
8. Implement inline anchor extractor.
9. Implement context_pack.json MVP.
10. Implement final_report.md generator.
```

Then propose the next 10 issues for Context Core, Rubrics, Decision Core, Model Router, and ETL demo.

---

# 30. Final Product Principle

Use this final product principle:

```text
Ariadna is not where the model thinks.
Ariadna is where the work becomes controllable.
```

Or:

```text
The agent generates.
The runtime captures.
The artifact visualizes.
The rubric evaluates.
The proof verifies.
The human approves.
```

Design everything around that.

