---
name: release
description: Bump version, run uv lock, write release notes from uncommitted git diff into README.md
trigger: /release
---

You are cutting a new release. The user will provide the version number (e.g. 1.26.9) as the argument, or ask you to determine it from context.

## Steps

1. **Determine version**: use the argument if provided; otherwise read `pyproject.toml` and increment the patch number.

2. **Bump version in `pyproject.toml`**: edit the `version = "…"` line.

3. **Run `uv lock`** to update the lock file.

4. **Investigate changes** by running `git diff HEAD` across all modified files. Read the diff carefully — do not guess.

5. **Write release notes**: prepend a `## Fork Changes (vX.Y.Z)` section to `README.md` (after the `---` separator that follows the intro, before the previous release section). Use the existing entries as style reference:
   - One bullet per logical change, not per file.
   - Lead with the user-visible feature name in **bold** (verb phrase), then a short explanation of what changed and why it matters.
   - Group related file changes into a single bullet.
   - Omit internal-only changes (settings.json, CLAUDE.md) unless they affect the user.

6. **Do not commit**. Report what was changed.

## Style rules
- Max ~15 bullets. Merge minor changes.
- No filler. Be concrete ("720 px tall, was 360 px") not vague ("improved").
- If a change is a bug fix, say "fix" not "improved stability".
