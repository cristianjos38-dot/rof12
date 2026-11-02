# ROF12 Git workflow

## Repository routing

- Official remote: `origin` → `https://github.com/cristianjos38-dot/rof12.git`
- Backup remote: `backup-gsgs01382-stack` → the original publication; never use it for delivery.
- Current branch: `master`
- GitHub account: `cristianjos38-dot`

The repository-local configuration sets `remote.pushDefault=origin`, `push.default=simple`, automatic upstream setup, rebased pulls and pruned fetches. The `git publish` alias expands to:

```bash
git push origin HEAD --follow-tags
```

## Validated milestone flow

1. Confirm the authorized phase and read the applicable `AGENTS.md` rules.
2. Inspect `git status`, remotes and current branch.
3. Implement only that phase; do not mix future-phase work.
4. Run `make check` and any phase-specific integration checks.
5. Scan the diff and tracked paths for `.env`, secrets, tokens, keys and private data.
6. Update the phase documentation with changes and test evidence.
7. Create a descriptive phase commit only after validation passes.
8. Run `git publish`; never use force push.
9. Verify local `HEAD` equals `origin/master` and verify any published tags.

## Safety rules

- The backup remote is preserved but is not a publication target.
- Do not rewrite history, alter commit dates, delete tags or change ownership.
- Do not publish incomplete functionality or failing tests.
- Use `git publish --dry-run` to validate routing without sending changes.

## Useful checks

```bash
gh auth status
gh api user --jq .login
git remote -v
git branch -vv
git status
git publish --dry-run
```

