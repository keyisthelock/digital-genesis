# Digital Genesis 1.0.1

Run these commands from this directory with Python 3.12. The experiment uses the Python standard library and imports the existing neural and reproductive code from the adjacent v03_social directory.

```powershell
$python = 'python'
& $python experiment.py --ecosystem-ticks 1000 --output continuous_run
& $python experiment.py --output pilot_repeat
& $python analyze.py pilot_repeat
```

The continuous mode starts a population and lets it move, learn and reproduce in one world. The experiment mode runs the cultural-transmission arms with the same starting worlds and foster families within each seed. The output path must be new. The world continues across cohort introductions and removals within a run. Saved panels are for frozen evaluation and do not resume a previous live process.

The following commands are available for larger research runs. The 67-module configuration is an independent comparison.

```powershell
& $python experiment.py --seeds 12 --output formal_32
& $python experiment.py --seeds 12 --modules 67 --output formal_67
```

Per-arm directories contain the population time series, interactions with packet timestamps, ancestry, energy accounting, individual communication conventions, and before/after learner snapshots. The top-level CSVs contain population endpoints, transmission by phase and role, and frozen evaluations. The analysis command adds estimates of marker–symbol association for delivered signals between unrelated individuals.
