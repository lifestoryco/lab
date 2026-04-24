---
description: Rebase onto origin/main before starting work. Use this after /start-session confirms environment is healthy.
---

# /sync

Pull latest and rebase. Run before starting any code changes.

```bash
git fetch origin
git rebase origin/main
```

If rebase conflicts:
1. Show the conflicting files
2. Resolve — prefer incoming if it's infrastructure, prefer local if it's domain logic
3. `git rebase --continue`
4. Report what was resolved

After clean rebase, print:
```
✅ Synced — HEAD: {short hash} | {n} commits ahead of origin/main
```
