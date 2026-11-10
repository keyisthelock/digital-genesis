# Digital Genesis

Digital Genesis is a CPU-first artificial-life research project. It follows simulated organisms as they forage, reproduce, learn signals, and exchange information. The current research version is **Genesis 1.4.1**.

## Latest research · The Memory That Crossed Worlds

Genesis 1.4 brought Omega into a procedural human body in a fictional settlement. In 1.4.1, the memory audit reproduced all 432 archived decisions and found zero lookups of the old Earth keys. A retrieval bridge then let recorded Earth outcomes influence the new planner.

Across 1,800 held-out episodes on 20 paired seeds, preserved memory scored 75.0% versus 71.4% for standardized memory. The paired difference was +3.6 percentage points (95% interval −3.1 to +10.3). One of 60 single-record removals changed a successful choice into a failure. Preserved Omega chose to read 84 times.

[Experiment and reproduction notes](genesis_1_4_1/README.md) · [Scientific report](genesis_1_4_1/evidence/REPORT.md) · [PDF](docs/Digital_Genesis_1.4.1_The_Memory_That_Crossed_Worlds.pdf) · [Paired results](genesis_1_4_1/evidence/paired.csv)

Exact replay requires the original local archives listed in the version guide.

## Research progress

| Phase | What changed | Observed result |
|---|---|---|
| v0.1–v0.2 · Ecology | Added the Earth viewer, food scarcity, starvation, juvenile growth, and energy-funded reproduction. Compared evolving organisms with fixed genomes across paired seeds. | Established reproducible ecology and survival controls, including overnight runs and five environmental trials. |
| v0.3 · Social Mind | Added individual neural controllers, social memory, and an instrumented laboratory. | All 45 primary neural populations in the first screen went extinct with zero births. |
| v0.3.1 · First Neural Survival | Fixed module routing and action credit. Compared four brain sizes, lifetime learning, and demonstration-based training. | The initial held-out screen recorded 90 neural births. All 16 demonstration-trained groups reproduced. Lifetime updates showed mixed results. |
| v0.3.2 · Reproduction and ages | Added biparental inheritance and eight environmental eras. Tested shared two-symbol signaling under resource pressure. | Two-parent births worked, but compatible partners rarely met all conditions. All groups died under the original era schedule. In a buffered communication experiment, five groups learned to signal and survived a million simulated years. |
| v0.3.3 · Individual communication | Replaced shared signal weights with individual sender and receiver policies. Tested limited range, delayed feedback, and unfamiliar partners. | Intact signals improved survival in four of five original tasks. An abrupt flood defeated 11 of 12 intact pairs. With a low-risk transition on fresh seeds, 12 of 12 intact pairs survived versus 2 of 12 shuffled pairs. |
| Genesis 1.0.1 · The Last Teacher Dies | Introduced cross-foster learners into freely interacting populations and compared teacher removal with retention and communication controls. | On unseen maps, learners exposed to intact teachers and tested after removal scored 73.3% with acquired weights, 52.2% with inherited weights, and 50.6% with messages blocked. |

In Genesis 1.0.1, teachers and newcomers kept exchanging messages in both directions when teachers stayed. The retained arm finished with 45 of 48 original teachers alive and 26 foster-lineage organisms, compared with 89 foster-lineage organisms after removal. Teacher retention also changed crowding and resource competition. The three-seed pilot supports transmission of useful signals, with stable culture and long-term evolutionary advantage still open questions.

## Run Genesis 1.0.1

Use Python 3.12. The headless experiments use the standard library.

```sh
cd genesis_1_0_1
python experiment.py --ecosystem-ticks 1000 --output results/continuous
python experiment.py --output results/pilot-repeat
python analyze.py results/pilot-repeat
```

The experiment requires a fresh output directory. See the [Genesis run guide](genesis_1_0_1/README.md) for larger seed counts and the 67-module comparison. For the graphical lab, install the optional Pygame dependency with `python -m pip install -r requirements.txt`, then run `python run_v03.py` from `v03_social`.

## Reports and evidence

- [Genesis 1.0.1 scientific report](genesis_1_0_1/REPORT.md), [PDF](docs/Digital_Genesis_1.0.1_The_Last_Teacher_Dies.pdf), and [held-out results](genesis_1_0_1/pilot/heldout.csv)
- [The Age of Communication](v03_social/experiments/communication_v033/REPORT.md)
- [Sexual reproduction and evolution](v03_social/experiments/reproduction_v032/REPORT.md)
- [Signaling across simulated eras](v03_social/experiments/signal_ages_v032/REPORT.md)
- [First Neural Survival](v03_social/experiments/first_survival_v031/REPORT.md) and [experience-only follow-up](v03_social/experiments/diwali_v031/REPORT.md)
- [Ten-seed environmental trials](knowledge_candidate/experiments/five_trials_10seeds/REPORT.md) and [six-hour experiment report](docs/Digital_Genesis_Six_Hour_Report.pdf)
- [Early ecology and v0.2 methods](V02.md)

This repository contains source, runnable configurations, selected trained genomes, and compact result tables. Full local archives include raw interaction logs, replay data, and checkpoints. Simulated calendar years describe an environmental schedule. Survival, task accuracy, and learned signals measure specific outcomes under the stated controls.
