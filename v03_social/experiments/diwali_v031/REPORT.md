# Digital Genesis v0.3.1 · Diwali research session

The short screen recorded six neural-policy births on three unseen maps and one during curriculum training. A compute-matched random policy produced one additional birth. The experience-only curriculum gave 30 survivors and three births, compared with 30 survivors and two births for the same cold neural policies with lifetime updates. The first mutated descendant underperformed its founder. These results verify reproduction and inheritance, with limited evidence that the curriculum improves performance.

## Failure diagnosis

The archived CSV confirms 45 extinctions and zero births for the 45 primary neural populations. We instrumented the original 67-module policy on three archived case-1 worlds, first with sharing masked and then with it available. The sharing-enabled runs exactly matched the archive for food, ticks, survivors, and births. The six runs provide 18 complete individual histories from the first decision through death. Each trace records the nine network outputs, the legal action probabilities, chosen action, food and energy, reward, learning updates, and sharing transfers.

| Seed | Extinction tick, off / on | Food, off / on | Peak mature energy, off / on | Sharing losses when on |
|---:|---:|---:|---:|---:|
| 0 | 363 / 468 | 322.7 / 468.5 | 54.2 / 71.5 | 19.4 |
| 1 | 436 / 372 | 443.0 / 414.5 | 61.4 / 67.1 | 17.2 |
| 2 | 275 / 306 | 303.0 / 255.8 | 63.4 / 70.6 | 23.4 |

All six populations went extinct. Of 72 deaths, 55 were classified as starvation. The policies selected movement on 10,980 of 14,672 decisions and ate on 381 of 2,455 decisions with edible food available underfoot (15.5%). The average gap between the most and least likely legal actions was about 1.2 percentage points. For example, on seed 0, organism 2 with sharing off died at age 40 having acquired zero food. All observed mature energy peaks stayed below the 85-point birth threshold.

With sharing off, the populations retained 1,068.8 food energy in total and spent approximately 1,318.4 on basal metabolism, 1,780.2 on movement, and 33.5 on neural computation. The full ledgers balance within numerical rounding after including starting energy and the remaining terms. Low food intake relative to movement and metabolism is the primary verified failure mechanism in these three replays. Sharing changed the trajectories and introduced a measurable transfer loss. It was unnecessary for extinction to occur. These three cases cannot isolate mechanisms for all five archived scenarios.

## Minimal changes and curriculum

The experiment uses the v0.3.1 adapter with the same original brain layouts and reproduction rules. Module routing advances once per decision, fixing skipped slots in even-sized groups. The learning reward measures the selected action from the decision-time energy and health, subtracts any subsequent incoming transfers, and adds back the birth debit when a parent reproduces. This prevents these unrelated energy changes from being credited to the action. The candidate also retains the previously introduced softmax temperature of 0.16. The legacy replays use the original temperature and reward, so a legacy-to-candidate comparison cannot isolate one change.

Training uses the existing lifetime-learning updates with no teacher. Stage A uses 90% food, no hazards and no brain-energy debit for 70 ticks. Stage B restores that debit under the same food and hazard settings for 70 ticks. Normal body and movement costs apply in both. Stage C adds natural hazards and reduces food to 60% for 90 ticks. Stage D uses the normal 35% food setting and ordinary reproduction for 220 ticks. Training uses terrain seeds 4201–4204. Ages, bodies, memory and recurrent state reset at each stage. Each founder's learned module weights carry forward as runtime weights, separate from the fixed starting genome. The same mechanism initializes the trained holdout arm. Imitation was a separate earlier experiment.

## Three-seed held-out comparison

Every arm starts with 12 organisms per seed, a cap of 24 and the same starting positions and 35% food budget within each seed. Evaluation terrain seeds 9201–9203 were unseen in training. Runs stop at extinction or 360 ticks. The random control performs the same forward computation as the 32-module brain but samples legal actions uniformly. Food rate is food energy acquired per organism-tick. Alive, births, brain energy, and process CPU time are summed over three seeds. Forward work is about 84 modeled operations per neural decision at every size, as all sizes activate three modules. Mutation can change the per-decision count. Learning updates affect CPU time. The in-world brain debit charges for stored complexity and forward work.

| Brain | Treatment | Alive | Births | Food rate | Brain energy | CPU seconds |
|---:|---|---:|---:|---:|---:|---:|
| — | Original rules | 43 | 37 | 0.442 | 0.00 | 2.16 |
| 32 | Random actions | 10 | 1 | 0.214 | 23.85 | 4.58 |
| 8 | Cold, updates off | 4 | 0 | 0.197 | 11.32 | 3.89 |
| 8 | Cold, updates on | 7 | 1 | 0.210 | 12.06 | 5.62 |
| 8 | Curriculum, updates on | 9 | 1 | 0.224 | 11.95 | 5.19 |
| 16 | Cold, updates off | 4 | 0 | 0.192 | 15.79 | 4.81 |
| 16 | Cold, updates on | 5 | 1 | 0.209 | 15.78 | 6.70 |
| 16 | Curriculum, updates on | 9 | 0 | 0.212 | 16.67 | 7.08 |
| 32 | Cold, updates off | 7 | 0 | 0.214 | 23.44 | 4.95 |
| 32 | Cold, updates on | 8 | 0 | 0.214 | 24.64 | 5.69 |
| 32 | Curriculum, updates on | 6 | 1 | 0.210 | 23.59 | 7.22 |
| 67 | Cold, updates off | 10 | 1 | 0.234 | 41.43 | 6.97 |
| 67 | Cold, updates on | 10 | 0 | 0.222 | 41.33 | 8.20 |
| 67 | Curriculum, updates on | 6 | 1 | 0.221 | 43.03 | 8.81 |
| 32 | Cold, updates and sharing on | 5 | 0 | 0.205 | 23.70 | 8.78 |
| 32 | Curriculum, updates and sharing on | 9 | 0 | 0.221 | 24.39 | 7.98 |

Cold lifetime updates raised the pooled endpoint count from 25 to 30 and births from one to two. The curriculum added one birth over cold updates with the same endpoint count. Eating when food was available rose from 18.0% with cold frozen weights to 18.2% with cold updates and 18.8% after curriculum. Effects varied by size and seed. The two held-out extinctions both occurred on seed 9201, in the 16-module curriculum arm at tick 347 and in the 32-module cold sharing arm at tick 356. Sharing transferred energy 121 times in the cold 32-module comparison and 100 times in its curriculum counterpart, costing 24.2 and 20.0 energy respectively. The effects on survival went in opposite directions.

## First neural generations

The seven neural-policy births across the curriculum and main holdouts were all generation 2. Each child’s genome matched deterministic mutation of its parent's genome. All seven genomes changed. Six parents had acquired lifetime changes, and every child's runtime weights started equal to its own genome with empty acquired long-term memory and zero updates. The first observed lineage was founder 12 to child 13 at tick 100 in the final 8-module curriculum stage. The parent reached 86.01 energy, funded the birth, and the child inherited mutations in seven modules.

On three fresh maps (9301–9303), clones of each genome were evaluated with matching body initialization, frozen mutation and lifetime updates off. After 240 ticks the founder had 21 survivors versus 15 for the descendant, with zero births in both. The founder matched or exceeded the descendant’s survival in every pair and collected more food per organism-tick in every pair. This one lineage provides evidence against an improvement in its inherited weights under these conditions.

The held-out screen took 98.6 process CPU seconds, and the lineage comparison took 10.5. No GPU benchmark was run. All 10 existing tests passed. Output checks verified energy conservation, exact archived replay results, paired resources and spawns, update settings, complete traces, and original engine source hashes.

For the next short experiment, preregister the 8-module curriculum and compare it against both cold lifetime learning and the same number of training ticks spent entirely under normal conditions. Use fresh paired terrain and founder seeds. Track edible-food decisions and births as the primary outcomes. The equal-training-budget control would distinguish a benefit of staging from a benefit of extra practice.

Reproduce with `python diwali_survival.py --output experiments/diwali_repeat` from the project directory.

[Per-seed holdout](held_out.csv) · [Diagnosis](diagnosis.csv) · [Curriculum](curriculum.csv) · [Lineage](lineage.csv) · [Protocol](protocol.json)
