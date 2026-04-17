# centaur.tools — Full Context for AI Agents

> Community-governed registry for AI tools with provenance tracking and attribution.

## What It Is

centaur.tools is a community-governed registry for AI tools. Named after Kasparov's "centaur" concept — advanced chess where human and machine play together as partners. The registry exists so that when a platform ships something that looks like a prior community tool, the record exists.

The registry helps builders:
- find what's already been built
- discover who's working on similar problems
- preserve the incentives that keep independent builders building

## The Problem It Solves

The AI tools ecosystem has no citation norms. Platforms run opaque gatekeeping processes with misaligned incentives. Builders create tools; platforms ship similar features weeks later; there is no attribution infrastructure. The academic parallel — "you published first, you get the nod" — is a social contract that keeps people publishing. That contract is missing from the AI tools ecosystem.

Specific failure modes the registry addresses:
- Tools rejected from platform plugin directories despite strong user demand
- Tools subverted by platform features shipped shortly after community publication
- No mechanism for recognizing prior art or establishing provenance
- No community-owned discovery mechanism independent of platform gatekeepers

## Core Principles

- **Provenance**: Every tool carries its lineage. Forks link to parents. Overlapping problem spaces surface automatically.
- **Community Governance**: No gatekeepers. Usefulness votes from builders. Rotating moderation council.
- **Prior Art**: When a platform ships a feature an existing tool anticipated, the community flags it. The record is permanent.
- **MIT Only**: Everything is forkable. The only social contract is: cite your parents.

## Boundary Conditions

- MIT license only. No exceptions. Hard reject with explanation for non-MIT.
- No scores, rankings, featured lists, editor's picks, leaderboards.
- No single gatekeeper. Community governance with rotating council.
- GitHub OAuth only. No email/password.
- In-app notifications only. No email.
- Problem statement is the primary field for search and proximity, not description.
- Usefulness voting only. Not quality voting.
- Prior Art records are permanent once confirmed.
- Fork lineage is permanent and bidirectional.
- Founder (Jeremy McEntire) has structural veto for first 2 years, then transfers.

## Success Shape

Builders submit tools. On submission, they immediately see adjacent tools in their problem space — not as warnings, as introductions. "Three other centaurs are working on this. Here's who they are." When a platform ships a feature a week after a tool anticipated it, the community flags it as Prior Art. The record is permanent. The centaur was here first.

The forum is where builders coordinate. Categories for announcements, help, show-and-tell, and meta/governance. Tool pages have their own comment threads. Governance decisions happen in the open.

## Trust Model

- All reads are public and unauthenticated
- All mutations require GitHub OAuth
- Tool edits/deletes restricted to owner
- Moderation actions by rotating council (elected by vote)
- Moderation log is append-only and public
- Founder veto expires after 2 years

## Technical Stack

- Frontend: Astro + React + Tailwind CSS (SSR on Fly.io)
- Backend: Python FastAPI (separate Fly.io app)
- Database: PostgreSQL with pgvector extension (Fly.io managed)
- Embeddings: Gemini API (text-embedding-004)
- Auth: GitHub OAuth -> JWT in HttpOnly cookie
- Edge: nginx proxies /api/* to the backend service

## Public API Reference

Base URL: `https://centaur.tools/api`. All reads are public; mutations require GitHub OAuth (session cookie).

### Tools

- `GET /api/tools/` — list tools (params: `tag`, `page`, `per_page<=100`)
- `GET /api/tools/{slug}` — tool detail with provenance, forks, adjacent tools
- `POST /api/tools/` — submit a tool (auth required; MIT license required)
- `PATCH /api/tools/{slug}` — update (owner only)
- `DELETE /api/tools/{slug}` — deactivate (owner only)
- `POST /api/tools/{slug}/vote` — usefulness vote (auth)
- `DELETE /api/tools/{slug}/vote` — remove vote (auth)

### Search

- `GET /api/search/?q=...` — semantic + lexical search over the registry

### Users

- `GET /api/users/{username}` — public profile
- `PATCH /api/users/me` — update own profile (auth)
- `GET /api/users/me/data` — export own data (auth)
- `GET /api/users/me/starred` — starred tools (auth)
- `DELETE /api/users/me` — delete account (auth)

### Forum

- `GET /api/forum/categories` — list categories
- `GET /api/forum/categories/{slug}` — category with threads
- `GET /api/forum/threads/{thread_id}` — thread + replies
- `POST /api/forum/threads` — create thread (auth)
- `POST /api/forum/threads/{thread_id}/replies` — reply (auth)
- `PATCH /api/forum/replies/{reply_id}` — edit reply (auth, author only)
- `DELETE /api/forum/replies/{reply_id}` — delete reply (auth)
- `POST /api/forum/threads/{thread_id}/vote` — upvote thread (auth)

### Prior Art

- `GET /api/prior-art/` — confirmed records
- `GET /api/prior-art/pending` — open nominations
- `POST /api/prior-art/nominate` — nominate (auth)
- `POST /api/prior-art/{nomination_id}/vote` — council vote (auth, council only)

### Feed & Notifications

- `GET /api/feed/atom.xml` — public activity (Atom)
- `GET /api/notifications/` — user's notifications (auth)
- `GET /api/notifications/unread-count` — (auth)
- `POST /api/notifications/{notification_id}/read` — mark read (auth)
- `POST /api/notifications/read-all` — mark all read (auth)

### Auth

- `GET /api/auth/login` — start GitHub OAuth
- `GET /api/auth/callback` — OAuth callback
- `POST /api/auth/logout` — clear session
- `GET /api/auth/me` — current user

### Meta

- `GET /api/health` — liveness

Full machine-readable catalog: [/.well-known/api-catalog](https://centaur.tools/.well-known/api-catalog)
Full capabilities manifest: [/.well-known/capabilities.yaml](https://centaur.tools/.well-known/capabilities.yaml)

## Licensing and Attribution Policy

All registered tools must be MIT-licensed. Forks must cite parents. Prior Art nominations, once confirmed by the rotating council, are permanent and public. The moderation log is append-only.

## Links

- Website: https://centaur.tools
- Author: Jeremy McEntire (https://perardua.dev)
- Part of: Exemplar stack (https://exemplar.tools)
- Contact: jandrewmcentire@gmail.com
