# Digital Genesis v0.3.3 · The Age of Communication

Individually learned signals improved pair survival over shuffled messages in four of the five original environments. The abrupt flood defeated 11 of 12 communicating pairs. In an exploratory follow-up on 12 fresh seeds, a low-risk interval after the route reversal let all 12 intact pairs survive, compared with two shuffled pairs.

## Individual policies and controls

Each organism starts with its own sender and receiver weights. All four symbol slots have the same random initialization distribution. Senders use local observations. Receivers see only the delivered symbol and, in the two-key task, their own private key. The existing trained 32-module brain contributes to the route choice using local body-state features. Its neural weights are frozen to isolate learning in the communication layer. A separate 67-module run verified that the runner supports the larger brain.

An attempted send costs 0.035 energy by default and delivers only within two Manhattan tiles. Both parameters are configurable. Packets arrive two simulated ticks after sending, the route outcome is known at tick four, and a sender receives credit at tick six only for a delivered, uncorrupted packet used in the task. Each organism updates only its own weights. The birth adapter samples a child's communication genes from the parents' immutable genomes, mutates them, and starts with fresh runtime weights. The inheritance path was verified through an actual simulator birth. The arena trials used the same living organisms from nursery to challenge without reproduction or resets, so they measure lifetime learning and do not estimate evolutionary response.

The intact, shuffled, and blocked arms used the same seeded nursery before the intervention. During the challenge, the shuffled channel delivers independently sampled symbols from the sender's nursery symbol distribution. The blocked channel delivers silence. Both retain the cost of attempted sends. A no-learning arm uses founder weights throughout. The familiar-partner control retains both nursery pairings for Case E. A pair counts as surviving only when both organisms complete all 64 challenge rounds.

## Main comparison

| Environment | Intact | Shuffled | Blocked | No learning | Intact task success | Adjusted p, intact vs. shuffled |
|---|---:|---:|---:|---:|---:|---:|
| A · The Last Harvest | 12/12 | 4/12 | 4/12 | 4/12 | 100.0% | 0.0156 |
| B · The Poisoned Garden | 12/12 | 0/12 | 0/12 | 0/12 | 100.0% | 0.0024 |
| C · The Great Flood | 1/12 | 0/12 | 0/12 | 0/12 | 64.2% | 1.0000 |
| D · The Two-Key Refuge | 12/12 | 0/12 | 0/12 | 0/12 | 97.9% | 0.0024 |
| E · The Unseen Partner | 24/24 | 7/24 | 3/24 | 6/24 | 87.3% | 0.0024 |

Task success is per attempted round, so exposure ends at a pair's first death. Survival inference uses a two-sided exact paired permutation over seed-level counts, with Holm correction across the five comparisons. Both pairs from Case E stay grouped under their common seed.

- **A. Food search.** Intact pairs chose the stocked route on all 768 challenge attempts. The shuffled channel chose correctly on 51.1% of attempts.
- **B. Hazard avoidance.** Intact pairs had zero harmful encounters across 768 attempts. Each control arm recorded 156 harmful encounters before extinction.
- **C. Reversal.** Intact pairs chose correctly on 89.9% of pre-flood attempts and 25.2% after the abrupt reversal. They followed the former safe route 166 times after it became unsafe. Only one pair reached seven correct decisions in an eight-attempt window, on post-flood round 20.
- **D. Coordination.** Both organisms had a private key and sent one symbol. They had to press the same correct switch during a one-slot window. Intact pairs opened the refuge 752 times in 768 attempts, using 1,536 delivered messages at a combined sending cost of 53.76 energy. That is about two packets per successful opening.
- **E. New partners.** All 24 swapped pairs and all 24 familiar pairs survived. Swapped pairs were correct on 71.5% of the first 12 decisions, compared with 88.9% for familiar pairs. Over the full challenge the rates were 87.3% and 92.1%. Lifetime updates remained enabled, so survival after the swap includes time to learn the new pairing.

## Flood follow-up

The paired follow-up kept the abrupt comparison and added 18 shallow-water rounds after the route reversal. During that interval the old convention still failed, but incorrect decisions incurred lower upkeep and no hazard damage. In the fresh-seed abrupt runs, two intact pairs survived and zero shuffled pairs survived. With shallows, 12 intact, two shuffled, zero blocked, and one no-learning pair survived. The unadjusted paired permutation p-value for intact versus shuffled in the shallow treatment was 0.0020. This was a follow-up motivated by the first flood failure.

In the shallow treatment, intact accuracy fell from 312/336 before the change to 42/216 during the shallow interval, then rose to 147/216 once hazards returned. Nine of 12 pairs reached seven correct decisions within an eight-attempt window. Their median time to that threshold was 28 rounds after the reversal. The threshold alone can be reached by chance, so the survival controls and the post-change trajectory are more informative together.

## Scope and verification

The experiment shows learning of arbitrary conventions, short-range cooperative coordination, and partner adaptation in controlled arenas. The task supplies the channel, private information, and outcome feedback. It does not test a general language or demonstrate an evolved survival advantage. The fixed-pair arenas also do not test competition among larger freely interacting groups. Previous simulation files, genomes, archive data and laboratory screens were retained.

All 20 regression tests passed. The run audited energy every round and checked packet and feedback order, private weight initialization, and the absence of updates in the frozen control. The three archives contain 348 total seed-treatment runs.

```powershell
python communication_trials.py --output experiments/communication_repeat
python communication_trials.py --case C --seed-start 23400 --output experiments/flood_abrupt_repeat
python communication_trials.py --case C --seed-start 23400 --flood-grace 18 --output experiments/flood_shallows_repeat
```

[Main results](results.csv) · [Decision traces](decisions.csv) · [Individual weights](weights.json) · [Fresh abrupt flood](../communication_v033_flood_abrupt/results.csv) · [Shallow flood](../communication_v033_flood_shallows/results.csv)
