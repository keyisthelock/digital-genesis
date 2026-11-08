# First-hour progress — Digital Genesis knowledge experiment

The last complete comparison checkpoint is **126,300 ticks**. The CSV update
failed at about **66 minutes after the original start**, with Windows access
denied while replacing comparison.csv. The likely cause is a transient file lock
from a reader; the exact locking process is not proven. Saved data is retained.
File publication now retries transient PermissionError failures for up to three
seconds; twelve unit tests pass, including transient and persistent lock tests.
Deterministic recovery is underway in results/knowledge_recovered. The recovered
manifest records whether all checkpoint metrics match before continuing. This
report describes the preserved checkpoint, not an assumed successful recovery.

Means across the same ten seeds on identical saved terrain:

| Metric | Knowledge + evolution | Ordinary evolution | Fixed genomes |
|---|---:|---:|---:|
| Final survivors per seed | 1.50 | 1.00 | 2.80 |
| Births per seed | 421.30 | 483.60 | 793.40 |
| Mean observed lifespan (ticks, censored) | 639.90 | 625.57 | 687.79 |
| Organism-ticks per food unit | 2.33 | 2.31 | 2.17 |
| Average fitness | 352.54 | 345.19 | 383.01 |
| Extinct populations out of 10 | 7 | 8 | 4 |

The knowledge treatment reached lineage generation **140**. This is
parent-to-child depth, not the UI's 400-tick logging-window counter. No founders
remain alive, as expected beyond their maximum lifespan.

Its persisted journals contain **321,905 food-association
events**, **4,628 danger-association events**, and
**35,159 exploration-goal completions**.
Association counts can include forgetting and relearning, and goals are
program-defined computational milestones. Final events may include up to the next
partial batch after the last complete comparison checkpoint. They are not proof
of subjective experience, general understanding, or self-directed intelligence.

There is **no clear adaptive advantage**. Knowledge has slightly more survivors
than ordinary evolution but fewer births; its fitness difference is small relative
to variation between paired seeds. It trails the fixed-genome baseline on mean
survivors, births, observed lifespan and fitness. Greater food-efficiency values
alone do not establish adaptation. Runs are still incomplete and several seeds
have gone extinct; no populations are rescued or revived.

The recovery changes file-write reliability only. Behaviour weights, goals,
terrain, mutation, scarcity and all three treatments remain unchanged. The fruit
is offline. Any behaviour improvements belong in a separate subsequent experiment.
