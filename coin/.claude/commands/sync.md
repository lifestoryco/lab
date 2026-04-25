# SYNC — Rebase Worktree onto Latest Main

> **Preamble:** Git rebase utility. Fetch, check distance, rebase, report. Do not start any work after syncing — wait for user go-ahead.

Use this command when switching computers or when the worktree may be behind `origin/main`.

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
  # fix conflicts, then:
  git rebase --continue
```
And stop.

## Step 4 — Report what changed

```bash
git log --oneline HEAD~$BEHIND..HEAD
```

If `docs/state/project-state.md` exists, read the updated version to get fresh session context.

## Step 5 — Print summary

```
═══════════════════════════════════════════════
  Sync complete ✅
  Pulled $BEHIND commit(s) from origin/main
═══════════════════════════════════════════════
```

Then list notable changes pulled in (from commit messages).

## Rules

- Do NOT start work after syncing — wait for user go-ahead
- Do NOT force-push
- Do NOT auto-resolve code conflicts — only lockfiles and state files are safe to auto-resolve
- Report all conflicts clearly so the user can resolve them
