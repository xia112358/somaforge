# Predictor execution gap interval

The predictor's ordinary CPU and GPU plan-realization loss uses
`-DEFAULT_ACCEPTANCE.shallow_penetration_m <= d <= actual includemargin`.
This is an optimization interval, not a new contact predicate. Newton's strict
activation test and allocation/primary-face checks remain authoritative;
zero loss at the upper boundary is not proof of contact.

The intended part/surface term penalizes `relu(d - includemargin)^2`, taking
the minimum over matching witnesses (one witness can establish a part's contact).
It no longer attracts inactive contacts toward `0.05 * includemargin`, and
does not switch based on frozen activation flags. Each witness uses its own margin.

The full-body term penalizes depth beyond the existing accepted penetration
tolerance, including other witnesses on the intended part and self collisions.
This is the lower interval bound; it is not added again to the intended-contact
term. Existing loss normalizations and aggregation settings are retained.
The optional body_mean_plus_max mode still provides its explicitly configured
additional per-body aggregation; the current training uses max.

Absent witnesses remain missing, not realized. Finite-face geometric guidance
approaches the configured margin's upper bound, clips negative normal residuals,
and retains tangential region guidance. Newton must re-query to establish truth.
The approach weight, pose prior, planner, acceptance criteria, physics margins,
assets, and standalone projector's legacy buffered mode are unchanged.

Regression tests cover upper/lower gradient signs, zero gradients inside the
interval, activation-flag independence, per-pair margins, missing-pair guidance,
and the scalar right-foot distance recorded at recursive step 2 (24.049 mm).
These are frozen-witness tests, not an end-to-end network recovery experiment.

The shared regional objective and Motion Edit's missing-region proxies also use
the actual `includemargin` upper bound (`native_activation_upper_gap_v1`). Their
penetration lower bound remains zero; this does not change the predictor's
existing shallow-penetration allowance. There is no regional 1 mm target mode.
