# q7x project preflight

For meaningful implementation or infrastructure work, resolve the existing Linear
issue (or create one if none exists) and verify its title, project and state before
dispatching implementation or making changes. Reuse the matching issue; do not
create a duplicate. Include the verified issue link in the implementation record
and real verification evidence in its completion update.

Follow the existing workflow in
[/Users/rproemer/dev/claude-toolkit/skills/playbook/SKILL.md](/Users/rproemer/dev/claude-toolkit/skills/playbook/SKILL.md).
This preflight applies to q7x only. Direct task authorization continues to control
scope and execution; do not add routine approval checkpoints.

For the shared message API, read `services/messages/OPERATIONS.md` before changing
the schema or deploying. Keep unrelated services and business schemas untouched.

From the repository root, run message-service checks with
`npm --prefix services/messages test` (the root package has no test script).
Use an explicit working directory for file edits, and run `git diff --check`
separately so a later successful command cannot hide a failed check.
