// Serve robots.txt as text/plain with explicit AI user-agent rules.
import type { APIRoute } from 'astro';
import body from '../data/robots.txt?raw';

export const GET: APIRoute = () =>
  new Response(body, {
    status: 200,
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
