import { readFileSync } from 'node:fs';
import { createApi } from './api.mjs';
import { createPool, createStore } from './store.mjs';

const pool = createPool();
const server = createApi({ token:process.env.MESSAGES_TOKEN, store:createStore(pool), docs:readFileSync(new URL('./README.md', import.meta.url),'utf8') });
const port = Number(process.env.PORT ?? 3320);
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('invalid PORT');
try {
  await pool.query('SELECT id FROM ai_chat.messages LIMIT 0');
  server.listen(port, process.env.HOST ?? '127.0.0.1', () => console.log(`q7x messages listening on port ${port}`));
} catch {
  console.error('Message database startup check failed');
  await pool.end(); process.exitCode = 1;
}
let stopping = false;
for (const signal of ['SIGTERM','SIGINT']) process.on(signal, () => {
  if (stopping) return;
  stopping = true;
  const timer = setTimeout(() => process.exit(1), 15000).unref();
  server.close(async () => { await pool.end(); clearTimeout(timer); });
});
