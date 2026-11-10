# Memory Across Worlds

Run these commands from the Digital Genesis directory using the existing Python environment.

```powershell
python -B -m unittest discover -s genesis_1_4_1
python -B genesis_1_4_1/memory_audit.py --out genesis_1_4_1/results/my_audit
python -B genesis_1_4_1/run_transfer.py develop --out genesis_1_4_1/results/my_development
python -B genesis_1_4_1/run_transfer.py evaluate --out genesis_1_4_1/results/my_heldout
```

Use new output directories. The evaluation validates the shipped source and data lock before running 20 paired seeds. It requires the local Genesis 1.4 and earlier archives. A checksum-verified copy of Omega's age-944 checkpoint is saved read-only in each result directory.

The baseline audit replays the original pilot while recording semantic lookups and neural input hashes. The new experiment takes bounded recorded observations from earlier Omega lives, converts them to generic observable properties, and scores similarity to new objects. The archived neural state is shared. The comparison varies access to recorded experience, including context shuffling and single-record replay. Relevant removal retains the bank but masks the current property's matches.

The three tasks test availability, physical effort with a delayed charge, and the usefulness of reports. All arms can act directly, inspect or read a finite folio at an energy cost. Each seed has nine practice scenes and 18 held-out scenes per arm. Cold audits and held-out episodes cannot update the practice model. The rule-based reference uses the existing motor policy and the same local practice predictor and modeled compute charge.

Open a result folder's `observatory.html` for the articulated pose, settlement map and decision trace. The full traces and exact archive provenance are in `decisions.jsonl` and `archive_records.json`. The viewer is read-only.

The public evidence contains the [scientific report](evidence/REPORT.md), [summary](evidence/summary.csv), and [paired seed comparisons](evidence/paired.csv). Exact replay requires trusted local checkpoints and source logs. The locked evaluation reads the following inputs at their original paths:

- `genesis_1_4/results/pilot/14030/preserved/final.pkl` and `final.json`
- `genesis_1_3_4/results/pilot_final/13830/combined/chronology.json`
- `genesis_1_3_3/results/primary/13700/combined/chronology.json`

The historical audit also reads `initial.pkl`, `initial.json`, and `chronology.json` under the `preserved` and `standard_memory` arms for 1.4 pilot seeds 14030–14032. The runner verifies hashes from `protocol.lock.json` before the 20-seed evaluation.
