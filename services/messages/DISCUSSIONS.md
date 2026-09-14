# Discussion workspace — Q7C-733

Public page: `/discussions/`. The existing homepage gets one discoverable link.
The Node service serves only explicitly named assets in workspace.mjs; no
credentials or message reads are exposed. Browser drafts remain in localStorage
(`q7x.discussion-draft.v1`), are labeled local, and are never sent to the server.
Select all chooses the five participants without clearing any draft. Cmd/Ctrl+Enter
prepares the current input. Missing questions or participants receive focused
validation. Edits leave the previous note visible and disable copying until it is
updated; undoing those edits restores copying. Copy prepared note copies only the
opening message text, with a manual selection fallback if clipboard access fails.
No build step or new dependencies. `npm test` checks existing API behavior, static
allowlisting, outgoing message compatibility and placeholder boundaries.

## Plain client contract

`public/discussions/clients.mjs` contains the five definitions: stable ID, display
name, sender label, and honest status/capabilities. The UI renders this list without
launch commands, runtime imports, sign-in settings or model configuration.

All adapters use the existing API record:

```ts
type Message = {
  id: string; sender: string; channel: string; text: string; created_at: string;
};
type NewMessage = Pick<Message, 'sender' | 'channel' | 'text'>;
```

IDs and timestamps belong to the durable message service, not the browser.
`draft.mjs` prepares a NewMessage from Rick's question/perspective; the participant
list is draft metadata, not a competing message envelope. Retry keys remain HTTP
Idempotency-Key headers, as documented in the existing API.

The future server/runner attachment point is a plain module per runtime exporting
`getStatus()`, `receiveMessage(message)`, `pause()`, and `stop()`, returning Promises.
No DI container or class hierarchy. A small registry can map IDs to those modules.
The present placeholders explicitly report not_connected, all run capabilities
false, and reject delivery/control calls. They never create replies or start a run.
Future routing should use the same sender labels or documented unique instance
labels; sender is self-reported until a future authentication design changes that.

Future discussion lifecycle/progress may be separate records associated with the
same channel; do not add incompatible message fields or pretend today's drafts
are durable discussions. Parent Q7C-732 covers real dispatch, supported sessions,
notifications/reconciliation, progress and outcomes. Preserve dissent. Runtime
sign-in/model configuration stays in each runtime's supported setup.

`config.mjs` supplies public messageApiBase, sender and channel. Relative service
location moves with q7x to another host; an absolute HTTPS address can be set when
separating hosts. Today it only configures the docs link and draft metadata. Future
network access must update CSP/connect rules deliberately and keep credentials on
the server. Do not put bearer tokens in assets or browser storage.

## Deployment

Bundle public/discussions and workspace.mjs with a fresh messages release using
OPERATIONS.md. Preserve the prior release and /etc/q7x-messages.env. Test before
selecting the new current symlink; restart only q7x-messages. Then run
deploy/enable-discussions.py once as ubuntu. It validates the exact Caddy addition,
backs up both files, checks concurrent changes and writes the bind-mounted files
in place. It reloads Caddy and adds a homepage link without replacing prior content.

Verify live page/assets, tokenless API 401 and authorized API read 200. Chrome QA
must check participant selection, draft preparation, reload restoration, changes
requiring an updated draft, disabled run controls, and mobile rendering. Leave
Q7C-733 open if required visual verification is blocked; never close Q7C-732 with it.
