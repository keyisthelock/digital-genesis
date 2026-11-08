# Digital Genesis v0.3.1 · First Neural Survival

The 36-population CPU screening produced **90 neural births**. All 16 curriculum-trained populations reproduced, contributing 86 births, and 4 of those populations reached generation 3. A generation-3 birth means an offspring reproduced within the trial. The best paired result for endpoint survival and births was the trained 32-module configuration with lifetime updates disabled. The original rule-based control still led the screening.

## Archived extinction replay

Replayed v0.3 case 1, seed 0, on the archived terrain and spawn positions with the original 67-module policy. Extinction at tick 468, 12 starvation deaths, zero births, and 468.55 food energy acquired matched the archived row. Population fell from 12 at tick 140 to 6 at tick 200, 2 at tick 320, and 0 at tick 468. This instrumented replay covers one of the 45 extinct primary populations.

| Selected action | Count | Share |
|---|---:|---:|
| Move | 2,151 | 73.3% |
| Rest | 604 | 20.6% |
| Share | 108 | 3.7% |
| Eat | 72 | 2.5% |
| Investigate | 1 | <0.1% |

Eat was selected on 72 of 484 decisions with edible food under the organism (14.9%). The mean model probability of eating on those decisions was 16.6%. On average, the highest and lowest legal-action probabilities differed by 1.27 percentage points. There were 2,936 lifetime updates, with food-prediction MSE of 0.219 early and 0.218 later. These are errors on experienced states, whose distribution changes during the run.

From 780 initial body energy and 468.55 retained food energy, the main debits were movement (686.40), basal metabolism (530.50), sharing losses (19.40), neural computation (13.48), and gateway investigation (0.20). Removing dead bodies with a combined negative balance of 1.43 reconciles the ledger to zero within rounding. The highest energy observed for a mature survivor was 71.54 against the unchanged birth threshold of 85. This replay implicates inadequate food acquisition relative to movement and metabolism. It also shows why the birth gate stayed closed.

## Curriculum and controls

The opt-in runner keeps the original module internals, ecology, social simulation, birth gate, and mutation rules. Its router advances once per decision so that even-sized module groups cycle through all slots. The lifetime reward excludes incoming transfers received after the choice and refunds the parent’s reproduction debit for credit assignment. Action selection uses a common softmax temperature of 0.16 in all new neural arms. Consequently, the legacy replay and new cold arms differ in several respects and cannot isolate the effect of an individual fix.

The warm start fits the existing rule policy’s actions with four shuffled passes over each stage’s demonstrations. The stages used 90% food with hazards removed, 60% food with ordinary hazards, and 35% food with ordinary hazards. Terrain seeds were 3101, 3102, and 3103, with 160 ticks of demonstrations per stage. The stages yielded 2,638, 2,580, and 2,544 examples. All sizes improved training action log loss in stage 1. Changes during later stages were small and mixed. The saved trained genomes serve as initial founder weights. Experience acquired by an individual after its birth is kept separate from its genotype.

Evaluation used fresh terrain seeds 9101 and 9102, generated after training, for up to 420 ticks. Each seed used the same 12 starting positions, food budget at 35% scarcity, and population cap of 24 across all arms. Learning on and off started with the same genotype within each size and initialization pair. The off switch freezes lifetime weight updates while retaining sensing, memory, and recurrent state. The uniform random policy draws from the neural legal-action mask. The rule control uses the existing rule-based treatment.

## Held-out results

Alive and births are sums across the two seeds. Maximum generation starts at 1 for founders. Food rate is acquired food energy per organism-tick. Efficiency is retained food energy divided by basal, movement, neural, gateway, sharing-loss, and net reproduction costs combined. Starting body energy is outside that ratio.

| Modules | Initialization | Lifetime updates | Alive | Births | Max generation | Food rate | Efficiency |
|---:|---|---|---:|---:|---:|---:|---:|
| 8 | Cold | Off | 3 | 1 | 2 | 0.229 | 0.543 |
| 8 | Cold | On | 6 | 1 | 2 | 0.248 | 0.591 |
| 8 | Trained | Off | 6 | 7 | 2 | 0.353 | 0.743 |
| 8 | Trained | On | 7 | 12 | 2 | 0.361 | 0.747 |
| 16 | Cold | Off | 4 | 0 | 1 | 0.250 | 0.593 |
| 16 | Cold | On | 3 | 0 | 1 | 0.237 | 0.565 |
| 16 | Trained | Off | 7 | 10 | 2 | 0.384 | 0.797 |
| 16 | Trained | On | 9 | 10 | 3 | 0.414 | 0.861 |
| 32 | Cold | Off | 2 | 0 | 1 | 0.242 | 0.576 |
| 32 | Cold | On | 3 | 0 | 1 | 0.243 | 0.578 |
| 32 | Trained | Off | 16 | 15 | 3 | 0.426 | 0.879 |
| 32 | Trained | On | 10 | 13 | 3 | 0.402 | 0.833 |
| 67 | Cold | Off | 6 | 1 | 2 | 0.233 | 0.545 |
| 67 | Cold | On | 7 | 1 | 2 | 0.233 | 0.548 |
| 67 | Trained | Off | 4 | 10 | 2 | 0.365 | 0.767 |
| 67 | Trained | On | 6 | 9 | 2 | 0.381 | 0.795 |
| — | Random policy | — | 8 | 1 | 2 | 0.283 | 0.680 |
| — | Original rules | — | 27 | 30 | 3 | 0.429 | 0.899 |

- **Curriculum transfer.** Training increased births and food acquisition per organism-tick in every matched seed, size, and lifetime-update comparison against cold initialization. Trained agents selected Eat on 74–75% of edible-food opportunities across the two update settings, versus 19–21% with cold weights. This is transfer of a demonstrated behavior to new maps from the same generator. The screen does not distinguish the value of staging from the value of imitation itself.
- **Lifetime learning.** With trained weights, enabling updates produced 44 births and 32 survivors, versus 42 births and 33 survivors with updates disabled. The enabled arm performed 31,896 updates. Its birth difference across the eight pairs was positive in two, negative in three, and zero in three. With cold weights, each update setting produced two births. The sole held-out extinction was cold 16-module with updates enabled, at tick 372 on seed 9102. The results do not establish a consistent survival benefit from lifetime learning.
- **Inheritance.** All 90 neural births matched deterministic mutation of the parent’s genetic weights. Each child started with weights matching its own genome and with empty acquired long-term memory and zero updates. In 46 births, parents had runtime weights different from their genomes. All 90 child genomes differed from their parents’ genomes, and four neural newborns reached generation 3. At the end, 30 living neural organisms were descendants. This verifies natural reproduction and separation of learned weights from inherited weights. It does not measure a fitness gain due to mutation.
- **Compute.** The nominal stored complexity was 224, 448, 896, or 1,876 units, with three active modules and 84 forward ops per neural decision at every size. Modeled brain cost per decision was approximately 0.0013, 0.0017, 0.0026, or 0.0046 energy respectively. These charges model stored complexity and forward work. Lifetime-update overhead is captured in CPU time. Total held-out CPU time was 100.3 seconds. No GPU benchmark or CUDA migration was performed.

## Verification and limits

All 10 existing v0.3 tests passed. The 36 CSV rows were cross-checked against per-run diagnostics for paired spawn positions and food, lifetime update counts, energy balance, and birth audit counts. Nine existing engine source hashes matched the pre-update record. The two terrain seeds and 420-tick horizon support an initial reproduction and transfer check. They do not establish long-run persistence or generalization outside this terrain generator.

Run from the v0.3 project directory with a fresh output path:

```powershell
python first_survival.py --output experiments/first_survival_v031_repeat
```

[Per-seed held-out results](held_out.csv) · [Curriculum training log](curriculum.csv) · [Protocol and founder fingerprints](protocol.json) · [Archived replay diagnostics](legacy_replay/diagnostics.json)
