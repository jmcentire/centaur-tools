// Serve llms-full.txt as text/markdown.
import type { APIRoute } from 'astro';
import body from '../data/llms-full.md?raw';

export const GET: APIRoute = () =>
  new Response(body, {
    status: 200,
    headers: { 'Content-Type': 'text/markdown; charset=utf-8' },
  });
