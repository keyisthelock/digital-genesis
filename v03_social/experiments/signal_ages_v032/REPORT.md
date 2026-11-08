# Digital Genesis v0.3.2 · Learning across a million simulated years

Five of six groups with the intact learned channel reached 1,000,000 simulated years alive. Two used the trained 32-module foraging policy and three used the original rule-based foraging policy. The groups learned a binary signal during the same ecological run. Once the weights were frozen, they chose the correct food-gate route on all 6,656 attempts. The five groups that reached the endpoint accounted for 6,131 of those attempts.

## Same populations, eight eras

The schedule uses 2,000 ticks at 500 simulated years per tick. It passes through temperate conditions, cooling, an ice age, deglaciation, a warm forest, volcanic disturbance, a dry age and recovery. Population, ancestry and group learning continue between eras, with no restocking of organisms. This communication trial uses a 60% starting food and regrowth floor, a 90% daylight floor and half-patch relocation as an exploratory refuge treatment. Conditions are more permissive than in the original age experiment. Both control channels run with the same refuge conditions.

When an organism attempts to eat from a stocked patch, the protocol presents an independent random safe route to a distinct sender role within the living cohort. The receiver role gets one symbol and chooses a route. A correct choice accesses existing food. The gate creates no food or energy. The sender and receiver use two shared group action-value tables, initialized at zero. The learning signal is retained food divided by 10 less 0.25 per attempt. These tables are part of the experiment and are separate from the individual neural genome. The phase at 750,000 simulated years freezes both tables. Shuffled and blocked controls differ from the intact channel only after freezing. Before freezing, the controls and intact arms had identical phase outcomes, trained tables, attempts and successes within each seed and foraging policy.

| Frozen channel | Groups alive at 1M / 6 | Organisms alive at 1M | Births across runs | Correct route choices |
|---|---:|---:|---:|---:|
| Intact learned signal | 5 | 56 | 372 | 6,656 / 6,656 (100%) |
| Shuffled | 5 | 71 | 367 | 6,226 / 12,570 (49.5%) |
| Blocked, constant symbol | 6 | 65 | 366 | 6,101 / 12,309 (49.6%) |

| Learned group | Simulated years reached | Alive at endpoint | Frozen route choices |
|---|---:|---:|---:|
| 18100 neural | 1,000,000 | 11 | 963 / 963 |
| 18101 neural | 986,500 | 0 | 525 / 525 |
| 18102 neural | 1,000,000 | 2 | 653 / 653 |
| 18100 rule-based | 1,000,000 | 16 | 1,432 / 1,432 |
| 18101 rule-based | 1,000,000 | 14 | 1,635 / 1,635 |
| 18102 rule-based | 1,000,000 | 13 | 1,448 / 1,448 |

For example, neural group 18100 used symbol 1 for route 0 in 492 frozen decisions and symbol 0 for route 1 in 471. It used both symbols and assigned their meanings through feedback. Blocking or shuffling the cue brought the group-level choice accuracy close to chance. Food-gate competence did not confer an endpoint survival advantage in the buffered ecology. The rate of opportunities and the population trajectories differed after the intervention, so the raw number of correct choices is not an estimate of equal-exposure efficiency.

## Survival under a tighter communication constraint

Two separate corridor tasks, whiteout crossing and ash channels, made a wrong route cost energy. The sender received the safe route and the receiver received only a symbol. Across both arenas and all three training seeds, all six learned pairs and all six scripted perfect pairs finished alive. All shuffled, blocked and untrained pairs died. The learned code was reversed in one training seed compared with the other two, demonstrating that the token meanings were learned rather than preassigned. The corridor task shows a causal survival benefit under its designed conditions.

The observed behavior is learning and using a two-symbol convention. The task supplies the cue, channel and feedback. The integrated trial uses group tables, so the result does not establish individual neural learning of the signal or an inherited improvement in communication. The earlier age experiments and reproduction trials remain separate. The combined age and signal runs used 172 process CPU seconds.

```powershell
python signal_trials.py --output experiments/signals_repeat
python signal_ages.py --output experiments/signal_ages_repeat
```

[Combined per-seed CSV](results.csv) · [Protocol](protocol.json) · [Example learned weights and frozen route counts](18100_asexual_learned/communication.json) · [Corridor results](../signals_v032/results.csv) · [Original and refuge age experiments](../ages_v032/REPORT.md)
