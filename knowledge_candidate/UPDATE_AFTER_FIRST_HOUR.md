# Updates after the first-hour review

The initial drive did not demonstrate a consistent advantage. Many populations
went extinct, births trailed the fixed baseline, and Windows file locking stopped
CSV publication. No improvement in intelligence or adaptation is claimed.

Completed engineering updates:

- Retry temporary Windows CSV replacement locks rather than failing immediately.
- Exact state snapshots every 1,000 ticks, including RNG, world, genomes, lifetime
  memories, goals and counters. A checksum detects file corruption. Only load local
  project-generated pickle snapshots. Logs before a snapshot remain in the source
  experiment directory; resumed logs begin in a new directory.
- Snapshot resume restores state directly instead of replaying the entire history.
- Dashboard distinguishes failed/recovering states and displays four treatments.
- Selected organisms show exploration-goal and novel-location counts.

New hypothesis, not a proven fix: cautious knowledge seeking uses energy above
75 for adults or 55 for juveniles, and grants no novelty bonus when local risk or
pain is present. Existing eating, fitness, energy costs, world and reproductive
rules are unchanged. Original drive, ordinary evolving genomes and fixed genomes
remain controls, using the same terrain and seeds.

All 14 unittest cases passed. A 40-case pilot (10 seeds, 1,000 ticks, eight founders,
cap 30) completed. Mean surviving populations: cautious 8.4, original drive 9.7,
ordinary evolving 7.6, fixed baseline 6.8. Mean births: 23.1, 24.3, 22.8, 22.6
respectively. Mixed evidence; this pilot is not proof of improved adaptation.
The runner then restored the full 40-case snapshot and continued to tick 1,025
successfully. Unit tests separately verified exact continued RNG, organisms,
resources and metrics, and rejection of corrupted snapshot data.

At the user's explicit request, the older recovery was stopped and archived.
A FRESH six-hour experiment started at 2026-11-06 15:56:32 UTC
(6 November 21:26:32 IST), in results/updated_overnight. Deadline is approximately
7 November 03:26:32 IST, unless complete extinction, failure or tick limit ends it
earlier. It uses 30 founders, cap 100, fraction 0.35, maturity 100, lifespan 3,000,
seeds 0–9, four treatments, 60% approximate one-core duty and the same saved terrain.

The dashboard follows this run. The animated Earth window is a read-only
deterministic cautious seed-0 replay of saved checkpoints. Tab changes dashboard
comparisons; camera and pause controls affect the replay only. Hourly checks now
target the new experiment. Internet access remains disabled.
