# Climb00 compatibility package

Implementations now live in [`generator`](../generator/README.md),
[`contact_solver`](../contact_solver/README.md), and `somaforge_core`.
Old imports and `python -m climb00_pipeline.<module>` remain supported.
New code should use the canonical packages; WBT remains in `src/holosoma`.

Tests now live beside their canonical implementations in `generator/tests`,
`contact_solver/tests`, and `somaforge_core/tests`. This package contains no
independent model, solver or dataset implementation. Its aliases preserve module
identity for historical scripts and saved experiment reproduction.

Historical experiments and runtime contracts are indexed in
[repository maintenance](../../docs/repository-maintenance.md).
The [direct-infiller recipe](../../docs/climb00_direct_infiller_baseline.md) is a
historical experiment with protected external dependencies; it is not the current
training-data approval contract.
