import type { MiddlewareHandler } from 'astro';

const BACKEND_URL = process.env.CENTAUR_API_URL || 'http://centaur-api.flycast:8000';

const SECURITY_HEADERS: Record<string, string> = {
  'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
  'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' https://avatars.githubusercontent.com data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
  'X-Frame-Options': 'DENY',
  'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
};

// Agent-readiness: explicit content-types for files Astro's static handler
// mis-detects (extensionless, or exotic types). Most of our agent-readiness
// files are served by Astro endpoints now — this covers remaining public/ files.
const CONTENT_TYPE_OVERRIDES: Record<string, string> = {
  '/.well-known/capabilities.yaml': 'application/yaml',
};

// Link header advertising machine-readable discovery endpoints (RFC 9727, llms.txt).
const ROOT_LINK_HEADER =
  '</.well-known/api-catalog>; rel="api-catalog", ' +
  '</llms.txt>; rel="alternate"; type="text/markdown", ' +
  '</llms-full.txt>; rel="alternate"; type="text/markdown"';

function addSecurityHeaders(response: Response): Response {
  const headers = new Headers(response.headers);
  for (const [key, value] of Object.entries(SECURITY_HEADERS)) {
    headers.set(key, value);
  }
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

export const onRequest: MiddlewareHandler = async (context, next) => {
  const url = new URL(context.request.url);

  // Agent-readiness: markdown content negotiation on /.
  // Agents sending Accept: text/markdown get rewritten to /llms-full.txt
  // (which is now a real Astro endpoint returning text/markdown).
  if (url.pathname === '/') {
    const accept = context.request.headers.get('accept') || '';
    if (/text\/markdown/i.test(accept)) {
      return context.rewrite('/llms-full.txt');
    }
  }

  if (url.pathname.startsWith('/api/')) {
    const target = `${BACKEND_URL}${url.pathname}${url.search}`;
    const headers = new Headers(context.request.headers);
    headers.delete('host');
    // Don't request compressed responses — let the outer server handle compression
    headers.delete('accept-encoding');

    const init: RequestInit = {
      method: context.request.method,
      headers,
      redirect: 'manual',
    };

    if (context.request.method !== 'GET' && context.request.method !== 'HEAD') {
      init.body = context.request.body;
      // @ts-ignore - duplex required for streaming request bodies
      init.duplex = 'half';
    }

    const response = await fetch(target, init);

    // Pass through response, stripping transfer/encoding headers that don't apply
    const respHeaders = new Headers(response.headers);
    respHeaders.delete('content-encoding');
    respHeaders.delete('transfer-encoding');

    return addSecurityHeaders(new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: respHeaders,
    }));
  }

  const response = await next();

  // Apply content-type overrides for agent-readiness files served by Astro's
  // static handler (which doesn't know about extensionless well-known URIs).
  const override = CONTENT_TYPE_OVERRIDES[url.pathname];
  const headers = new Headers(response.headers);
  if (override) {
    headers.set('Content-Type', override);
  }
  // Link header advertising api-catalog + llms.txt on /.
  if (url.pathname === '/') {
    headers.set('Link', ROOT_LINK_HEADER);
  }

  return addSecurityHeaders(new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  }));
};
