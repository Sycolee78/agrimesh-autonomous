# System Overview — AgriMesh Autonomous

## Core Idea
Farm = physical layer
AgriMesh = Farm OS
Agents = decision services

Each agent runs a loop:
1. Observe state
2. Infer condition
3. Decide action
4. Execute/recommend action
5. Log outcomes
6. Learn/update policy (future phase)

## Phase Strategy
- **Phase 1:** Rule-based + deterministic simulation + optimization heuristics
- **Phase 2:** ML-enhanced predictions + policy tuning
- **Phase 3:** Reinforcement learning + multi-agent coordination

## Initial Agent Set
- Irrigation Agent (decision/action)
- Yield Forecast Agent (prediction + planning signal)

## Boundaries (critical)
- Agent outputs are explicit and typed
- Shared farm state is versioned
- No hidden side effects between agents
- Every decision must have an explanation payload

## Logging Contract
For each decision cycle, log:
- timestamp
- observed features
- chosen action
- confidence/explanation
- expected effect
- realized effect (when available)

## Why simulation-first
- Fast iteration
- Controlled testing
- Lower hardware dependency
- Better risk management before field deployment
