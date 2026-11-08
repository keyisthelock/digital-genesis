# Digital Genesis v0.3.2 · Million-year transitions

The experiment uses eight 250-tick eras, with 500 simulated years per tick. A complete run covers exactly 1,000,000 simulated years. This is a time scale for the environmental schedule. It does not change organism ages, reproduction thresholds or the number of evolutionary generations simulated.

## Original schedule and refuges

The schedule passes through a temperate start, cooling, an ice age, deglaciation, a warm forest age, volcanic disturbance, a dry age, and temperate recovery. Daylight and regrowth vary by era. Deglaciation and recovery move food patches while conserving their stock. The volcanic era adds a small number of temporary hazards on food-free land. Each cohort uses the same original map within its seed. Extinct populations stay extinct and later eras show zero exposure.

No cohort survived the original transitions to the million-year endpoint. All nine entered the ice age, seven reached deglaciation and three entered the final era. A separate exploratory refuge experiment kept the same seeds and hazards, set floors of 35% for regrowth and 90% for the daylight multiplier, and left half of the food patches in place during relocations. Five groups finished with living organisms in the refuge experiment.

| Policy | Static finishers / 3 | Original transitions / 3 | Refuge transitions / 3 | Refuge births | Refuge alive at 1M |
|---|---:|---:|---:|---:|---:|
| Neural asexual | 2 | 0 | 2 | 101 | 7 |
| Neural biparental, social preference | 0 | 0 | 0 | 0 | 0 |
| Rule asexual | 3 | 0 | 3 | 103 | 14 |

The weighted score uses 50% persistence, 30% food acquisition per organism-tick, and 20% births per mature organism-tick. Each component is scaled to 0–1 before weighting. This score summarizes performance and does not enter the agents' rewards. Mean scores for static, original transitions, and refuge transitions were 0.828 / 0.692 / 0.950 for neural asexual, 0.548 / 0.433 / 0.564 for social pairing, and 0.869 / 0.751 / 0.866 for rule asexual. The refuge test was designed after seeing the original extinctions. It identifies a feasible experimental condition and should be replicated with fresh seeds.

[Original per-era exposure](ages.csv) · [Paired adaptation scores](adaptation_contrast.csv) · [Refuge results](../ages_v032_refuges/results.csv)
