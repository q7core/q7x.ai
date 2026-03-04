import "dotenv/config";
import { Bot, Context } from "grammy";
import { spawn } from "child_process";
import Database from "better-sqlite3";
import path from "path";
import os from "os";
import { randomUUID } from "crypto";

// ── Config ────────────────────────────────────────────────────────────────────

const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN!;
const ALLOWED_USERS = (process.env.ALLOWED_USERS ?? "").split(",").map(Number);
const SQLITE_PATH = process.env.SQLITE_PATH ?? path.join(os.homedir(), ".q7x", "memory.db");
const AGENT_WORKSPACE = process.env.AGENT_WORKSPACE ?? path.join(os.homedir(), "q7x-workspace");
const MAX_BUDGET_USD = process.env.MAX_BUDGET_USD ?? "0.50";
const SESSION_TIMEOUT_MINUTES = parseInt(process.env.SESSION_TIMEOUT_MINUTES ?? "60");
const CLAUDE_BIN = path.join(os.homedir(), ".local", "bin", "claude");

if (!TELEGRAM_BOT_TOKEN) throw new Error("TELEGRAM_BOT_TOKEN is not set");
if (ALLOWED_USERS.length === 0) throw new Error("ALLOWED_USERS is not set");

// ── Database ──────────────────────────────────────────────────────────────────

import { mkdirSync } from "fs";
mkdirSync(AGENT_WORKSPACE, { recursive: true });
mkdirSync(path.dirname(SQLITE_PATH), { recursive: true });

const db = new Database(SQLITE_PATH);
db.exec(`
  CREATE TABLE IF NOT EXISTS sessions (
    chat_id    INTEGER PRIMARY KEY,
    session_id TEXT    NOT NULL,
    updated_at INTEGER NOT NULL
  );
`);

const getSession = db.prepare<[number], { session_id: string; updated_at: number }>(
  "SELECT session_id, updated_at FROM sessions WHERE chat_id = ?"
);
const upsertSession = db.prepare(
  "INSERT INTO sessions (chat_id, session_id, updated_at) VALUES (?, ?, ?) ON CONFLICT(chat_id) DO UPDATE SET session_id = excluded.session_id, updated_at = excluded.updated_at"
);
const deleteSession = db.prepare("DELETE FROM sessions WHERE chat_id = ?");

function getOrCreateSessionId(chatId: number): string {
  const row = getSession.get(chatId);
  const now = Date.now();
  if (row) {
    const ageMinutes = (now - row.updated_at) / 1000 / 60;
    if (ageMinutes < SESSION_TIMEOUT_MINUTES) {
      upsertSession.run(chatId, row.session_id, now);
      return row.session_id;
    }
  }
  const newId = randomUUID();
  upsertSession.run(chatId, newId, now);
  return newId;
}

// ── Claude (stdin pipe) ───────────────────────────────────────────────────────

function queryAgent(prompt: string, _sessionId: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const proc = spawn(
      CLAUDE_BIN,
      [
        "--print",
        "--output-format", "json",
        "--max-budget-usd", MAX_BUDGET_USD,
        "--add-dir", AGENT_WORKSPACE,
      ],
      {
        cwd: AGENT_WORKSPACE,
        env: { ...process.env, HOME: os.homedir(), PATH: `${path.join(os.homedir(), ".local", "bin")}:${process.env.PATH}` },
        timeout: 300_000,
      }
    );

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (d: Buffer) => { stdout += d.toString(); });
    proc.stderr.on("data", (d: Buffer) => { stderr += d.toString(); });

    proc.on("close", (code) => {
      if (stderr) console.error("[claude stderr]", stderr);
      if (code !== 0) {
        reject(new Error(`claude exited ${code}: ${stderr || "(no stderr)"}`));
        return;
      }
      try {
        const result = JSON.parse(stdout);
        resolve(result.result ?? result.response ?? JSON.stringify(result));
      } catch {
        resolve(stdout.trim() || "(empty response)");
      }
    });

    proc.on("error", reject);

    proc.stdin.write(prompt);
    proc.stdin.end();
  });
}

// ── Telegram helpers ──────────────────────────────────────────────────────────

const TELEGRAM_MAX = 4096;

async function sendChunked(ctx: Context, text: string): Promise<void> {
  if (text.length <= TELEGRAM_MAX) {
    await ctx.reply(text, { parse_mode: "Markdown" }).catch(() => ctx.reply(text));
    return;
  }
  for (let i = 0; i < text.length; i += TELEGRAM_MAX) {
    await ctx.reply(text.slice(i, i + TELEGRAM_MAX));
  }
}

// ── Bot ───────────────────────────────────────────────────────────────────────

const bot = new Bot(TELEGRAM_BOT_TOKEN);

bot.use(async (ctx, next) => {
  const userId = ctx.from?.id;
  if (!userId || !ALLOWED_USERS.includes(userId)) {
    await ctx.reply("Unauthorized.");
    return;
  }
  await next();
});

bot.command("start", (ctx) => ctx.reply("q7x online."));
bot.command("ping",  (ctx) => ctx.reply("pong"));

bot.command("new", async (ctx) => {
  deleteSession.run(ctx.chat.id);
  const newId = randomUUID();
  upsertSession.run(ctx.chat.id, newId, Date.now());
  await ctx.reply("New session started.");
});

bot.command("session", async (ctx) => {
  const row = getSession.get(ctx.chat.id);
  if (!row) {
    await ctx.reply("No active session.");
  } else {
    const age = Math.round((Date.now() - row.updated_at) / 1000 / 60);
    await ctx.reply(`Session: \`${row.session_id}\`\nAge: ${age}m`, { parse_mode: "Markdown" });
  }
});

bot.on("message:text", async (ctx) => {
  const chatId = ctx.chat.id;
  const text = ctx.message.text;
  const thinking = await ctx.reply("⏳");
  const sessionId = getOrCreateSessionId(chatId);

  try {
    const response = await queryAgent(text, sessionId);
    await ctx.api.deleteMessage(chatId, thinking.message_id);
    await sendChunked(ctx, response);
  } catch (err) {
    console.error("[agent error]", err);
    await ctx.api.deleteMessage(chatId, thinking.message_id);
    await ctx.reply(`⚠️ ${err instanceof Error ? err.message : String(err)}`);
  }
});

bot.catch((err) => console.error("Bot error:", err));
bot.start();
console.log("q7x agent started");
