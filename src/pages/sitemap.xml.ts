// Serve sitemap.xml with application/xml content-type.
import type { APIRoute } from 'astro';
import body from '../data/sitemap.xml?raw';

export const GET: APIRoute = () =>
  new Response(body, {
    status: 200,
    headers: { 'Content-Type': 'application/xml; charset=utf-8' },
  });
