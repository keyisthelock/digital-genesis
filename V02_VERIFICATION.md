# v0.2 verification — 6 November 2026

All eight unittest cases pass: the original four are unchanged, plus four focused
cases for starvation under zero food, juvenile maturity/energy-funded reproduction/
mutation/population cap, fixed-genome offspring, saved terrain and deterministic
lifetime simulation. No new packages were installed.

The short experiment used seeds 0–9, two treatments, 1,200 ticks each, 20 founders,
population cap 60, resource fraction 0.2, maturity age 60 and maximum lifespan 1,200.
Every treatment loaded the same saved terrain and initial resources, SHA-256:
`21fd166cece622a20acf3b6e7aa6605d60f4f66a82027bd5c93147b7b874cf76`.

| Metric (mean across 10 seeds) | Evolving | Fixed baseline |
|---|---:|---:|
| Final living population | 2.2 | 2.7 |
| Births | 7.2 | 7.9 |
| Starvation deaths | 24.4 | 24.4 |
| Organism-ticks survived | 7,735 | 7,387 |
| Mean observed lifespan, ticks | 284.64 | 265.09 |
| Organism-ticks per food unit | 3.318 | 3.364 |
| Average fitness per organism ever born | 165.94 | 153.81 |

Founders surviving to the final horizon: zero in both treatments. Maximum age
coincides with the horizon, so this metric alone cannot indicate adaptive success.
The evolving treatment has higher fitness and lived ticks but fewer births and
final survivors, with slightly lower food efficiency. This is mixed descriptive
evidence, not a demonstrated adaptive improvement. There were no statistical
significance tests or correction for testing multiple metrics.

The full comparison was repeated and yielded byte-identical comparison CSVs.
After adding two derived metrics, the final code was run again and matched every
previous metric for all 20 simulations. Final outputs:
`results/v02_final_verification/comparison.csv` and `paired_summary.csv`.

The separate six-hour offline experiment is running in `results/v02_overnight`:
30 founders, cap 100, fraction 0.35, maturity 100, lifespan 3,000, seeds 0–9,
same terrain, approximate duty fraction 0.15. It updates CSVs and history during
execution. These settings differ from the short verification; conclusions must
compare treatments within each experiment, not the two experiments directly.
An outcome review is scheduled in this chat. Six hours is a wall-time ceiling;
complete extinction ends the run early. No result from this unfinished experiment
is claimed here. The Forbidden Fruit remains offline as requested.

The existing visual windows were not restarted. Updated v0.2 UI rendering has not
been inspected live; camera/UI code is preserved except juvenile radius, growth
inspection, and safe handling of an empty population.
