// RFC 9727 API Catalog (linkset). Served as application/linkset+json so agent
// probes detect it as a linkset rather than Astro's default octet-stream.
import type { APIRoute } from 'astro';

const BODY = JSON.stringify({
  linkset: [
    {
      anchor: 'https://centaur.tools/',
      'service-desc': [
        {
          href: 'https://centaur.tools/.well-known/capabilities.yaml',
          type: 'application/yaml',
          title: 'centaur.tools capabilities manifest',
        },
      ],
      'service-doc': [
        {
          href: 'https://centaur.tools/llms-full.txt',
          type: 'text/markdown',
          title: 'centaur.tools — full context for AI agents',
        },
      ],
      item: [
        { href: 'https://centaur.tools/api/tools/', type: 'application/json', title: 'List tools' },
        { href: 'https://centaur.tools/api/search/', type: 'application/json', title: 'Search tools (semantic + lexical)' },
        { href: 'https://centaur.tools/api/forum/categories', type: 'application/json', title: 'Forum categories' },
        { href: 'https://centaur.tools/api/prior-art/', type: 'application/json', title: 'Confirmed prior art records' },
        { href: 'https://centaur.tools/api/feed/atom.xml', type: 'application/atom+xml', title: 'Public activity feed' },
        { href: 'https://centaur.tools/api/health', type: 'application/json', title: 'Health check' },
      ],
    },
  ],
});

export const GET: APIRoute = () =>
  new Response(BODY, {
    status: 200,
    headers: { 'Content-Type': 'application/linkset+json' },
  });
