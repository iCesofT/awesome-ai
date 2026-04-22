# awesome-ai

A curated collection of AI agents and skills for the full software development lifecycle. Designed to be used with AI-powered development tools (Claude Code, Cursor, Copilot, etc.), each agent and skill provides structured, unambiguous guidance that AI assistants can follow precisely.

---

## Overview

| Category | Count | Description |
|---|---|---|
| Agents | 13 | Role-based AI agents for specialized engineering tasks |
| Agent Skills | 19 | Focused reference patterns used inside agents |
| Lifecycle Skills | 59 | Phase-organized skills from planning to deployment |

---

## Agents

Agents are self-contained prompt definitions that give an AI assistant a specialized role, workflow, and quality standards.

### ADR Generator
**File:** `agents/adr-generator.agent.md`

Produces structured Architectural Decision Records (ADRs). Generates numbered markdown files under `/docs/adr/` with front matter, context, decision rationale, consequences, alternatives considered, implementation notes, and references. Includes a 13-point quality checklist.

### API Architect
**File:** `agents/api-architect.agent.md`

Designs and implements API connectivity layers. Takes a target language, endpoint URL, DTOs, and REST methods as input and returns full working code (no templates) organized in a three-layer architecture: service, manager, and resilience. Supports circuit breaker, bulkhead, throttling, and retry/backoff configuration.

### Context Architect
**File:** `agents/context-architect.agent.md`

Maps all files affected by a planned change before implementation begins. Produces a context map listing primary files, secondary/dependency files, test coverage, relevant patterns, and a suggested implementation sequence to avoid cascading surprises.

### Modernization Agent
**File:** `agents/modernization.agent.md`

Guides a human-in-the-loop full project modernization. Supports any stack (.NET, Java, Python, Node.js, Go, PHP, Ruby, etc.). Runs a 9-step process from stack identification through technology selection to implementation planning. Produces per-feature documentation, technology recommendations, and a master README under a `/modernizedone/` output structure.

### PostgreSQL DBA
**File:** `agents/postgresql-dba.agent.md`

Manages and maintains PostgreSQL databases. Handles schema creation, query optimization, backups/restores, performance monitoring, and security. Requires the `ms-ossdata.vscode-pgsql` VS Code extension.

### Principal Software Engineer
**File:** `agents/principal-software-engineer.agent.md`

Provides expert-level engineering guidance modeled after Martin Fowler's approach. Balances craft excellence with pragmatic delivery. Covers requirements analysis, implementation with GoF patterns, SOLID/DRY/YAGNI/KISS principles, clean code, test automation, and technical debt management (logged as GitHub Issues).

### Prompt Builder
**File:** `agents/prompt-builder.agent.md`

Engineers and validates high-quality prompts through systematic improvement cycles. Operates in two personas — Prompt Builder (creates/improves) and Prompt Tester (validates) — running up to three research/test/improve cycles. Enforces imperative language, specificity, logical flow, and evidence-backed content.

### Prompt Engineer
**File:** `agents/prompt-engineer.agent.md`

Analyzes and restructures existing prompts. Evaluates simplicity, chain-of-thought, structure, examples, complexity, specificity, and prioritization. Returns a detailed reasoning analysis followed by the full improved prompt verbatim.

### QA Subagent
**File:** `agents/qa-subagent.agent.md`

Operates under the philosophy "assume it's broken until proven otherwise." Produces a test plan covering happy path, boundary, negative, error handling, concurrency, and security cases. Runs exploratory testing and delivers a structured findings report.

### Software Engineer Agent v1
**File:** `agents/software-engineer-agent-v1.agent.md`

Delivers production-ready code with zero-confirmation autonomous execution. Follows the testing pyramid (many unit → focused integration → few E2E). Process: Analyze → Design → Implement → Validate → Reflect → Handoff. Enforces SOLID, clean code, and comprehensive quality gates throughout.

### Specification
**File:** `agents/specification.agent.md`

Generates or updates AI-ready specification documents. Output is precise and unambiguous markdown saved under `/spec/` as `spec-[category]-[name].md`. Sections include: purpose/scope, definitions, requirements, interfaces, acceptance criteria, testing strategy, rationale, dependencies, examples, and validation criteria.

### Tech Debt Remediation Plan
**File:** `agents/tech-debt-remediation-plan.agent.md`

Produces a comprehensive technical debt analysis and remediation plan (analysis only — no code changes). Scores each item on ease of remediation (1–5), impact (1–5), and risk (low/medium/high). Outputs a summary table plus detailed plans for missing test coverage, outdated docs, poor modularity, and deprecated dependencies.

---

## Agent Skills

Focused reference guides packaged inside the `agents/skills/` directory for use within agent prompts.

| Skill | Purpose |
|---|---|
| `api-design-principles` | REST and GraphQL API design patterns |
| `architecture-designer` | High-level system architecture and ADR creation |
| `architecture-patterns` | Clean Architecture, Hexagonal Architecture, DDD |
| `backend-architect` | Scalable API design, microservices, distributed systems |
| `bdd-patterns` | Behavior-driven development with Given-When-Then |
| `clean-ddd-hexagonal` | Combined DDD + Clean Architecture + Hexagonal tactical guidance |
| `conventional-commit` | Structured commit message format (type, scope, description) |
| `database-optimizer` | Query optimization, index strategies, execution plan analysis (PostgreSQL/MySQL) |
| `ddd-domain-expert` | Strategic and tactical DDD for complex domains |
| `ddd-strategic-design` | Bounded contexts, subdomains, ubiquitous language |
| `error-handling-patterns` | Exception handling, Result types, error propagation, graceful degradation |
| `java-architect` | Enterprise Java with Spring Boot 3.x, microservices, reactive programming |
| `java-springboot` | Spring Boot best practices |
| `microservices-patterns` | Service boundaries, event-driven communication, resilience patterns |
| `multi-stage-dockerfile` | Optimized Docker multi-stage builds |
| `openapi-spec-generation` | OpenAPI 3.1 spec generation and validation |
| `sql-optimization` | SQL performance tuning across MySQL, PostgreSQL, SQL Server, Oracle |
| `sql-optimization-patterns` | Query optimization, indexing, EXPLAIN analysis |
| `spring-boot-engineer` | Spring Boot 3.x controllers, security, JPA, WebFlux |

---

## Lifecycle Skills

The `skills/` directory contains 59 skills organized by development phase. Each skill is a standalone folder with its own prompt definition, reference material, and examples.

### Phase 01 — Planning & Specification

| Skill | Description |
|---|---|
| `01-planning-architecture-adrs` | Create and maintain Architectural Decision Records |
| `01-planning-architecture-patterns` | Select and apply architectural patterns |
| `01-planning-architecture-review` | Review existing architecture for gaps and risks |
| `01-planning-backend-patterns` | Identify appropriate backend patterns for requirements |
| `01-planning-create-specification` | Author structured functional specifications |
| `01-planning-ddd-domain-expert` | Apply DDD principles to model a domain |
| `01-planning-ddd-strategic-design` | Define bounded contexts and subdomains |
| `01-planning-openapi-spec-generation` | Generate OpenAPI 3.1 specifications |
| `01-planning-spec-driven-development` | Drive implementation from a written specification |

### Phase 02 — Design & Architecture

| Skill | Description |
|---|---|
| `02-design-api-design` | Design RESTful and GraphQL APIs |
| `02-design-clean-code` | Apply clean code principles to existing code |
| `02-design-clean-ddd-hexagonal` | Combine Clean Architecture, DDD, and Hexagonal patterns |
| `02-design-code-review-and-quality` | Conduct thorough code reviews |
| `02-design-coding-standards` | Establish and enforce coding standards |
| `02-design-design-patterns` | Apply GoF and enterprise design patterns |
| `02-design-grpc-design` | Design gRPC services and protobuf schemas |
| `02-design-solid-principles` | Apply SOLID principles to object-oriented code |

### Phase 03 — Development & Implementation

| Skill | Description |
|---|---|
| `03-development-caching-patterns` | Implement caching strategies (local, distributed, CDN) |
| `03-development-code-simplification` | Simplify and reduce complexity in existing code |
| `03-development-concurrency-review` | Identify and fix concurrency issues |
| `03-development-conventional-commit` | Write structured git commit messages |
| `03-development-debugging-and-error-recovery` | Debug and recover from errors systematically |
| `03-development-error-handling-patterns` | Implement robust error handling |
| `03-development-git-commit` | Manage git workflow and branching |
| `03-development-java-development` | Java best practices and idiomatic code |
| `03-development-java-sensitive-log-auditor` | Audit Java logs and exception messages to prevent sensitive data leakage |
| `03-development-jpa-patterns` | JPA and Hibernate patterns and optimization |
| `03-development-logging-patterns` | Implement structured and contextual logging |
| `03-development-maven-dependency-audit` | Audit and update Maven dependencies |
| `03-development-spring-boot` | Spring Boot development best practices |
| `03-development-sql-code-review` | Review SQL for correctness and performance |
| `03-development-sql-optimization` | Optimize slow SQL queries |

### Phase 04 — Testing & Validation

| Skill | Description |
|---|---|
| `04-testing-bdd-patterns` | Write BDD scenarios with Given-When-Then |
| `04-testing-debugging-and-error-recovery` | Debug failing tests and flaky test suites |
| `04-testing-e2e-testing` | Design and implement end-to-end tests |
| `04-testing-spring-boot-testing` | Unit and integration testing for Spring Boot |
| `04-testing-test-driven-development` | Apply red-green-refactor TDD cycle |
| `04-testing-test-quality` | Assess and improve test suite quality |

### Phase 05 — Deployment & Operations

| Skill | Description |
|---|---|
| `05-deployment-changelog-generator` | Generate structured changelogs from git history |
| `05-deployment-deployment-patterns` | Apply blue/green, canary, and rolling deployment patterns |
| `05-deployment-gdpr-compliant` | Audit code and data flows for GDPR compliance |
| `05-deployment-liquibase` | Manage database schema migrations with Liquibase |
| `05-deployment-logging-patterns` | Configure production-grade logging and log aggregation |
| `05-deployment-multi-stage-dockerfile` | Build optimized multi-stage Docker images |
| `05-deployment-observability` | Implement metrics, tracing, and alerting |
| `05-deployment-performance-optimization` | Profile and optimize application performance |
| `05-deployment-performance-smell-detection` | Detect performance anti-patterns in code |
| `05-deployment-security-audit` | Audit code and infrastructure for security vulnerabilities |
| `05-deployment-springboot-security` | Harden Spring Boot applications |

---

## Design Philosophy

- **AI-ready:** All content uses structured, unambiguous, machine-parseable formats.
- **Language-agnostic core:** Most skills work across Go, Rust, Python, TypeScript, Java, and C#.
- **DDD-centric:** Domain-Driven Design patterns are deeply integrated throughout.
- **Working code only:** Agents produce full implementations, never placeholder templates.
- **Security by design:** Security and GDPR compliance are first-class concerns, not afterthoughts.
- **Observable systems:** Structured logging, distributed tracing, and alerting are built into deployment skills.

---

## Contributing

1. Place new agents under `agents/` as `<name>.agent.md`.
2. Place skills specific to agents under `agents/skills/`.
3. Place standalone lifecycle skills under `skills/<phase>-<name>/`.
4. Follow the existing frontmatter and section structure so AI tools can parse them consistently.
