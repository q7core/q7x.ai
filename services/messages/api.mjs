import http from 'node:http';
import { createHash, timingSafeEqual } from 'node:crypto';
import { TextDecoder } from 'node:util';

const MAX_BODY = 65536;
const fail = (status, message) => { throw Object.assign(new Error(message), { status }); };
const digest = value => createHash('sha256').update(value).digest();

function boundedText(value, max, label) {
  if (typeof value !== 'string' || !value.trim() || value.includes('\0') || Buffer.byteLength(value) > max) {
    fail(400, `${label} must be nonempty text, at most ${max} UTF-8 bytes`);
  }
  return value;
}

function bookmark(value) {
  if (!/^(0|[1-9][0-9]{0,18})$/.test(value) || BigInt(value) > 9223372036854775807n) fail(400, 'invalid cursor');
  return value;
}

function queryOptions(params) {
  for (const key of params.keys()) {
    if (!['channel', 'limit', 'after', 'before'].includes(key) || params.getAll(key).length !== 1) fail(400, 'unknown or duplicate query parameter');
  }
  if (params.has('after') && params.has('before')) fail(400, 'use after or before, not both');
  const value = params.get('limit') ?? '50';
  if (!/^[1-9][0-9]{0,2}$/.test(value) || Number(value) > 100) fail(400, 'limit must be 1 to 100');
  return {
    channel: boundedText(params.get('channel') ?? 'general', 128, 'channel'),
    limit: Number(value),
    direction: params.has('after') ? 'forward' : 'backward',
    cursor: params.has('after') ? bookmark(params.get('after')) : params.has('before') ? bookmark(params.get('before')) : null,
  };
}

async function readBody(req) {
  if (!/^application\/json(?:\s*;|$)/i.test(req.headers['content-type'] ?? '')) fail(415, 'use application/json');
  if (req.headers['content-encoding'] && req.headers['content-encoding'] !== 'identity') fail(415, 'compressed request bodies are unsupported');
  if (Number(req.headers['content-length']) > MAX_BODY) fail(413, 'body exceeds 65536 bytes');
  // Keep the socket alive long enough to deliver a JSON error on chunked overflow.
  const raw = await new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on('data', chunk => {
      size += chunk.length;
      if (size > MAX_BODY) reject(Object.assign(new Error('body exceeds 65536 bytes'), { status: 413 }));
      else chunks.push(chunk);
    });
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
    req.on('aborted', () => reject(Object.assign(new Error('request aborted'), { status: 400 })));
  });
  try { return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(raw)); }
  catch { fail(400, 'invalid JSON or UTF-8'); }
}

export function createApi({ token, store, docs = '' }) {
  if (typeof token !== 'string' || token.length < 32) throw new Error('MESSAGES_TOKEN must contain at least 32 characters');
  const expected = digest(`Bearer ${token}`);
  const server = http.createServer({ maxHeaderSize: 8192, requestTimeout: 15000, headersTimeout: 10000 }, async (req, res) => {
    const send = (status, body) => {
      res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
      res.end(JSON.stringify(body));
    };
    try {
      if (req.url.length > 2048) fail(414, 'URL too long');
      const url = new URL(req.url, 'http://localhost');
      if (url.pathname === '/api/messages/docs' && req.method === 'GET') {
        res.writeHead(200, {'Content-Type':'text/plain; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});
        res.end(docs); return;
      }
      if (!timingSafeEqual(expected, digest(req.headers.authorization ?? ''))) {
        res.setHeader('WWW-Authenticate', 'Bearer'); fail(401, 'valid bearer token required');
      }
      if (url.pathname !== '/api/messages') fail(404, 'not found');
      if (req.method === 'GET') {
        const options = queryOptions(url.searchParams);
        const rows = await store.list({ ...options, limit: options.limit + 1 });
        const hasMore = rows.length > options.limit;
        const messages = rows.slice(0, options.limit);
        if (options.direction === 'backward') messages.reverse();
        send(200, {
          channel: options.channel, messages, direction: options.direction, has_more: hasMore,
          next_after: messages.at(-1)?.id ?? (options.direction === 'forward' ? options.cursor : '0'),
          next_before: messages[0]?.id ?? (options.direction === 'backward' ? options.cursor : null),
        });
      } else if (req.method === 'POST') {
        if (url.search) fail(400, 'POST uses JSON fields, not query parameters');
        const body = await readBody(req);
        if (!body || Array.isArray(body) || typeof body !== 'object' || Object.keys(body).some(x => !['sender','channel','text'].includes(x))) fail(400, 'expected sender, channel and text fields');
        const key = req.headers['idempotency-key'] ?? null;
        if (key !== null && !/^[A-Za-z0-9._:-]{1,128}$/.test(key)) fail(400, 'invalid Idempotency-Key');
        const message = await store.post({
          sender: boundedText(body.sender, 128, 'sender'),
          channel: boundedText(body.channel ?? 'general', 128, 'channel'),
          text: boundedText(body.text, 16384, 'text'), idempotency_key: key,
        });
        send(200, { message });
      } else { res.setHeader('Allow', 'GET, POST'); fail(405, 'method not allowed'); }
    } catch (error) {
      if (res.destroyed || res.headersSent) return;
      // No database messages, tokens, URLs, or message bodies enter logs/responses.
      if (error.status) send(error.status, {error:error.message});
      else if (error.code === '23505') send(409, {error:'Idempotency-Key already used with different content'});
      else if (['22021','22P02','23514','22023'].includes(error.code)) send(400, {error:'invalid message'});
      else { res.setHeader('Retry-After','2'); send(503, {error:'message storage temporarily unavailable'}); }
    }
  });
  server.setTimeout(15000, socket => socket.destroy());
  server.maxConnections = 128;
  return server;
}
