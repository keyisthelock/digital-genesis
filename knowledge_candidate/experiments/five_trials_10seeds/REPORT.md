# Five experimental trials - screening report

Seeds [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]; up to 3000 ticks; 280 independent trials. No archived data was changed.

Means below are across paired seeds, not statistically conclusive. Fitness is secondary.
| Case | Treatment | Memory | Genome pool | Survivors | Births | Extinctions | Food | Energy spent | Hazards | Coverage | Fitness |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | baseline | enabled | founder | 0.00 | 0.00 | 10/10 | 269.9 | 2224.0 | 0.7 | 45.0% | 107.46 |
| 1 | cautious_knowledge | enabled | founder | 0.00 | 0.00 | 10/10 | 270.1 | 2224.1 | 0.9 | 45.0% | 108.28 |
| 1 | evolving | enabled | founder | 0.00 | 0.00 | 10/10 | 270.5 | 2224.8 | 0.7 | 45.0% | 108.59 |
| 1 | evolving_without_knowledge | enabled | founder | 0.00 | 0.00 | 10/10 | 269.9 | 2224.0 | 0.7 | 45.0% | 107.46 |
| 2 | baseline | enabled | founder | 7.70 | 27.30 | 0/10 | 10848.1 | 13239.3 | 5.1 | 45.2% | 280.77 |
| 2 | cautious_knowledge | disabled | founder | 6.80 | 30.30 | 0/10 | 10807.1 | 13310.8 | 0.0 | 44.9% | 223.09 |
| 2 | cautious_knowledge | enabled | founder | 6.80 | 28.10 | 0/10 | 10800.3 | 13244.9 | 7.2 | 45.3% | 279.87 |
| 2 | evolving | disabled | founder | 6.80 | 30.30 | 0/10 | 10807.1 | 13310.8 | 0.0 | 44.9% | 223.09 |
| 2 | evolving | enabled | founder | 6.20 | 26.50 | 0/10 | 10836.7 | 13243.1 | 11.0 | 45.4% | 288.94 |
| 2 | evolving_without_knowledge | enabled | founder | 6.40 | 26.20 | 0/10 | 10885.0 | 13265.9 | 6.2 | 45.3% | 284.35 |
| 3 | baseline | enabled | founder | 5.40 | 37.60 | 1/10 | 9313.5 | 12156.5 | 4.9 | 45.2% | 222.68 |
| 3 | cautious_knowledge | disabled | founder | 4.90 | 34.40 | 2/10 | 8328.6 | 11065.8 | 0.4 | 44.9% | 165.58 |
| 3 | cautious_knowledge | enabled | founder | 0.70 | 13.30 | 9/10 | 3760.9 | 6084.2 | 2.9 | 45.1% | 171.25 |
| 3 | evolving | disabled | founder | 4.90 | 34.40 | 2/10 | 8328.6 | 11065.8 | 0.4 | 44.9% | 165.58 |
| 3 | evolving | enabled | founder | 3.40 | 29.10 | 4/10 | 7210.3 | 9878.4 | 4.1 | 45.1% | 200.51 |
| 3 | evolving_without_knowledge | enabled | founder | 5.50 | 36.50 | 1/10 | 9394.5 | 12197.0 | 7.3 | 45.3% | 226.71 |
| 4 | baseline | enabled | early | 14.30 | 57.60 | 0/10 | 22182.5 | 25140.1 | 0.0 | 100.0% | 398.28 |
| 4 | baseline | enabled | late | 14.30 | 57.60 | 0/10 | 22182.5 | 25140.1 | 0.0 | 100.0% | 398.28 |
| 4 | cautious_knowledge | enabled | early | 13.80 | 61.00 | 0/10 | 22158.2 | 25205.8 | 0.0 | 100.0% | 386.82 |
| 4 | cautious_knowledge | enabled | late | 12.70 | 55.30 | 0/10 | 22164.5 | 25054.1 | 0.0 | 100.0% | 417.04 |
| 4 | evolving | enabled | early | 14.20 | 57.60 | 0/10 | 22125.9 | 25113.1 | 0.0 | 100.0% | 408.55 |
| 4 | evolving | enabled | late | 14.30 | 57.20 | 0/10 | 22185.4 | 25157.3 | 0.0 | 100.0% | 408.28 |
| 4 | evolving_without_knowledge | enabled | early | 13.80 | 59.80 | 0/10 | 22186.7 | 25253.3 | 0.0 | 100.0% | 391.38 |
| 4 | evolving_without_knowledge | enabled | late | 14.30 | 54.60 | 0/10 | 22169.4 | 24994.3 | 0.0 | 100.0% | 408.75 |
| 5 | baseline | enabled | founder | 4.70 | 21.50 | 0/10 | 7310.4 | 9698.7 | 3.8 | 45.2% | 233.06 |
| 5 | cautious_knowledge | enabled | founder | 5.00 | 21.30 | 0/10 | 7347.9 | 9715.2 | 5.2 | 45.3% | 236.78 |
| 5 | evolving | enabled | founder | 4.10 | 18.60 | 1/10 | 6681.3 | 9012.4 | 6.4 | 45.3% | 230.77 |
| 5 | evolving_without_knowledge | enabled | founder | 5.30 | 22.10 | 0/10 | 7345.9 | 9690.2 | 6.7 | 45.3% | 232.19 |

## Paired survival comparisons
Differences are cautious knowledge minus each control at the same seed and genome epoch.
- Case 1, founder, versus evolving: mean difference +0.00; individual differences [0, 0, 0, 0, 0, 0, 0, 0, 0, 0].
- Case 1, founder, versus evolving_without_knowledge: mean difference +0.00; individual differences [0, 0, 0, 0, 0, 0, 0, 0, 0, 0].
- Case 1, founder, versus baseline: mean difference +0.00; individual differences [0, 0, 0, 0, 0, 0, 0, 0, 0, 0].
- Case 2, founder, versus evolving: mean difference +0.60; individual differences [4, 0, 0, -2, -2, 1, 3, 1, 2, -1].
- Case 2, founder, versus evolving_without_knowledge: mean difference +0.40; individual differences [1, -3, 1, 0, -1, 0, 2, 2, 2, 0].
- Case 2, founder, versus baseline: mean difference -0.90; individual differences [-2, 0, -2, 1, -2, -1, -1, 2, -2, -2].
- Case 3, founder, versus evolving: mean difference -2.70; individual differences [-8, 0, 2, -8, 0, -4, 0, -4, 0, -5].
- Case 3, founder, versus evolving_without_knowledge: mean difference -4.80; individual differences [-8, -6, 0, -7, -5, -6, 0, -6, -6, -4].
- Case 3, founder, versus baseline: mean difference -4.70; individual differences [-4, -7, 0, -3, -6, -7, 0, -8, -7, -5].
- Case 4, early, versus evolving: mean difference -0.40; individual differences [-2, 2, 0, -4, 0, 2, 2, 2, -4, -2].
- Case 4, early, versus evolving_without_knowledge: mean difference +0.00; individual differences [-3, -1, 3, -1, 0, 0, 1, 1, -1, 1].
- Case 4, early, versus baseline: mean difference -0.50; individual differences [-3, 1, 2, -2, -3, -1, 5, 0, -2, -2].
- Case 4, late, versus evolving: mean difference -1.60; individual differences [-2, 2, -4, -3, 1, -3, -1, 1, -5, -2].
- Case 4, late, versus evolving_without_knowledge: mean difference -1.60; individual differences [-4, 0, -4, -2, 0, -4, -1, -1, -1, 1].
- Case 4, late, versus baseline: mean difference -1.60; individual differences [-3, 0, -4, -3, -2, -4, 4, -2, 1, -3].
- Case 5, founder, versus evolving: mean difference +0.90; individual differences [0, 0, -1, 2, 1, 5, 1, 1, 0, 0].
- Case 5, founder, versus evolving_without_knowledge: mean difference -0.30; individual differences [3, -2, -4, 0, 2, 1, 3, 0, -1, -5].
- Case 5, founder, versus baseline: mean difference +0.30; individual differences [1, -3, -1, 4, 3, 0, 1, 0, 0, -2].

## Scenario outcomes

### Case 1
Famine: 40/40 populations went extinct; 1200 starvation deaths. Low food and regeneration were both scaled to 0.12. There is no normal-food counterfactual in this screen, so scarcity adaptation is not established.

### Case 2
Danger: 295 harmful tile-ticks, 0 damage deaths, 0 entries into remembered harmful locations. Early/late hazard-per-move rates are in results.csv. Food amount and patch count were preserved; 70% of food amount was concentrated within two tiles of hazards on connected safe land. Safe routes require no hazard crossing. Existing visible-hazard penalties are programmed avoidance, not proof of acquired learning.

### Case 3
Changing world: 29/40 populations survived to relocation; 23 met the recovery rule. Recovery times: [1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000]. Rule: food acquired per organism-tick reaches 90% of the last pre-change window in two consecutive non-overlapping post-change windows. Window size is min(500, ticks/6). No recovery is blank, not zero. Resources and patch count are exactly preserved at relocation; renewable capacities are unchanged. Empty old-patch visits: 61316; repeated failed visits: 26821.

### Case 4
- cautious_knowledge: paired late-minus-early survivor differences [0, -1, -6, -1, 1, -3, -1, -2, 3, -1].
- evolving: paired late-minus-early survivor differences [0, -1, -2, -2, 0, 2, 2, -1, 4, -1].
- evolving_without_knowledge: paired late-minus-early survivor differences [1, -2, 1, 0, 1, 1, 1, 0, 3, -1].
- baseline: paired late-minus-early survivor differences [0, 0, 0, 0, 0, 0, 0, 0, 0, 0].
Early pools are archived founders; late pools are the last up to 30 actual birth records per treatment/seed, not selected champions. Sources, IDs, lineage depths, file hashes and exact genomes are saved in experiment_config.json. Pools smaller than 30 are replicated round-robin to form equal-sized founder populations. All mutation is disabled in this case. Ecological differential reproduction still occurs; no fitness-weighted selection is added. These pools are subject to survivor/lineage sampling bias and are not representative of all late organisms. Unseen seeded landmass configurations are connected; hazards are absent here to isolate transfer to new land and food geometry.

### Case 5
Gateway: 691 individual discoverers, 445 repeat entries; first discovery ticks [117, 157, 126, 144, 95, 121, 111, 113, 90, 119, 51, 51, 116, 80, 147, 146, 67, 65, 76, 76, 58, 63, 83, 83, 57, 64, 56, 56, 48, 55, 56, 56, 221, 135, 157, 125, 73, 124, 99, 99]. Deaths within 100 ticks of discovery: 222. This is an association, not a causal survival effect. The gateway is on connected land, at least ten tiles from initial clustered spawns, with no food within three tiles. Food removed around it was relocated without changing amount or patch count. Distance from ordinary food routes is approximated by this food-free buffer; actual future routes cannot be guaranteed. Brains receive only their existing local observation; no coordinates or reward are added. No network access exists.

## Memory ablations
- Case 2, cautious_knowledge: memory-enabled minus disabled survivors [1, -1, -3, 0, 0, 1, -1, 0, 4, -1].
- Case 2, evolving: memory-enabled minus disabled survivors [-3, -1, -3, 2, 2, 0, -4, -1, 2, 0].
- Case 3, cautious_knowledge: memory-enabled minus disabled survivors [-4, -5, 2, -7, -8, -9, 0, -6, 0, -5].
- Case 3, evolving: memory-enabled minus disabled survivors [4, -5, 0, 1, -8, -5, 0, -2, 0, 0].

## Interpretation, unusual behaviours and limitations
- Survival, births, extinction timing, acquired food, energy costs and actual actions are observed. No narrative about presumed feelings is inferred. Adaptation requires repeatable survival/reproduction or held-out transfer advantages, not fitness alone.
- Visible hazard avoidance and local food seeking are programmed policy responses. Memory ablations remove decision access to episodic locations and visited places; immediate pain, local hazard sensing and internal logging remain. This tests decision memory, not a completely memory-free organism.
- Hazard encounters count damaging tile-ticks, including repeated damage while stationary; hazard entries count movements onto hazards. Hazard/move rates may exceed one when resting in danger. Zero moves uses denominator one. Coverage is the union of visited passable tiles divided by all nonwater tiles; disconnected continents and initial placement constrain its ceiling.
- Energy spent includes basal/action costs and the full 40-unit parent reproduction debit, including the 30 units transferred to a child; it is not purely dissipated energy. Raw food collection can include energy-cap waste. Starting energy is an endowment. Health can fall below zero on the last hit; measured damage records the full hit.
- Existing policy danger memory uses a decaying pain signal and has no timestamp-based food forgetting. Outdated-location visits are measured but do not prove erroneous beliefs. Parents and children can overlap; spatial crowding has no cost. These inherited simplifications were not rewritten.
- There are only ten paired seeds and one 3000-tick screen. Extinction shortens exposure; total damage/intake comparisons are not exposure-adjusted by themselves. The live resource field persists; births change sampling. Observed lifespan is right-censored. Paired means are descriptive; no significance or intelligence claims are made.
- Food relocation, hazard concentration and clustered gateway spawns deliberately change their scenarios; scenarios should not be ranked as if all starting conditions were identical. Treatments within a scenario have identical terrain, resources and spawns.
- Failed or missing archive pools must be reported, never synthesized; inspect genome_sources for provenance. Archive hashes identify files used; this runner never writes under results/updated_overnight.

## Next experiment
Predefine a primary held-out survival/offspring endpoint, expand beyond ten paired seeds, add a normal-food famine control and an unshifted-world change control, and compare fixed early/late genomes with and without decision memory on multiple unseen terrains. Use action-specific exposure and net energy intake to separate programmed caution from beneficial lifetime learning.

Repeat all trials: `python five_trials.py --seeds 10 --output experiments/five_trials_10seeds`.
No new simulation starts automatically. Source code and archived six-hour data remain preserved.






## Additional recorded behaviour

Per-trial policy action selections, hazard/revisit rates, exploration and gateway metrics are saved in behavior_summary.csv. Selections can be preempted by basal starvation; they are not all completed actions.

### Conserved individual

Case 3, seed 2, cautious_knowledge, ID 36: age 2165, 6 offspring, alive at tick 3000. Born before relocation. Selection used survival, offspring, age and deterministic ties; fitness was not used.

Recorded individual behaviour from verified deterministic replay: {"actions_selected": {"eat": 324, "investigate": 1, "move": 1772, "rest": 68}, "damage": 0, "empty_old_patch_visits": 247, "food_after": 815.4873053115072, "food_before": 408.89549773423516, "hazard_entries": 0, "hazard_tile_ticks": 0, "moved_steps": 1772, "repeated_failed_visits": 170}.

Candidate selected after observing outcomes, not demonstrated best across environments. Its individual trajectory was recovered by deterministic replay matching trial metrics; this replay is not independent validation.

Exact organism state, genome, ancestry, own learning journal, individual behavior.jsonl and world context are saved under conserved_amoeba/.