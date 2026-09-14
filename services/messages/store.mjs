import pg from 'pg';
import { readFileSync } from 'node:fs';

export function createPool(env = process.env) {
  if (!env.DATABASE_URL) throw new Error('DATABASE_URL is required');
  // TLS verification is mandatory. Do not allow URL options to override it.
  let url;
  try { url = new URL(env.DATABASE_URL); }
  catch { throw new Error('Invalid DATABASE_URL'); }
  if (!['postgres:','postgresql:'].includes(url.protocol)) throw new Error('Invalid DATABASE_URL protocol');
  if ([...url.searchParams].length) throw new Error('DATABASE_URL must not include query parameters; use PGSSLROOTCERT for TLS');
  const pool = new pg.Pool({
    connectionString: url.toString(), max: 5, connectionTimeoutMillis: 5000,
    idleTimeoutMillis: 30000, statement_timeout: 10000,
    ssl: { rejectUnauthorized: true, ca:readFileSync(env.PGSSLROOTCERT ?? new URL('./deploy/supabase-ca.crt', import.meta.url),'utf8') },
  });
  pool.on('error', () => console.error('Idle database connection failed'));
  return pool;
}

export function createStore(pool) {
  return {
    async post({sender, channel, text, idempotency_key}) {
      const { rows } = await pool.query('SELECT id::text, sender, channel, text, created_at FROM ai_chat.append_message($1,$2,$3,$4)', [sender, channel, text, idempotency_key]);
      return rows[0];
    },
    async list({channel, direction, cursor, limit}) {
      const forward = direction === 'forward';
      const { rows } = await pool.query(`SELECT m.id::text, sender, channel, text, created_at FROM ai_chat.messages AS m
        WHERE channel = $1 AND ($2::bigint IS NULL OR m.id ${forward ? '>' : '<'} $2::bigint)
        ORDER BY m.id ${forward ? 'ASC' : 'DESC'} LIMIT $3`, [channel, cursor, limit]);
      return rows;
    },
  };
}
