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
  return addSecurityHeaders(response);
};
