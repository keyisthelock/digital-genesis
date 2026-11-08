# Digital Genesis v0.3.2 · Sexual reproduction and evolution

Two-parent reproduction worked. The saved 32-module neural policy produced one biparental birth in each pairing treatment, versus 24 asexual births across the three seeds. All main neural populations eventually went extinct under normal resources. No neural trial offered an initiator a choice between two eligible partners, and no neural source seed yielded enough biparental descendants to compare early and late cohorts. The experiment shows that the mechanism works and that access to compatible, simultaneously ready partners was a bottleneck. It gives no evidence of a survival advantage from social partner choice.

## Design and outcomes

Seeds 11100–11102 used the same saved terrain, 10 founder positions, and a cap of 24 in each paired comparison. Most treatments started at 35% resources, with up to 1,500 ticks. Both parents had to meet the original maturity age of 100, energy threshold of 85, and cooldown of 60 ticks. Compatible organisms had to be within two Manhattan tiles. Asexual parents paid 40 energy. Biparental parents paid 20 each, with the same 30-energy child endowment in either mode. Reproductive type affects compatibility only. Trial 3 changes the founder ratio to 8 A and 2 B, with the newborn A probability held at 50% in both arms.

| Trial | Treatment | Births | Alive at end | Surviving offspring | Extinctions | Births / 1,000 mature ticks |
|---|---|---:|---:|---:|---:|---:|
| 1 First partners | Neural asexual | 24 | 0 | 0 | 3 | 2.77 |
| 1 First partners | Neural random compatible | 1 | 0 | 0 | 3 | 0.12 |
| 1 First partners | Rule asexual | 99 | 33 | 30 | 0 | 2.63 |
| 1 First partners | Rule random compatible | 11 | 18 | 6 | 0 | 0.35 |
| 2 Bond or instinct | Neural random compatible | 1 | 0 | 0 | 3 | 0.12 |
| 2 Bond or instinct | Neural social preference | 1 | 0 | 0 | 3 | 0.12 |
| 3 Lonely world | Neural random, 50:50 | 1 | 0 | 0 | 3 | 0.12 |
| 3 Lonely world | Neural random, 80:20 | 0 | 0 | 0 | 3 | 0.00 |
| 4 Moderate scarcity | Neural social, sharing enabled | 0 | 0 | 0 | 3 | 0.00 |
| 4 Moderate scarcity | Neural social, sharing masked | 0 | 1 | 0 | 2 | 0.00 |
| 4 Moderate scarcity | Rule reference, paired | 6 | 13 | 3 | 0 | 0.23 |

Normal neural asexual runs reached generation 4 and first reproduced at tick 100 in all three seeds. Both neural biparental arms first reproduced at tick 135 on seed 11101 and reached generation 2. Each arm logged 184 mature compatible pair-ticks, only one with both parents ready. Social and random produced the same result when there was only one partner. The 80:20 runs recorded 181 mature compatible pair-ticks and zero ready pairs. At 28% resources, rule populations reproduced on two seeds and all survived. The neural scarcity runs had zero ready pairs and one observed energy share in the enabled arm. This was too little exposure to assess whether cooperation helps reproduction.

## Trial 5 · Frozen descendants

The neural comparison required disjoint early and late birth cohorts from both asexual and social source runs on the same seed. Source seeds had 3, 7, and 14 asexual births and 0, 1, and 0 social births. The neural transfer test therefore has three failed exposures. A supplemental rule-reference comparison used actual rule asexual and randomly paired descendants. Two source seeds yielded enough births for eight frozen evaluation runs. Both body-genome cohorts started from the same positions and food budgets within each seed. They faced an unseen map, a food relocation at tick 250, and no further reproduction, mutation, or learning. Early and late refer to birth order. Survival was identical across all four arms within a seed, with five survivors on one map and two on the other. Fitness shifts varied by mode and map, and offer no survival evidence for either inheritance mode.

## Inheritance and verification

Birth logs include both parent IDs where applicable, reproductive types, generation, contributions, child body and neural genotypes, module and scalar sources, and parental fingerprints. Ancestry records resolve fingerprints to the corresponding saved founder or earlier birth. The crossover selects valid sparse modules from both parents and samples the existing learning-rate, memory-decay and social-gain genes before bounded mutation. A child starts with fresh body, neural and social memories and recurrent state. The two rare biparental neural births used the same paired source run, so they are paired outcomes rather than two independent observations. Because the first-generation parents shared the same trained genotype, that birth shows segregation of source modules and mutation, with no demonstrated diversity gain from mixing distinct parents. All 24 asexual neural newborn genomes were distinct. The single newborn per biparental arm prevents a population-level dispersion comparison.

All 15 existing and focused regression tests passed. The run checked energy balance, genealogy, compatibility, cap and population accounting. Deterministic tests cover two-parent energy accounting, genetic crossover, newborn state, cooldown and compatibility, and equal results when the policies have the same sole available partner. The 27 distinct main runs used about 62 CPU seconds. A Pygame headless render smoke check exercised the existing laboratory setup. The experiment setup exposes reproduction mode, type probability, interaction distance, and optional saved founder genome. The laboratory displays the reproductive type, lineage branches, partner and birth events, and the living type distribution using the existing amoeba sprites and birth animation.

The next comparison should target partner availability before scaling seed count. Predeclare a second interaction-distance setting and measure how often multiple mature, sufficiently energized partners are available. That would give social ranking a real chance to differ from random choice while retaining the original energy requirements.

```powershell
python reproduction_trials.py --seeds 3 --output experiments/reproduction_repeat
python reproduction_trials.py --seeds 10 --output experiments/reproduction_10seeds
python run_v03.py --reproductive-mode social --modules 32 --trained-neural experiments/first_survival_v031/trained_32.json
```

[Trial CSV](results.csv) · [Frozen reference results](held_out.csv) · [Transfer exposure](transfer_exposure.csv) · [Protocol](protocol.json)
