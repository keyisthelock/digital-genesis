# Experimental ambition and knowledge drive

Isolated extension of v0.2. The active v0.2 comparison has not been modified.
This code cannot be injected into its already running Python process.

`KnowledgeDrive` adds a modest novelty bonus when energy is above 25. The bonus
decreases with visible/remembered risk. Existing eating, pain avoidance, energy
costs, fitness, terrain and reproduction rules remain. An inherited, mutated
`ambition` weight controls the bonus. No energy or fitness reward is granted for
goal completion, and nothing directs an organism toward the fruit.

Local experiences automatically update up to 64 food/danger associations. Novel
locations are counted against the organism's own visited set. Exploration goals
begin at five unique locations and grow in steps of 10, 15, ..., at most 50.
Goals are recorded milestones, not reasoning or human aspirations. Fresh children
inherit the drive weight, not memories. Existing local memory still guides food
seeking and avoidance.

`learning.jsonl` records food/danger associations and completed exploration goals
with organism ID, lineage generation and simulation tick. Association events can
repeat when a location has been forgotten and relearned. Ancestry snapshots include
goal and learning counters. They are computational observations, not subjective
reports or evidence of human-like understanding. Everything remains offline.

The optional comparison uses `--knowledge` to enable three treatments: evolving
with the module, ordinary evolving without it, and fixed-genome baseline.
`knowledge_contrast.csv` reports paired differences against ordinary evolution.
Fixed-genome baselines remain unchanged. To isolate the new
drive's contribution, compare at matched ticks against the ordinary evolving
v0.2 treatment on the same terrain/seeds/settings. A knowledge-versus-fixed
baseline alone conflates mutation and the drive. No benefit is assumed.

```powershell
python -m unittest discover -s tests -v
python experiment.py --knowledge --terrain ../results/v02_terrain.json --output results/knowledge_short --ticks 1200 --duty 1
```

The parent project's `monitor.py --results knowledge_candidate/results/knowledge_overnight`
can display checkpoints once a new experiment has been explicitly chosen.

## Verification and overnight replacement

All ten tests passed. A short 1,200-tick ten-seed check recorded 4,260 food
associations, 17 danger associations, and 1,457 completed exploration goals.
Knowledge populations averaged 1.7 survivors and 6.5 births, versus 2.7 and 7.9
in the fixed-genome baseline; no adaptive benefit is demonstrated. A subsequent
100-tick smoke test verified the three-treatment runner and contrast CSV.

The user explicitly chose to stop the old comparison and launch a replacement.
Its last saved original checkpoint was tick 8,800 and is retained separately.
The new run is `results/knowledge_overnight`, with 30 founders, cap 100,
resource fraction 0.35, maturity 100, lifespan 3,000, approximate CPU duty 0.10,
six-hour wall-time ceiling, seeds 0–9 and the original saved terrain. It starts
from new organisms, not the old process state. It may stop early on complete
extinction. The desktop monitor shows knowledge versus ordinary evolution;
Tab switches to the fixed-genome baseline. Hourly follow-up checks target this run.

## Acceleration and read-only Earth view

The user requested higher CPU usage. The run was continued in
`results/knowledge_accelerated` with a 0.60 duty target. The previous checkpoint
at tick 400 was reconstructed from seeds and the immutable terrain; every saved
metric across all 30 populations matched before continuation. The manifest records
`replay_verified: true`. This deterministic reconstruction recovers RNG and organism
state by replay, rather than loading a serialized live process. It retains the
original six-hour start/deadline and preserves the earlier checkpoint directory.

Edit `results/knowledge_accelerated/control.json` to set duty between 0.05 and 1.0
without another restart. This changes throughput, not simulated behaviour or
weights. Mutation continues to change inherited weights; manual tuning is not
applied during a controlled comparison.

`main.py --follow-experiment results/knowledge_accelerated --generations 1000000
--speed 80 --output results/knowledge_earth_replay` displays a 2D deterministic
replay of the actual seed-0 knowledge treatment. It loads the recorded configuration,
reconstructs its history and never advances beyond the latest saved checkpoint.
It may lag while catching up or wait between checkpoints. It does not drive the
experiment or represent all 30 populations. Closing it does not stop the comparison.
The default 20-window visual limit still applies unless `--generations` is raised.
There is no 3D implementation.
