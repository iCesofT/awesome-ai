---
name: ddd-strategic-design
description: Design DDD strategic artifacts including subdomains, bounded contexts, ubiquitous language, and context maps for complex business domains.
metadata:
  version: "1.2.0"
  domain: architecture
  triggers: DDD, Domain-Driven Design, strategic design, subdomain, bounded context, ubiquitous language, context map, anti-corruption layer, ACL
  role: architect
  scope: design
---

# DDD Strategic Design

Apply Domain-Driven Design strategic patterns to establish bounded contexts, classify subdomains, and define the relationships between them before writing a single line of code.

**Given:** a business domain description or existing system landscape.
**Produces:** subdomain classification, bounded context catalog, ubiquitous language glossary, and context map with integration patterns.

## When to Use

- Defining core, supporting, and generic subdomains at project start
- Splitting a monolith or service landscape along domain boundaries
- Aligning teams and ownership with bounded contexts
- Building a shared ubiquitous language with domain experts
- Designing context integration strategies (ACL, Shared Kernel, Open Host Service)

## When NOT to Use

- The domain model is stable and boundaries are already well established
- You need tactical code patterns only (use `architecture-patterns` instead)
- The task is purely infrastructure or UI oriented with no domain logic

---

## Step-by-Step Process

1. **Discover capabilities** — list everything the business does as verb-noun pairs (e.g., "manage orders", "process payments", "notify customers")
2. **Classify subdomains** — group capabilities by cohesion; label each as core, supporting, or generic
3. **Define bounded contexts** — draw consistency and ownership boundaries around each group; one team, one ubiquitous language
4. **Build the glossary** — for each context, list canonical terms, anti-terms (terms to avoid or qualify), and how they differ from adjacent contexts
5. **Map the context relationships** — identify integration patterns between contexts
6. **Capture decisions in ADRs** — record why boundaries were drawn where they were before implementation begins

---

## Subdomain Classification

| Type | Description | Strategy |
|------|-------------|----------|
| **Core** | Differentiates the business; highest competitive value | Build in-house, invest in DDD tactical patterns |
| **Supporting** | Enables core; not unique to the business | Build or buy, less design investment |
| **Generic** | Commodity; every business needs it | Buy off the shelf or use open source |

### Classification Table Template

| Capability | Subdomain | Type | Rationale |
|------------|-----------|------|-----------|
| Manage product catalog | Catalog | Core | Key differentiator in our marketplace |
| Process payments | Payments | Supporting | Important but follows industry standards |
| Send email notifications | Notifications | Generic | Use SendGrid / AWS SES |
| User authentication | Identity | Generic | Use Keycloak / Auth0 |
| Generate reports | Reporting | Supporting | Needed but not unique |

---

## Bounded Context Catalog Template

For each bounded context, document:

```markdown
## [Context Name]

**Team owner:** [team or squad]
**Type:** [core / supporting / generic]
**Description:** [one sentence — what this context knows and decides]

### Responsibilities
- [thing this context owns and decides]
- [thing this context owns and decides]

### NOT responsible for
- [explicitly out of scope — prevents scope creep]
- [explicitly out of scope]

### Key Aggregates
- `[AggregateRoot]` — [one-line purpose]

### APIs / Events exposed
- REST: `GET /products`, `POST /products`
- Event: `ProductCreated`, `ProductPriceUpdated`
```

### Example — E-Commerce Platform

#### Catalog Context

**Team owner:** Catalog squad  
**Type:** Core  
**Description:** Owns the definition, pricing, and lifecycle of products.

**Responsibilities:**
- Create and update product definitions and prices
- Manage product categories and attributes
- Publish `ProductCreated` / `ProductUpdated` / `ProductArchived` events

**NOT responsible for:**
- Stock levels (belongs to Inventory)
- Order line items (belongs to Orders)
- Customer-facing search ranking (belongs to Search)

**Key Aggregates:** `Product`, `Category`

#### Orders Context

**Team owner:** Orders squad  
**Type:** Core  
**Description:** Manages the full lifecycle of a customer order from cart to delivery confirmation.

**Responsibilities:**
- Create and mutate orders, apply discounts, confirm payment
- Publish `OrderPlaced`, `OrderShipped`, `OrderCancelled` events

**NOT responsible for:**
- Product details (reads a snapshot from Catalog at order time)
- Payment processing (delegates to Payments context)

**Key Aggregates:** `Order`, `OrderLine`

---

## Ubiquitous Language Glossary Template

| Term | Definition in this context | Anti-term / Confusion |
|------|----------------------------|-----------------------|
| `Product` | A catalog item with a price and status | Not an "item" or "article" — use "product" only |
| `Order` | A confirmed purchase with at least one line | Not a "cart" (that's a pre-order concept) |
| `Customer` | A registered user who has placed at least one order | Not a "user" in this context |
| `Price` | The amount charged at order time (snapshot, immutable) | Not the current catalog price which may change |

**Rules:**
- Every term in code (class names, field names, method names) must match the glossary
- If a concept appears in two contexts with different meanings, it MUST have different names
- Resolve ambiguities with domain experts before implementation

---

## Context Map — Integration Patterns

```
[Catalog] ──(published language)──► [Search]
[Catalog] ──(open host service)───► [Orders]
[Identity] ──(shared kernel)──────► [Orders]
[Orders] ──(anti-corruption layer)─► [Payments]   ← external payment gateway
[Orders] ──(conformist)────────────► [Shipping]   ← 3rd-party logistics API
```

### Integration Pattern Quick Reference

| Pattern | Use When | Impact |
|---------|----------|--------|
| **Shared Kernel** | Two contexts share a small, stable model | High coupling; coordinate releases |
| **Customer/Supplier** | Upstream team publishes, downstream consumes | Downstream depends on upstream roadmap |
| **Open Host Service** | Upstream exposes a stable public API | Loose coupling; upstream owns versioning |
| **Published Language** | Upstream defines a standard message schema | Very loose coupling; event-driven |
| **Anti-Corruption Layer (ACL)** | Integrating with external or legacy systems | Protects domain model from external noise |
| **Conformist** | Downstream must adapt to upstream with no negotiation | Accept external model as-is |

---

## Example Output — Commerce Domain

### Subdomain Map

```
Commerce Domain
├── Core
│   ├── Catalog        (product definitions, pricing)
│   ├── Orders         (order lifecycle, checkout)
│   └── Recommendations (personalized ranking — key differentiator)
├── Supporting
│   ├── Inventory      (stock levels, reservations)
│   ├── Promotions     (discount rules, coupon codes)
│   └── Reviews        (user-generated content)
└── Generic
    ├── Identity       (authentication, authorization) → use Keycloak
    ├── Notifications  (email, push, SMS) → use AWS SES + SNS
    └── Payments       (card processing) → use Stripe
```

### Context Relationships

```
Catalog ──[OHS]──► Orders
                    │
             [ACL]──┘──► Stripe (external)
Catalog ──[PL]───► Recommendations
Identity ──[SK]──► Orders
Inventory ──[C/S]──► Orders   ← Orders is downstream
```

---

## Required Artifacts

After running this skill, you should have:

- [ ] **Subdomain classification table** — every capability labelled core/supporting/generic
- [ ] **Bounded context catalog** — responsibilities, non-responsibilities, key aggregates per context
- [ ] **Ubiquitous language glossary** — canonical terms per context with anti-terms
- [ ] **Context map diagram** (text-based or drawn) — contexts and their integration patterns
- [ ] **ADRs** — one per significant boundary decision (e.g., why Payments is a generic subdomain)

---

## Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Anemic bounded contexts | Context only does CRUD, no domain logic | Look for business rules that belong there |
| Shared domain model | Two contexts import the same `User` entity | Each context defines its own representation |
| Too many generic subdomains | Building everything in-house | Re-evaluate; some things should be bought |
| Skipping the glossary | "Order" means different things to different teams | Define terms before writing code |
| Premature context splitting | Many tiny contexts with no clear boundary | Start coarse, split when friction emerges |

---

## Limitations

- This skill does not produce executable code; follow with `architecture-patterns` for tactical design
- It cannot infer business truth without stakeholder input — validate subdomain classification with domain experts
- Context boundaries must be confirmed in ADRs before implementation begins

---

## Related Skills

- `ddd-domain-expert` — Tactical DDD patterns: aggregates, value objects, repositories, domain events
- `architecture-patterns` — Clean Architecture and Hexagonal Architecture implementation
- `architecture-adrs` — Capture the boundary decisions as Architecture Decision Records
- `architecture-review` — Review an existing system against DDD strategic design principles
- `clean-ddd-hexagonal` — Apply DDD tactical patterns within a hexagonal architecture
