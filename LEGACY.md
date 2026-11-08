# Digital Genesis — The First Amoeba

**v0.2:** see [V02.md](V02.md) for lifetime reproduction, juvenile growth,
scarcity, fixed-genome baselines and ten-seed paired comparisons. The main program
now defaults to lifetime mode and resource fraction 0.35. Use
`--legacy-generations --resource-fraction 1` for the earlier cohort mechanics.
The description of cohort replacement below applies to legacy mode.

Python 3.10+; CPU only. No models, network calls, services, or external assets.

```powershell
python -m pip install -r requirements.txt
python main.py
python main.py --headless --generations 20 --seed 42
python -m unittest discover -s tests -v
```

Headless mode uses only the standard library and does not import Pygame.
Run commands from this directory. Options include `--population 100`,
`--ticks-per-generation 400`, `--mutation-rate 0.2`,
`--mutation-strength 0.25`, `--max-lifespan 600`, `--speed 30`, and
`--output results/experiment_name`. Outputs at the chosen path are overwritten;
use separate paths to retain experiments. R restarts with the same seed and resets logs.

SPACE pauses; +/- changes ticks per second; ESC exits. Click an
organism to inspect its vitals and genome. The purple diamond is a local inert
object, discovered by proximity and investigated on contact. It grants no fitness
or energy bonus and has no special navigation objective.

Earth view: stylized continents and oceans (not exact geography). Scroll the
mouse wheel over the map to zoom 1–8× around the pointer, right/middle-drag to
pan, and press Home to fit the whole map. Camera changes never reset the world,
organisms, tick, or learning. The R restart shortcut has been removed.
The terrain generator changed, so seed-42 runs from the previous version are not
directly comparable with the new Earth terrain. Existing experiment files remain.

The 60×40 world persists across generations. Organisms see a radius-two square,
use a 64-location food/danger memory, and score adjacent moves with inherited
weights. Food regenerates faster during daylight; nights cost more energy.
Trees are passable, water impassable, red tiles damage health. Every action costs
energy; resting reduces expenditure relative to movement but cannot generate energy.
Pain and fear are numerical signals, with no claim of subjective experience.

Each fixed-length generation has a fresh cohort, selected proportionally to
`1 + fitness` from all previous cohort genomes, including archived dead organisms.
Offspring receive new IDs, fresh lifetime memory, and independently mutated
weights clamped to [0.01, 6]. Dead individuals never resume acting. Survivors are
retired at the boundary; retirement is not counted as death.
Fitness = 0.1 × age + 0.5 × energy consumed from food + 0.8 × unique tiles visited.
Visited tile sets are bounded by world size. Ancestry is streamed to disk so
in-memory population/history stays bounded.

`generations.csv` records cohort size, natural deaths, mean/best fitness, mean
observed age, mean unique tiles explored, and individual fruit discovery counts.
Mean age includes censored ages of boundary survivors; it is not an estimate of
uncensored life expectancy. `ancestry.jsonl` stores every genome, parent, fitness,
age and boundary status as one JSON object per line; `selected_genomes.json`
contains the latest champion; `fruit_events.jsonl` records discoveries and
interactions; `config.json` records parameters. Compare CSV generation 1 with
later rows. Identical parameters/seeds reproduce outputs on the same Python
runtime; no monotonic improvement or intelligence gain is guaranteed.

Limitations: no mating, within-generation births, combat, or spatial inheritance;
movement can overlap and isolated land can trap organisms. Environmental changes
and stochastic variation confound single-run fitness comparisons. Use multiple
seeds and fixed-policy baselines for scientific conclusions. Partial visual runs
log only completed generations. Logs grow linearly on disk with experiment size.
