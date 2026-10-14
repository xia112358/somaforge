# Repository cleanup scope

Current scope and verification commands are maintained in
[repository-maintenance.md](repository-maintenance.md).

The earlier WBT-only cleanup has completed. The workspace now includes Motion
Edit, Generator, Contact Solver, shared core and WBT. Retargeting tools and
third-party assets remain dependencies/reference material; they are not unused
merely because they are outside the main Python packages.

All cleanup preserves existing source changes, baseline snapshots and referenced
runtime artifacts. File removals require an enumerated approval and use the
system recycle bin. Never use a blanket `git clean`, discard untracked research,
or clear `tmp/` based solely on its name.
