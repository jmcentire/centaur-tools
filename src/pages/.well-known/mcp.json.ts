// MCP Server Card: advertises the Centaur read-only HTTP API as a tool
// surface for agents that speak MCP's server-card discovery format.
import type { APIRoute } from 'astro';

const BODY = JSON.stringify({
  name: 'centaur.tools',
  description: 'Community registry for AI tools. Read-only public endpoints for search, listing, prior-art, forum, and feed.',
  version: '1.0.0',
  homepage: 'https://centaur.tools',
  transport: { type: 'http', base: 'https://centaur.tools/api/' },
  tools: [
    {
      name: 'search_tools',
      description: 'Search the Centaur AI tools registry (semantic + lexical).',
      endpoint: 'https://centaur.tools/api/search/',
      method: 'GET',
      inputSchema: {
        type: 'object',
        properties: { q: { type: 'string', description: 'Search query' } },
        required: ['q'],
      },
    },
    {
      name: 'list_tools',
      description: 'List registered AI tools with pagination.',
      endpoint: 'https://centaur.tools/api/tools/',
      method: 'GET',
    },
    {
      name: 'prior_art',
      description: 'Confirmed prior-art records attached to tools.',
      endpoint: 'https://centaur.tools/api/prior-art/',
      method: 'GET',
    },
    {
      name: 'forum_categories',
      description: 'List forum categories for cross-tool discussion.',
      endpoint: 'https://centaur.tools/api/forum/categories',
      method: 'GET',
    },
    {
      name: 'activity_feed',
      description: 'Public activity feed (Atom).',
      endpoint: 'https://centaur.tools/api/feed/atom.xml',
      method: 'GET',
    },
  ],
});

export const GET: APIRoute = () =>
  new Response(BODY, {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
