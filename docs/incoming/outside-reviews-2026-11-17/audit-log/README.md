# Audit log

The claude-code-skills session's records of its audits, kept off `main`. This is the same idea
as Platterpus's and the fork's `evidence` branches: a way to keep records and messages without
crowding the branch the reports live on.

`main` holds the reports each repository acts on. This branch holds what produced them and what
was learned from them:

- **`lessons/`:** what each repository, this session and the owner could do better, what worked
  together, and where the repositories differ without a written reason. One file per audit
  cycle, named by date.
- **`kit/audit/`:** the audit kit: the brief and in-repository prompt, `make-runs.sh`, the grading
  script `grade.py`, and the answer keys in `keys/`, each written before its run. Also each
  repository's state recorded before an audit (`pre-*-state.txt`) and the checking briefs
  (`verify-*.md`). The repository snapshots are left out: the state files name the commits to
  rebuild them from.
- **`kit/messages/`:** every prompt, review and message the session wrote for the owner to send
  to the repositories, as sent.

## Rules

- **Add files; don't edit or delete them,** as on `main`. A new cycle adds a new lessons file.
- **Never merged into `main`.** Commits only add to the previous tip.
- **No secrets,** as on `main`. Each addition is scanned before it's pushed.

Like `main`, this branch is private: it names the repositories and their findings.
