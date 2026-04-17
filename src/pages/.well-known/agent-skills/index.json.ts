// Agent Skills index (empty list).
import type { APIRoute } from 'astro';

const BODY = JSON.stringify({
  $schema: 'https://agentskills.io/schemas/v0.2.0.json',
  skills: [],
});

export const GET: APIRoute = () =>
  new Response(BODY, {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
