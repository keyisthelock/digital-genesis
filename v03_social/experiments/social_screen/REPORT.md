# Digital Genesis v0.3 - Social Mind prototype

Actual screening: 67 modules per neural organism; target 67 implemented. Seeds [0, 1, 2]; up to 1500 ticks; 114 population runs. No archived files were modified.
## What these results support

- All 45 primary neural populations became extinct and produced 0 offspring. The rule policy retained survivors in 12/15 primary runs. These results do not show a neural or social survival advantage.
- C and D had identical primary trajectories and no primary offspring. Therefore the enabled genetic mutation mechanism had no opportunity to produce descendant changes in these comparisons. This screening does not demonstrate inherited neural adaptation. Any differences between early and late frozen pools can reflect sampling of original founders rather than genetic improvement.
- All 9 primary neural food-relocation runs ended before the midpoint intervention. They did not experience the changed food field, so the screen cannot assess their adaptation to that change. This is a task-exposure failure, not evidence of successful updating.
- The main, unshuffled treatments produced 2940 actual energy-sharing actions and 150 locally observed bonded-loss events across scenarios. C/D trajectories are repeated controls, so these event counts are not independent replications. Relationships and loss mechanisms operated, but functioning mechanisms alone do not establish useful cognition.
- The cooperative access condition caused extinction in all primary treatments, including the rule control. It needs a better validated difficulty range before it can discriminate beneficial cooperation; no change was made to its difficulty after seeing results.
- A tenth focused test confirmed that treatment A matches the preserved v0.2 rule simulation metrics and state under identical initial conditions. The source archive, original five trials, 10-seed results and conserved Organism 36 passed the recorded hash checks.

## Prototype functionality still limited

- The eight-location working-memory buffer is maintained and bounded, but the current policy directly reads the long-term association store, recurrent states, last reward and prediction error. Direct readout of the separate working-location buffer remains unimplemented and should be added with an ablation before attributing benefits to it.
- Module groups are routing labels using the same input features and distinct random parameters; there is no demonstrated functional specialization or evolved routing. Recipient choice uses a designed bond/need heuristic; the decision to share is neural.
- Only the 67-module size received the complete task screen. The 8/16/32-module variants received matched compute/memory benchmarks and have commands for equivalent task comparisons; their survival advantage or disadvantage is untested.
- Lifetime learning updates real numerical parameters but has no learning-disabled matched primary control here. Its energy-based local reward includes reproduction debits and sharing costs, potentially discouraging actions important for population persistence. Prediction error lacks a constant-predictor comparator, and mostly empty food observations can make low error uninformative.
- Loss-window changes are descriptive and include censored observations and repeated C/D paths. A loss-signal-only ablation with matched organisms is still needed to test whether the signal caused a useful response. No subjective emotion, consciousness or intelligence is established.

## Results (means across paired seeds)
|Task|Treatment|Shuffled|Pool|Survivors|Births|Extinctions|Prediction MSE|Shares|Loss events|
|---|---|---|---|---:|---:|---:|---:|---:|---:|
|1|A_rule|0|new|4.33|11.00|0|N/A|0.0|0.0|
|1|B_neural_nonsocial|0|new|0.00|0.00|3|0.2229|0.0|0.0|
|1|C_social_fixed|0|new|0.00|0.00|3|0.2182|100.0|4.3|
|1|C_social_fixed|1|new|0.00|0.00|3|0.2184|93.0|6.3|
|1|D_social_evolving|0|new|0.00|0.00|3|0.2182|100.0|4.3|
|1|D_social_evolving|1|new|0.00|0.00|3|0.2184|93.0|6.3|
|2|A_rule|0|new|13.67|28.67|0|N/A|0.0|0.0|
|2|B_neural_nonsocial|0|new|0.00|0.00|3|0.2229|0.0|0.0|
|2|C_social_fixed|0|new|0.00|0.00|3|0.2182|100.0|4.3|
|2|C_social_fixed|1|new|0.00|0.00|3|0.2184|93.0|6.3|
|2|D_social_evolving|0|new|0.00|0.00|3|0.2182|100.0|4.3|
|2|D_social_evolving|1|new|0.00|0.00|3|0.2184|93.0|6.3|
|3|A_rule|0|new|0.00|0.00|3|N/A|0.0|0.0|
|3|B_neural_nonsocial|0|new|0.00|0.00|3|0.2105|0.0|0.0|
|3|C_social_fixed|0|new|0.00|0.00|3|0.2083|96.7|6.7|
|3|C_social_fixed|1|new|0.00|0.00|3|0.2126|86.3|4.7|
|3|D_social_evolving|0|new|0.00|0.00|3|0.2083|96.7|6.7|
|3|D_social_evolving|1|new|0.00|0.00|3|0.2126|86.3|4.7|
|4|A_rule|0|new|5.00|12.33|0|N/A|0.0|0.0|
|4|B_neural_nonsocial|0|new|0.00|0.00|3|0.2219|0.0|0.0|
|4|C_social_fixed|0|new|0.00|0.00|3|0.2196|92.0|3.3|
|4|C_social_fixed|1|new|0.00|0.33|3|0.2182|90.7|4.7|
|4|D_social_evolving|0|new|0.00|0.00|3|0.2196|92.0|3.3|
|4|D_social_evolving|1|new|0.00|0.33|3|0.2174|93.7|4.7|
|5|A_rule|0|new|4.00|10.00|0|N/A|0.0|0.0|
|5|B_neural_nonsocial|0|new|0.00|0.00|3|0.2234|0.0|0.0|
|5|C_social_fixed|0|new|0.00|0.00|3|0.2192|101.3|6.3|
|5|C_social_fixed|1|new|0.00|0.00|3|0.2183|87.0|5.0|
|5|D_social_evolving|0|new|0.00|0.00|3|0.2192|101.3|6.3|
|5|D_social_evolving|1|new|0.00|0.00|3|0.2183|87.0|5.0|
|6|A_rule|0|early|15.33|34.00|0|N/A|0.0|0.0|
|6|A_rule|0|late|15.33|37.67|0|N/A|0.0|0.0|
|6|B_neural_nonsocial|0|early|5.67|9.33|1|0.2144|0.0|0.0|
|6|B_neural_nonsocial|0|late|2.00|3.67|2|0.2179|0.0|0.0|
|6|C_social_fixed|0|early|3.00|4.33|1|0.2125|126.7|3.0|
|6|C_social_fixed|0|late|1.33|3.33|2|0.2116|141.0|4.0|
|6|D_social_evolving|0|early|3.00|4.33|1|0.2125|126.7|3.0|
|6|D_social_evolving|0|late|1.33|3.33|2|0.2116|141.0|4.0|

Task 1: familiar resources. Task 2: food relocation at midpoint. Task 3: food access requires two physically nearby organisms. Task 4: founder 1 moved away at tick 80 and returned at 140 if still alive. Task 5: founder 2 is killed at tick 100 if alive; only local witnesses with existing bonds receive a loss signal. Task 6: unseen connected land/food geometry, frozen recorded early/late genomes, no lifetime learning or mutation.
## Paired comparisons: D minus controls (survivors, births)
- Task 1 vs A_rule: survivor differences [-5, -4, -4]; birth differences [-13, -9, -11].
- Task 1 vs B_neural_nonsocial: survivor differences [0, 0, 0]; birth differences [0, 0, 0].
- Task 1 vs C_social_fixed: survivor differences [0, 0, 0]; birth differences [0, 0, 0].
- Task 2 vs A_rule: survivor differences [-14, -13, -14]; birth differences [-29, -29, -28].
- Task 2 vs B_neural_nonsocial: survivor differences [0, 0, 0]; birth differences [0, 0, 0].
- Task 2 vs C_social_fixed: survivor differences [0, 0, 0]; birth differences [0, 0, 0].
- Task 3 vs A_rule: survivor differences [0, 0, 0]; birth differences [0, 0, 0].
- Task 3 vs B_neural_nonsocial: survivor differences [0, 0, 0]; birth differences [0, 0, 0].
- Task 3 vs C_social_fixed: survivor differences [0, 0, 0]; birth differences [0, 0, 0].
- Task 4 vs A_rule: survivor differences [-6, -4, -5]; birth differences [-11, -12, -14].
- Task 4 vs B_neural_nonsocial: survivor differences [0, 0, 0]; birth differences [0, 0, 0].
- Task 4 vs C_social_fixed: survivor differences [0, 0, 0]; birth differences [0, 0, 0].
- Task 5 vs A_rule: survivor differences [-3, -4, -5]; birth differences [-8, -9, -13].
- Task 5 vs B_neural_nonsocial: survivor differences [0, 0, 0]; birth differences [0, 0, 0].
- Task 5 vs C_social_fixed: survivor differences [0, 0, 0]; birth differences [0, 0, 0].

## Social signal controls
- Task 1, C_social_fixed: true minus shuffled survivor differences [0, 0, 0].
- Task 1, D_social_evolving: true minus shuffled survivor differences [0, 0, 0].
- Task 2, C_social_fixed: true minus shuffled survivor differences [0, 0, 0].
- Task 2, D_social_evolving: true minus shuffled survivor differences [0, 0, 0].
- Task 3, C_social_fixed: true minus shuffled survivor differences [0, 0, 0].
- Task 3, D_social_evolving: true minus shuffled survivor differences [0, 0, 0].
- Task 4, C_social_fixed: true minus shuffled survivor differences [0, 0, 0].
- Task 4, D_social_evolving: true minus shuffled survivor differences [0, 0, 0].
- Task 5, C_social_fixed: true minus shuffled survivor differences [0, 0, 0].
- Task 5, D_social_evolving: true minus shuffled survivor differences [0, 0, 0].

## Held-out transfer: late minus early genomes
- A_rule: survivors [-2, -1, 3]; births [9, 1, 1].
- B_neural_nonsocial: survivors [-7, 0, -4]; births [-13, 1, -5].
- C_social_fixed: survivors [-6, -3, 4]; births [-6, -2, 5].
- D_social_evolving: survivors [-6, -3, 4]; births [-6, -2, 5].

## Actual observed behaviour
- Task 1: 600 sharing actions; 386 bond-threshold crossings; 527 damaging tile-ticks; 0 repeated empty old-food visits; 26 observed bonded-loss events. Socially eligible interventions 0; applied 0.
- Task 2: 600 sharing actions; 386 bond-threshold crossings; 534 damaging tile-ticks; 3597 repeated empty old-food visits; 26 observed bonded-loss events. Socially eligible interventions 0; applied 3.
- Task 3: 580 sharing actions; 376 bond-threshold crossings; 498 damaging tile-ticks; 0 repeated empty old-food visits; 40 observed bonded-loss events. Socially eligible interventions 0; applied 0.
- Task 4: 552 sharing actions; 380 bond-threshold crossings; 522 damaging tile-ticks; 0 repeated empty old-food visits; 20 observed bonded-loss events. Socially eligible interventions 6; applied 12.
- Task 5: 608 sharing actions; 394 bond-threshold crossings; 540 damaging tile-ticks; 0 repeated empty old-food visits; 38 observed bonded-loss events. Socially eligible interventions 6; applied 10.
Loss behaviour: 354 logged windows, 275 complete 20-before/20-after windows. These are descriptive within-organism observations, with survival/selection confounding. See loss_behavior.csv and social_events.jsonl for individual evidence.
Mean post-minus-pre action rates: move +0.0275, share -0.0255, hazard -0.0280.

## Mechanisms and limits
- Real sparse tanh recurrent networks, randomly initialized. Three context-selected modules per decision. Neural multiply-add costs and active indices are recorded; feature construction, sensing, logging and Python overhead are included in CPU measurements but not neural operation counts.
- Capacity bounds: 8/16/32/67 modules; 2-4 neurons/module; at most 12 input connections/module; one recurrent self-connection/neuron and nine readouts (eight actions plus food predictor). 67 groups: 15 survival, 12 memory, 12 exploration, 18 social, 10 coordination. Genetic weights are deep copies; lifetime updates never enter offspring. Weight, connection, neuron, learning-rate, memory-decay and social-gain mutation are bounded. Lifetime learning uses a local one-step policy-gradient-style rule and food prediction error, without backpropagation through recurrent time.
- Simulated brain cost: 0.000002 per stored complexity unit plus 0.00001 per active neural operation each decision. All neural sizes use the same maximum 168 neural operations per decision. Sizes were benchmarked under the same 12-founder, 24-cap, 100-tick task; full screening uses the reported size only. Rule A has no artificial brain cost and is the copied v0.2 ordinary rule policy, rerun under these matched initial conditions. It is not a reuse of six-hour results as if they were matched v0.3 trials.
- Sharing transfers up to 3 energy at an additional 0.2 energy loss. Repeated local encounters weakly increase familiarity; observed help increases numerical bonds, observed food competition reduces them. These update rules and the cooperative food gate are designed mechanisms, not evolved discoveries. No parent bond is assigned automatically. Local recognition is capped at eight contacts/tick, relationship memory at 32 people, group signatures at eight, food associations at 64, working memory at eight, and recent loss events at eight.
- Loss is triggered only for locally observed deaths with bond >=0.15; bounded at one and multiplied by 0.985 each living tick. The neural policy receives this signal and may ignore it. Loss locations are historical observations. No emotional dialogue or subjective state is claimed.
- The shuffled controls permute identity-to-outcome associations within the currently sensed neighborhood and replay historical isolation/loss/group signals from a bounded own-history buffer. With zero or one neighbor they are weak controls. Physical interactions and actual costs remain real. B removes social inputs, social activation, sharing choices and relationship updates; B therefore tests a social-system ablation, not only removal of a signal.
- The new memory system decays confidence over time, replaces stale associations after negative evidence, and separates eight working locations from 64 longer-term associations. First-50 versus later prediction MSE is exposure-dependent and cannot by itself demonstrate learning. The screening does not include a neural learning-off ablation; transfer freezes learning but also changes terrain. No causal lifetime-learning advantage is established.
- Founder spawns are clustered near food to permit encounters. Treatment pairs share exact terrain, spawns and initial neural genotypes; behavioral RNG paths diverge after different decisions. C disables genetic mutation of neural and old scalar traits; learned parameters remain plastic. D and B retain the original energy-funded reproduction. No fitness-weighted generation replacement is added.
- Social interventions use preselected founder IDs and fixed times. Extinction or no existing bond can make the intended task unavailable. Such cases are counted, never assigned fabricated bonds. Before/after loss and separation results are conditional on opportunity and survival; the intervention is not a complete randomized causal estimate.
- Held-out pools are actual founder or last living/recently dead genomes from Task 1, not champions. Up to eight late genomes are repeated round-robin. All lifetime state resets and all mutation/learning is disabled for transfer. Survivor and lineage sampling bias remains. Unseen worlds change connected land/food geometry and omit hazards; transfer to new hazard ecology remains untested.
- Relationship reciprocity and group stability columns describe living organisms at endpoint, creating survivor bias. Bond-threshold crossings can count re-formation. Action counts record selections that may be preempted by starvation. CSV metrics contain aggregate exploration, hazard and sharing outcomes; journals contain individual cognitive summaries, sharing events and loss windows. Full position trajectories and complete chosen-action totals were not saved for every organism.
- This prototype does not infer subjective love, belonging, grief, consciousness, or intelligence. Three seeds and 1500 ticks are a screening study. Benefits require repeatable survival/reproduction and held-out evidence against relevant controls; higher fitness, clusters, and larger brains alone are insufficient.

## Performance
Screen CPU seconds total 258.453; wall seconds summed across runs 265.789. Benchmark Python allocation peaks and CPU times are in benchmark.csv; these are not total process RAM. All runs are sequential and CPU-only.

## Next experiment
Add matched neural learning-off and time-shuffled nonsocial-memory controls; preregister a primary survival/offspring endpoint; extend paired seeds only after populations survive long enough to reproduce and experience the intervention. Assess trained versus untrained policies on multiple held-out land/hazard maps, and test costly sharing with/without the cooperative gate. Do not tune on the final held-out maps.

## Commands
Visual: `python run_v03.py --modules 67 --treatment D_social_evolving --speed 20`
Headless: `python run_v03.py --headless --modules 67 --ticks 1500 --output results/headless_new`
10-seed expansion (separate output): `python experiment_v03.py --seeds 10 --ticks 1500 --modules 67 --output experiments/social_10seeds`
Capacity controls: use `--modules 8`, `16`, or `32` with the same seeds/ticks/output budget. No expansion starts automatically.

Verification: 114 unique runs; population balances, terrain hashes, neural computation bounds and 10 preserved source/archive hashes passed. Module utilization denotes the population-wide fraction of module indices used at least once, rather than mean per-organism utilization.
