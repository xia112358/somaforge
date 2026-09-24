#!/usr/bin/env bash
set -eo pipefail
source scripts/source_isaaclab3_newton_setup.sh
set -u
root=tmp/full1000_regionfix5000_20260925
common=(--headless --device cuda:0 --mode full --gpu-pipeline --query-worlds 32
  --batch-size 128 --learning-rate .0003 --seed 20260917
  --region-plan --unified-contact --event-roles --consistent-event-roles
  --no-recover-failed-states --no-pending-plan-repair --no-relative-plan-supervision
  --reuse-fk --defer-statistics --no-profile-components --no-compile-fk --no-compile-modules
  --stage-a-checkpoint tmp/conditioned_pose_stage_a_full_v1/best.pt
  --manifest tmp/temporal207_newton_main_hold_compact_eventclean_v1/manifest.json
  --data-cache tmp/full1000_event_trial_20260925/data.pt
  --q-cache tmp/temporal207_newton_main_hold_compact_eventclean_v1/q_cache_64.npz)
echo START_SMOKE_ADAPTER1
python tmp/train_full1000_position.py "${common[@]}" --execution-only --rollout-batch-fraction 0 \
  --steps 1 --schedule-steps 1000 --evaluation-every 1 --output "$root/smoke_adapter1" > "$root/smoke_adapter1.log" 2>&1
echo START_SMOKE_AUTONOMOUS2
python tmp/train_full1000_position.py "${common[@]}" --parallel-rollouts --parallel-pool-size 128 \
  --parallel-updates-per-step 2 --steps 2 --schedule-steps 1000 --evaluation-every 1 \
  --fixed-teacher-probability 0 --initial-position-checkpoint "$root/smoke_adapter1/last.pt" \
  --output "$root/smoke_parallel2" > "$root/smoke_parallel2.log" 2>&1
python "$root/check_smoke.py"
echo START_FRESH_ADAPTER20
python tmp/train_full1000_position.py "${common[@]}" --execution-only --rollout-batch-fraction 0 \
  --steps 20 --schedule-steps 1000 --evaluation-every 5 --output "$root/adapter20" > "$root/adapter20.log" 2>&1
echo START_WARMUP10
python tmp/train_full1000_position.py "${common[@]}" --parallel-rollouts --parallel-pool-size 128 \
  --steps 10 --schedule-steps 1000 --evaluation-every 5 --initial-position-checkpoint "$root/adapter20/last.pt" \
  --output "$root/warmup10" > "$root/warmup10.log" 2>&1
echo START_MAIN1000
python tmp/train_full1000_position.py "${common[@]}" --parallel-rollouts --parallel-pool-size 128 \
  --steps 1000 --schedule-steps 1000 --evaluation-every 25 --initial-position-checkpoint "$root/warmup10/last.pt" \
  --output "$root/main1000" > "$root/main1000.log" 2>&1
echo REGIONFIX1000_COMPLETE
