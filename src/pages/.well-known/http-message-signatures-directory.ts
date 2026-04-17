// Web Bot Auth: HTTP Message Signatures directory. Empty list for now;
// advertises the endpoint so agent probes detect the discovery path.
import type { APIRoute } from 'astro';

const BODY = JSON.stringify({ signatures: { keys: [] } });

export const GET: APIRoute = () =>
  new Response(BODY, {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
