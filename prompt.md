# centaur.tools — System Context

## What It Is

centaur.tools is a community-governed registry for AI tools with provenance tracking and attribution. Named after Kasparov's "centaur" concept — advanced chess where human and machine play together as partners. The registry exists so that when a platform ships something that looks like a prior community tool, the record exists.

## The Problem

The AI tools ecosystem has no citation norms. Platforms like Anthropic run opaque gatekeeping processes (/plugins) with misaligned incentives. Builders create tools, platforms ship similar features weeks later, and there's no attribution infrastructure. The academic parallel — "you published first, you get the nod" — is a social contract that keeps people publishing. This contract is entirely missing from the AI tools ecosystem.

Specific failure modes:
- Kindex was rejected from /plugins despite users calling it a game-changer
- Tools get subverted by platform features shipped shortly after community publication
- No mechanism for recognizing prior art or establishing provenance
- No community-owned discovery mechanism independent of platform gatekeepers

## Consequence Map

- **Proximity too aggressive** → noise, every tool "relates" to everything else, notifications become spam
- **Proximity too lax** → tools stay isolated, builders never discover adjacent work, the registry is just a list
- **Prior Art threshold too low** → gaming, frivolous claims, noise overwhelms signal
- **Prior Art threshold too high** → legitimate claims go unrecognized, the mechanism becomes useless
- **Fork lineage breaks** → the core attribution promise is violated, trust collapses
- **Governance concentrates** → becomes the thing it was built to replace
- **MIT-only rule relaxed** → forkability guarantee breaks, social contract fragments

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

Builders submit tools. On submission, they immediately see adjacent tools in their problem space — not as warnings, as introductions. "Three other centaurs are working on this. Here's who they are." When a platform ships auto mode a week after someone built signet-eval, the community flags it as Prior Art. The record is permanent. The centaur was here first.

The forum is where builders coordinate. Categories for announcements, help, show-and-tell, and meta/governance. Tool pages have their own comment threads. Governance decisions happen in the open.

## Trust Model

- All reads are public and unauthenticated
- All mutations require GitHub OAuth
- Tool edits/deletes restricted to owner
- Moderation actions by rotating council (elected by vote)
- Moderation log is append-only and public
- Founder veto expires after 2 years

## Technical Stack

- Frontend: Astro + React + Tailwind CSS (deployed as static to Fly.io via nginx)
- Backend: Python FastAPI (deployed to Fly.io as separate app)
- Database: PostgreSQL with pgvector extension (Fly.io managed)
- Embeddings: Gemini API (text-embedding-004)
- Auth: GitHub OAuth → JWT in HttpOnly cookie
- Two Fly.io apps: frontend (nginx) proxies /api/* to backend (FastAPI)
