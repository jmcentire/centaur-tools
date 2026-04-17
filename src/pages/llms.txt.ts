// Serve llms.txt as text/markdown (Astro's static handler would serve text/plain).
import type { APIRoute } from 'astro';
import body from '../data/llms.md?raw';

export const GET: APIRoute = () =>
  new Response(body, {
    status: 200,
    headers: { 'Content-Type': 'text/markdown; charset=utf-8' },
  });
