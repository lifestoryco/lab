---
description: Rebase the holo worktree onto latest origin/main. Use when switching machines or resuming after a break. Does NOT start any work — waits for go-ahead.
---

# /sync

Fetch, check distance from origin/main, rebase, report what changed.

---

## Step 1 — Fetch remote state

```bash
git fetch --all 2>&1
```

## Step 2 — Check how far behind

```bash
BEHIND=$(git rev-list HEAD..origin/main --count 2>/dev/null || echo "0")
echo "Behind by $BEHIND commit(s)"
git log --oneline HEAD..origin/main
```

## Step 3 — Decide & act

**If BEHIND = 0:** Print `✅ Already up to date with origin/main.` and stop.

**If BEHIND > 0:** Run:

```bash
git rebase origin/main
```

If the rebase succeeds, continue to Step 4.

If the rebase fails with conflicts, print:
```
❌ Rebase conflict — resolve manually:
  git status
  # fix conflicts in the listed files, then:
  git add <file>
  git rebase --continue
```
And stop. Do NOT auto-resolve conflicts in Python source files.
Safe to auto-resolve: `docs/state/project-state.md`, `docs/advisory-board/meetings/README.md`.

## Step 4 — Report what changed

```bash
git log --oneline HEAD~$BEHIND..HEAD
```

Read the updated `docs/state/project-state.md` to get fresh session context.

## Step 5 — Print summary

```
═══════════════════════════════════════════════
  Sync complete ✅
  Pulled $BEHIND commit(s) from origin/main
═══════════════════════════════════════════════
```

List notable changes pulled in (from commit messages, grouped by prefix: feat/fix/docs/test/chore).

Then: **wait for go-ahead before starting any work.**

## Rules

- Do NOT start work after syncing — wait for explicit go-ahead
- Do NOT force-push
- Do NOT auto-resolve conflicts in source files (api/, pokequant/, config.py, tests/)
- Report all conflicts clearly so the user can resolve them
