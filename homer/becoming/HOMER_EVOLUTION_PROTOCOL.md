# Homer evolution protocol

This offline experiment evolves six task-to-method bits, one per numerical or data skill. A bit selects a shortcut or a worked method. No model weights, simulator rules, evaluators or permissions are mutable. A population of ten is evaluated for six generations with seed 180018. The top three training candidates reproduce. Descendants after the first three slots receive a single-bit mutation. Candidate IDs, parent IDs, training results and bits are retained.

Training seeds are 18000–18011, validation seeds 18100–18107, and held-out seeds 18200–18219. Public task packets are checked for duplicates across all splits. Evolution uses training answers through the verifier only. Validation selects a single final elite before held-out metrics are evaluated. The score maximizes accuracy first and minimizes an explicitly modeled method cost second. A checkpoint would be promoted only if it beats the worked reference in both validation and held-out results with no skill-level accuracy regression.

| Split | Evolved | Worked reference | Shortcut |
| --- | --- | --- | --- |
| Training | 72/72 | 72/72 | 2/72 |
| Validation | 48/48 | 48/48 | 3/48 |
| Held out | 120/120 | 120/120 | 8/120 |

The evolved and worked policies used the same modeled cost, 240 held-out method units. No checkpoint was promoted. The result shows the search found the existing worked configuration. These are finite generated exercises with similar task families across splits. The costs are bookkeeping units rather than measured CPU time.
