# Digital Genesis v0.3 - Social Mind prototype

Separate, offline extension of v0.2. The old amoeba drawing, Earth, local sensing and energy-funded reproduction are reused. Earlier projects, experiments and conserved Organism 36 stay in their original directories.

## Run from this directory

The Python bundled with this installation is:
`python`

Visual (click an amoeba; I toggles inspection; wheel zoom; right drag pan; H shows controls):
```powershell
python run_v03.py --modules 67 --treatment D_social_evolving --speed 20
```

The Research Laboratory dashboard defaults to Medium graphics. Use `--quality low` or `--quality high`, `--no-animations`, or `--paused` as needed. See [UI verification and controls](UI_VERIFICATION.md) for checks and measured frame rates.

Headless:
```powershell
python run_v03.py --headless --modules 67 --ticks 1500 --output results/headless_new
```

Repeat screening, using a new directory:
```powershell
python experiment_v03.py --seeds 3 --ticks 1500 --modules 67 --output experiments/social_repeat
```

Separate 10-seed expansion:
```powershell
python experiment_v03.py --seeds 10 --ticks 1500 --modules 67 --output experiments/social_10seeds
```

Smaller capacity controls: substitute `--modules 8`, `16`, or `32`. All sizes have the same 168-operation maximum neural decision budget, three active modules, bounded neurons/connections and identical simulation settings. The benchmark includes Python overhead; neural operation counts cover neural multiply-adds only. Screening uses the requested size if the traced benchmark stays below 100 ms/world-tick and 128 MB; otherwise it explicitly records the 8-module pilot fallback.

Tests:
```powershell
python -m unittest tests_v03 -v
```

`cognition.py`: shared sparse neural modules, genetic mutation, lifetime updates, confidence memory.
`social.py`: bounded identity/bond/group memories, isolation and decaying observed-loss signals.
`social_sim.py`: local sensing, costly sharing, logging, simulation integration.
`experiment_v03.py`: five tasks, shuffled social controls, benchmarks, frozen early/late transfer.
`experiments/social_screen/REPORT.md`: actual results and scientific limitations.

This is an artificial-life prototype. Numerical bonds and loss signals are computational mechanisms; subjective experiences are not measured. Initial random neural policies can fail badly. The experiment reports failures, intervention eligibility and censored observations. No network or external execution tool is exposed to organisms.
