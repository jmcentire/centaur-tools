# centaur.tools

> Community-governed registry for AI tools with provenance tracking and attribution. Named after Kasparov's "centaur" concept — advanced chess where human and machine play together as partners.

centaur.tools exists so that when a platform ships something that looks like a prior community tool, the record exists. The registry helps builders find what's already been built, discover who's working on similar problems, and preserve the incentives that keep independent builders building.

## Core Principles

- **Provenance**: Every tool carries its lineage. Forks link to parents. Overlapping problem spaces surface automatically.
- **Community Governance**: No gatekeepers. Usefulness votes from builders. Rotating moderation council.
- **Prior Art**: When a platform ships a feature an existing tool anticipated, the community flags it. The record is permanent.
- **MIT Only**: Everything is forkable. The only social contract is: cite your parents.

## Key Pages

- [Explore tools](https://centaur.tools/explore): Browse the registry
- [Submit a tool](https://centaur.tools/submit): Add your tool (GitHub OAuth required)
- [Forum](https://centaur.tools/forum): Builder coordination and governance
- [Governance](https://centaur.tools/governance): Rotating council, prior art process
- [Dashboard](https://centaur.tools/dashboard): Your submissions and activity

## Public API

All reads are public. Base: `https://centaur.tools/api`

- `GET /api/tools/` — list tools (paginated)
- `GET /api/tools/{slug}` — tool detail
- `GET /api/search/?q=...` — semantic + lexical search
- `GET /api/users/{username}` — public profile
- `GET /api/forum/categories` — forum categories
- `GET /api/forum/threads/{thread_id}` — thread + replies
- `GET /api/prior-art/` — confirmed prior art records
- `GET /api/feed/atom.xml` — activity feed
- `GET /api/health` — liveness

Full API catalog: [/.well-known/api-catalog](https://centaur.tools/.well-known/api-catalog)
Full capabilities manifest: [/.well-known/capabilities.yaml](https://centaur.tools/.well-known/capabilities.yaml)

## Licensing

All registered tools are MIT-licensed. Hard reject for non-MIT.

## Links

- Website: https://centaur.tools
- Author: Jeremy McEntire (https://perardua.dev)
- Part of: Exemplar stack (https://exemplar.tools)
