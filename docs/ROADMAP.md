# AgriMesh Roadmap

## Phase 5 – Resource Economy & Monitoring (Complete)

- Resource economy engine with priority-based pool and preemption
- Agent bidding protocol with partial fulfilment and queuing
- Budget constraint enforcement with soft / hard thresholds
- Decision logger with SQLite persistence
- Real-time WebSocket monitoring for resource usage
- Frontend components for burn-down charts, resource monitor, and decision replay

## Phase 6 – Farm Profiles & Onboarding (In Progress)

- [x] Frontend farm profiles (local, per-browser via Zustand persist)
- [x] Farm onboarding wizard (location → area → basic config → description)
- [ ] Backend persistence for farm profiles (per-user accounts)
- [ ] Import / export farm profiles

## Phase 7 – IoT / Hardware Bridge (Planned)

- Adapters for pumps, valves, and soil moisture sensors
- Clear hardware abstraction layer for different field controllers
- Dry-run (simulation) mode vs live hardware mode
- Safety limits and manual override paths

## Phase 8 – Production Hardening (Planned)

- Authentication and authorization for the API
- Rate limiting and basic abuse protection
- Separate dev / staging / production environments
- Database migrations and backup strategy

## Phase 9 – Decision Explanation & Reporting (Planned)

- Rich explanation UI for agent decisions ("why" behind actions)
- Scenario comparison tooling (e.g. different budgets or crop mixes)
- Exportable reports (PDF / CSV) for farmers and stakeholders
