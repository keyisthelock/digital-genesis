"""Read-only replay of archived 1.4 actions and memory accesses."""

import argparse
import json
from pathlib import Path
import pickle
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "genesis_1_4"))
from embodied import DEV as OLD_SEEDS, HumanTrial, digest

HUMAN_PILOT = ROOT.parent / "genesis_1_4/results/pilot"
SOURCE = HUMAN_PILOT / f"{OLD_SEEDS[0]}/preserved/final.pkl"


def verified_checkpoint(path):
    data = path.read_bytes()
    meta = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    if digest(data) != meta["sha256"] or meta["identity"] != 1:
        raise ValueError(f"checkpoint identity/hash mismatch: {path}")
    trial = pickle.loads(data)
    if type(trial) is not HumanTrial or trial.core.id != 1 or trial.world.tick != meta["tick"]:
        raise ValueError(f"checkpoint state mismatch: {path}")
    return data, trial


def replay(seed, arm, intervention):
    run = HUMAN_PILOT / str(seed) / arm
    _, trial = verified_checkpoint(run / "initial.pkl")
    life = trial.core.lifetime
    legacy = trial.legacy[1] if trial.legacy else {}
    old_semantics = sorted(k for k in life.semantic if not k.startswith("settlement:"))
    changed = []
    if intervention == "remove_one":
        if legacy:
            key = next(iter(legacy))
            changed.append(str(key))
            del legacy[key]
        if old_semantics:
            key = old_semantics[0]
            changed.append(key)
            del life.semantic[key]
    if intervention == "shuffle_old":
        values = list(legacy.values())
        for key, value in zip(legacy, values[1:] + values[:1]):
            legacy[key] = value
        values = [life.semantic[k] for k in old_semantics]
        for key, value in zip(old_semantics, values[1:] + values[:1]):
            life.semantic[key] = value
        changed.extend(old_semantics)
    before = dict(legacy_sites=len(legacy), spatial_entries=len(trial.core.brain.memory.long),
                  episodic_entries=len(life.episodes), legacy_semantic=len(old_semantics),
                  trust_entries=len(trial.core.local_life.trust),
                  hypothesis_weights=digest(pickle.dumps(trial.core.local_life.model.weights)),
                  mutated_entries=changed)
    confidence, decide = life.confidence, trial.core.brain.decide
    queries, features, rows = [], [], []

    def record_confidence(label, tick):
        value = confidence(label, tick)
        queries.append((label, value))
        return value

    def record_decision(vector, *args):
        features.append(digest(pickle.dumps(vector)))
        return decide(vector, *args)

    life.confidence = record_confidence
    trial.core.brain.decide = record_decision
    archived = json.loads((run / "chronology.json").read_text(encoding="utf-8"))
    for old in archived:
        queries.clear()
        features.clear()
        current = trial.step()
        rows.append(dict(seed=seed, arm=arm, intervention=intervention, tick=current["tick"],
                         action=current["action"], archived_match=current["action"] ==
                         {**old["action"], "target": tuple(old["action"]["target"]) if old["action"]["target"] else None},
                         semantic_queries=list(queries), neural_input=list(features),
                         active_spatial_entries=len(trial.core.brain.memory.long),
                         school_reachable=sum(p["tile"] == "school" and p["distance"] <= 1
                                              for p in current["perception"]) > 0))
    return before, rows


def run_audit(out):
    out.mkdir(parents=True, exist_ok=False)
    totals, comparisons = [], []
    with (out / "memory_access.jsonl").open("w", encoding="utf-8") as stream:
        for seed in OLD_SEEDS:
            data = {}
            for arm, mode in (("preserved", "as_saved"), ("standard_memory", "as_saved"),
                              ("preserved", "remove_one"), ("preserved", "shuffle_old")):
                before, trace = replay(seed, arm, mode)
                data[arm, mode] = trace
                totals.append(dict(seed=seed, arm=arm, intervention=mode, loaded=before,
                                   decisions=len(trace), archive_mismatches=sum(not r["archived_match"] for r in trace),
                                   named_semantic_lookups=sum(len(r["semantic_queries"]) for r in trace),
                                   legacy_lookups=sum(not key.startswith("settlement:") for r in trace
                                                      for key, _ in r["semantic_queries"]),
                                   school_reachable=sum(r["school_reachable"] for r in trace),
                                   read_choices=sum(r["action"]["kind"] == "read" for r in trace)))
                for row in trace:
                    stream.write(json.dumps(row, separators=(",", ":")) + "\n")
            reference = data["preserved", "as_saved"]
            for (arm, mode), trace in data.items():
                comparisons.append(dict(seed=seed, arm=arm, intervention=mode,
                                        actions_changed=sum(a["action"] != b["action"] for a,b in zip(reference,trace)),
                                        neural_inputs_changed=sum(a["neural_input"] != b["neural_input"]
                                                                  for a,b in zip(reference,trace))))
    result = dict(runs=totals, comparisons=comparisons)
    (out / "audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    result = run_audit(parser.parse_args().out)
    print(json.dumps(result["comparisons"], separators=(",", ":")))
