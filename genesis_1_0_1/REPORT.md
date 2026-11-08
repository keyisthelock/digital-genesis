# Digital Genesis 1.0.1 · The Last Teacher Dies

After the residents were removed, fosters that had exchanged intact signals with them chose correctly on 73.3% of frozen attempts on two unseen maps. The same surviving individuals scored 52.2% with inherited communication weights and 50.6% when messages were blocked. The intact source arm also outperformed the teacher-isolated source arm in all three seeds, although the margin was small in seed 10113 and randomized teachers did better in that seed. This is pilot evidence that useful information can persist after the experienced cohort disappears. It does not identify which resident originated a convention or establish stable culture across generations.

## Design

The continuous ecosystem reuses the trained 32-module movement and social policy, the original energy-funded reproductive lifecycle, and individual four-symbol communication tables. Movement uses the existing neural policy. The pilot freezes its lifetime weight updates so that communication learning can be measured separately. Natural births can mutate both the existing neural genome and the inherited communication genome. Children initialize private communication weights from their own inherited values. Adult runtime weights and memories stay with that individual.

Local encounters are selected from freely moving organisms, with no fixed partners. At some encounters a scout alone sees a local two-state marker for a latch that gives access to stocked food. The receiver sees the delivered symbol or silence and independently chooses a latch. The environment generates marker values at random. A successful latch draws from existing food stock. An attempted send costs 0.035 energy, range is three Manhattan tiles, delivery takes two ticks, and feedback is applied one tick after the latch resolves. Movement can break range or leave the cache behind. Nearby witnesses can learn from a successful public latch action and its symbol, capped at 24 updates per individual. They never receive another organism's private weights, memories, or unobserved marker.

Each pilot run starts with 16 residents. At tick 250, twelve newborns from four external donor families enter the same world. Their siblings and genes are matched across all six arms within a seed. The external donor parents pay the ordinary reproduction debit and never meet the residents. At tick 460, all resident-lineage organisms are removed in the five removal arms. The retained arm leaves them in place. No terrain, food, learner, or clock resets occur at either boundary. Runs end by tick 660.

The intact channel transmits the scout's symbol. The disabled channel delivers silence after the establishment phase. The shuffled channel substitutes unrelated recent symbols. Isolation masks resident–foster social observations and packets while the groups share physical terrain. The randomized-teacher arm replaces resident outgoing symbols with uniform random symbols. All arms use the same initial ecology within a seed. The retained and intact arms use the same contact protocol up to the boundary. Because retained residents occupy space and consume food, the retained arm measures coexistence as well as continued teacher access.

Calibration used separate seeds. The final protocol uses a compact training habitat and four times the original regrowth rate at the same initial food fraction, after sparse encounters and food depletion limited earlier calibrations. This is an enriched experimental environment with a per-tile stock cap. The three pilot seeds are 10111–10113. The two fixed held-out habitats are 90101 (causeway) and 90102 (islands). Their resource geometry and layouts differ from the training basin.

At the endpoint, the surviving original fosters supply frozen held-out panels. Each panel runs with its acquired weights, its own inherited weights, and its acquired weights with the channel blocked. Bodies and starting positions match across these three variants. Weight updates and reproduction are disabled in this assay. Panels with fewer than two surviving original fosters cannot be tested. This comparison separates lifetime weights from their inherited starting values among the survivors. Differences between source arms still include survivor selection, exposure counts, and the small number of independent seeds.

## Outcomes

Frozen entries show correct attempts divided by all resolved attempts across the two held-out maps and three seeds. These are descriptive counts. Attempts within an individual or seed are dependent.

| Source arm | Foster lineage alive at 660 | Original fosters alive / 36 | Resident lineage alive | Frozen acquired weights | Frozen inherited weights | Frozen blocked channel |
|---|---:|---:|---:|---:|---:|---:|
| Intact, residents removed | 89 | 26 | 0 | 384/524 (73.3%) | 269/515 (52.2%) | 270/534 (50.6%) |
| Disabled | 99 | 26 | 0 | 279/532 (52.4%) | 281/547 (51.4%) | 291/587 (49.6%) |
| Shuffled | 102 | 24 | 0 | 244/517 (47.2%) | 244/519 (47.0%) | 273/518 (52.7%) |
| Teacher-isolated | 101 | 25 | 0 | 333/546 (61.0%) | 270/516 (52.3%) | 261/518 (50.4%) |
| Randomized teachers | 95 | 25 | 0 | 296/484 (61.2%) | 276/519 (53.2%) | 257/514 (50.0%) |
| Intact, residents retained | 26 | 21 | 91 | 295/424 (69.6%) | 203/409 (49.6%) | 228/435 (52.4%) |

The removal arm's acquired-weight accuracy by seed was 73.0%, 79.5%, and 65.0%. The corresponding teacher-isolated values were 53.7%, 67.0%, and 62.8%. The isolated arm could still learn from peers and its own outcomes, and its acquired weights improved on its inherited weights. The extra gain in the intact arm is consistent with teacher contact adding to those processes. The source-arm variants were restored to a common test channel for the acquired and inherited evaluations. Their test performance reflects what each source arm had learned during exposure.

During contact, intact residents delivered 132 packets to unrelated fosters, with 75 successful latches on those delivered messages. After removal, fosters delivered 482 messages to other fosters. Of these, 313 crossed ancestry roots and 254 crossed generation numbers. Fosters chose correctly on 289 of the 482 delivered attempts. The unrelated marker–symbol association was 0.095–0.260 bits per seed in the intact removal arm and 0.013–0.019 bits in the shuffled arm. These are uncorrected empirical estimates. Among the 26 surviving original fosters in the intact removal arm, 112 of 156 greedy sender or receiver choices stayed the same between the cutoff and endpoint. Learning continued in the ecosystem after the cutoff, so continuity and later peer learning may both contribute.

The retained arm finished with 45 of the 48 original residents alive, and 91 living organisms of resident ancestry including descendants. After the boundary, resident scouts delivered 95 messages to fosters, and foster scouts delivered 99 to residents. Resident-to-foster interactions resolved correctly in 80 of 141 attempts, and foster-to-resident interactions in 87 of 152. Residents continued participating in both roles. Retention coincided with fewer living foster-lineage organisms in all three seeds. Continued contact and increased competition for food and population slots were coupled in this arm.

All arms survived to tick 660. The intact removal arm recorded 119 natural births across the three seeds and reached generation 4. Of those births, 102 changed the inherited communication genome relative to the parent. The pilot logs genetic change and lifetime learning separately. A mutation count does not measure the direction or strength of genetic selection. Better signal use did not translate into higher population survival or more foster descendants in this pilot.

## CPU and verification

The 18 main runs used 279.3 process CPU seconds and about 28.1 million modeled neural operations. The 108 frozen evaluations used another 64.1 process CPU seconds. The main runs spent 1,322.72 simulated energy on sends, 1,246.64 on latch attempts, and 880.48 on neural computation. Calibration and benchmarking are separate from those totals.

| Standalone run on the same map and seed | Ticks | Process CPU seconds | Ticks / CPU second | Modeled brain energy |
|---|---:|---:|---:|---:|
| 32 modules | 240 | 2.30 | 104.5 | 14.43 |
| 67 modules | 240 | 4.69 | 51.2 | 25.36 |

These are single-run CPU measurements with different population trajectories. Twenty-two regression tests passed. Data checks verified matched foster cohorts, identical intact and retained interactions through the boundary, packet delays, channel masking, ancestry, and energy balance. This release uses the existing CPU execution path.

For Genesis Stage II, replace removed residents with matched naïve residents at the same density and hold resource access and population slots constant across that comparison. Add a frozen evaluation just before removal and track particular signal conventions in descendant cohorts. That would separate the effect of a teacher's experience from crowding and distinguish retained conventions from new conventions learned among peers.

[Population results](pilot/results.csv) · [Transmission by phase and role](pilot/transmission.csv) · [Held-out evaluations](pilot/heldout.csv) · [Unrelated signal association](pilot/information.csv) · [Run commands](README.md)
