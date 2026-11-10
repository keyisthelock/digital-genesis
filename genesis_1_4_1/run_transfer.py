"""Run and lock the Memory Across Worlds experiment."""

import argparse
import csv
import json
from pathlib import Path
import random
import stat
from statistics import mean
from time import process_time

from memory_audit import ROOT, SOURCE, verified_checkpoint
from embodied import cognitive_hashes, digest
from run_human import observe
from settlement import Settlement
from transfer import (ARMS, DEV, EARLIER, EARTH, EVAL, HELDOUT_PER_TASK, PRACTICE, TASKS,
                      Predictor, asdict, memory_bank, run_task, shuffled)

LOCK=ROOT/"protocol.lock.json"
SOURCES=(ROOT/"memory_audit.py", ROOT/"transfer.py", ROOT/"run_transfer.py", SOURCE, EARTH, EARLIER,
         ROOT.parent/"genesis_1_4/embodied.py", ROOT.parent/"genesis_1_4/settlement.py",
         ROOT.parent/"genesis_1_4/run_human.py", ROOT.parent/"genesis_1_3_1/inquiry.py")
MEASURES=("success","cold_brier","prior_brier","posterior_brier","read","inspection","verified","confirmed",
          "changed_after_information","useful","unnecessary","retrieved","energy_spent","neural_ops",
          "comparison_slots","cpu_seconds")


def config():
    return dict(version="1.4.1", development=list(DEV), evaluation=list(EVAL), arms=list(ARMS), tasks=list(TASKS),
                practice_per_seed=PRACTICE, holdout_per_task=HELDOUT_PER_TASK,
                primary="Mean paired held-out success, preserved minus standardized, collapsed by independent seed.",
                secondary="Seed-level 95% percentile bootstrap, 4000 resamples. No multiplicity adjustment.",
                checkpoint="Genesis 1.4 latest age, preserved arm, lowest seed, independent of performance.",
                state_protocol="Shared archived neural state. Each held-out episode receives a fresh clone of learned "
                               "local evidence. Cold audits and held-out outcomes never enter training.",
                files={str(p.relative_to(ROOT.parent)).replace("\\","/"):digest(p.read_bytes()) for p in SOURCES})


def write_json(path,data):
    path.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")


def write_csv(path,rows):
    with path.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def summarize(rows):
    return [dict(arm=arm,task=task,episodes=len(group),**{k:mean(row[k] for row in group) for k in MEASURES})
            for arm in ARMS for task in ("all",*TASKS)
            if (group:=[r for r in rows if r["arm"]==arm and task in ("all",r["task"])])]


def paired(rows):
    seeds=sorted({r["seed"] for r in rows})
    rng=random.Random(14114)
    indices=[rng.choices(seeds,k=len(seeds)) for _ in range(4000)]
    result=[]
    for arm in ARMS[1:]:
        for task in ("all",*TASKS):
            subset=[r for r in rows if task in ("all",r["task"]) and r["arm"] in ("preserved",arm)]
            for metric in ("success","cold_brier","prior_brier","posterior_brier","energy_spent","useful"):
                values={s:mean(r[metric] for r in subset if r["seed"]==s and r["arm"]=="preserved")
                          -mean(r[metric] for r in subset if r["seed"]==s and r["arm"]==arm) for s in seeds}
                samples=sorted(mean(values[s] for s in sample) for sample in indices)
                result.append(dict(treatment="preserved",control=arm,task=task,metric=metric,n_seeds=len(seeds),
                                   difference=mean(values.values()),low95=samples[100],high95=samples[3899]))
    return result


def observatory(out, trace, bank, replays):
    provenance={m.id:asdict(m) for m in bank}
    matched={(r["seed"],r["task"],r["scene_seed"]):r for r in replays}
    frames=[]
    for row in trace:
        key=row["seed"],row["task"],row["scene_seed"]
        chosen=row["options"][row["choice"]] if row["choice"] is not None else None
        world=Settlement(row["scene_seed"])
        frames.append(dict(tick=len(frames)+1,age=944,body=row["body"],
                           action={"kind":"commit" if chosen else "rest","chosen":chosen},
                           outcome=row["outcome"],prediction=max(row["posterior"]),
                           observed_energy_delta=-row["energy_spent"],curiosity=row["opportunity"],
                           observation=row["options"],book=row["book"],question=row["question"],
                           prediction_before=row["prior"],prediction_after=row["posterior"],
                           candidate_actions=row["candidates"],
                           retrieved=[[dict(record=provenance[i],relevance=w) for i,w in item]
                                      for item in row["retrieved_records"]],
                           memory_formed=row["added_local_memory"],counterfactual=matched.get(key),
                           map=[(p,tile) for p,tile in world.tiles.items()]))
    observe(out,frames)
    path=out/"observatory.html"
    html=path.read_text(encoding="utf-8").replace("Omega Human Experiment","Memory Across Worlds")
    html=html.replace('<a href="life.jsonl">Life trace</a>','<a href="decisions.jsonl">Decision traces</a>')
    html=html.replace('<pre id="observed"></pre>','<svg id="map" viewBox="0 0 340 260" style="width:100%;max-width:420px" aria-label="Settlement map"></svg><pre id="observed"></pre>')
    html=html.replace('const {body,action,outcome,...remaining}=s;',"""const map=$('map'); map.replaceChildren();
 const colors={river:'#34779c',bridge:'#dfbd82',road:'#a48c68',market:'#ddb25b',workshop:'#bb8360',
 school:'#967cb4',house:'#c8ac88',well:'#55b7c5',field:'#7d9e4d',wood:'#42684e',wall:'#374455'};
 function tile(x,y,color,size){const r=document.createElementNS('http://www.w3.org/2000/svg','rect');
 r.setAttribute('x',20*(x-100)+(20-size)/2);r.setAttribute('y',20*(y-100)+(20-size)/2);
 r.setAttribute('width',size);r.setAttribute('height',size);r.setAttribute('fill',color);map.append(r);}
 for(const [[x,y],t] of s.map)tile(x,y,colors[t]||'#58745b',19);
 for(const o of s.observation)tile(...o.position,'#f7d885',9);
 tile(...s.body.position,'#ffffff',11);
 const {body,action,outcome,map:terrain,...remaining}=s;""")
    path.write_text(html,encoding="utf-8")


def report(out,summary,contrasts,replays,practices):
    primary=next(r for r in contrasts if (r["control"],r["task"],r["metric"])==("standardized","all","success"))
    p=lambda x:f"{100*x:+.1f}"
    lines=["# Digital Genesis 1.4.1 - The Memory That Crossed Worlds","",
           "## Diagnosis of 1.4","",
           "The original actions and neural inputs replayed exactly. Across 432 preserved decisions the adapter "
           "made 14 semantic lookups, all for settlement keys, and zero for archived Earth keys. The archived "
           "spatial records were stored separately. Removing one old spatial record and one old semantic "
           "record or shuffling old contexts changed no action or neural input in the archived runs. The book "
           "was reachable on 21 ticks, with zero selected reads.","",
           "## Held-out comparison","",
           f"Preserved minus standardized success was **{p(primary['difference'])} percentage points** "
           f"(95% seed bootstrap {p(primary['low95'])} to {p(primary['high95'])}, "
           f"{primary['n_seeds']} paired seeds).","",
           "| Arm | Success | Cold Brier | After practice | After investigation | Read / trial | Energy / trial |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for r in summary:
        if r["task"]=="all":
            lines.append(f"| {r['arm']} | {r['success']:.1%} | {r['cold_brier']:.3f} | {r['prior_brier']:.3f} | "
                         f"{r['posterior_brier']:.3f} | {r['read']:.2f} | {r['energy_spent']:.2f} |")
    lines.extend(("", "| Task | Preserved | Standardized | Relevant removed | Shuffled | Reference |",
                  "|---|---:|---:|---:|---:|---:|"))
    for task in TASKS:
        lines.append(f"| {task} | "+" | ".join(f"{r['success']:.1%}" for r in summary if r["task"]==task)+" |")
    lines.extend(("",f"With one retrieved record removed, {sum(r['changed'] for r in replays)} of "
                  f"{len(replays)} held-out replays changed the committed object. The longer practice and held-out "
                  "logs separate action changes from information that improved success or the forecast. "
                  "They also record verified claims, computation slots and energy costs. "
                  "The learning-time proxy is the first practice episode ending a run of three successes.",
                  "", "## Interpretation", "",
                  "The bridge encodes generic perceptual properties and observed outcomes. It supplies neither a "
                  "mapping of old objects to new objects nor the live answer. The similarity weights are engineered. "
                  "The ledger is reconstructed from past recorded observations rather than recovered by native "
                  "memory recall. This tests whether those outcomes help a supplied bridge, and leaves spontaneous "
                  "discovery of a cross-world representation open. Old stock observations are predictive. The archive "
                  "contains effort costs, while the new workshop applies the charge after a delay. The archive "
                  "does not establish that Omega previously learned a delayed cost.",
                  "", "Books are reachable scene objects with finite, sometimes incomplete or incorrect statements. "
                  "The chosen Read action uses the motor's existing reach primitive and incurs energy and time costs. "
                  "An estimate of source reliability can update from directly checked claims during practice. "
                  "Read is a supplied affordance. Independent selection of that affordance is observable. This is "
                  "separate from discovering how writing works.",
                  "", "All task outcomes use the same body and local menu. A rule-based motor proposal is the reference "
                  "and receives the same modeled neural debit. Old Earth coordinates and partner IDs never score new "
                  "objects. Three short practice instances per family precede held-out visual variants. The test "
                  "varies seeded scenes within one procedural settlement, with fixed low-level dynamics.", ""))
    (out/"REPORT.md").write_text("\n".join(lines),encoding="utf-8")


def evaluate(out,seeds,saved,bank):
    rows,practice,chronology,replays=[],[],[],[]
    for seed in seeds:
        for arm in ARMS:
            available=shuffled(bank,seed) if arm=="shuffled" else bank
            learner=Predictor(available)
            cold=Predictor(available)
            run=[]
            for i in range(PRACTICE):
                e=run_task(saved,learner,arm,seed*1000+i,TASKS[i%len(TASKS)],True)
                run.append(e["success"])
                chronology.append(dict(seed=seed,**e))
            streak=next((i+3 for i in range(len(run)-2) if sum(run[i:i+3])==3),None)
            practice.append(dict(seed=seed,arm=arm,successes=sum(run),episodes=PRACTICE,first_three_successes=streak,
                                 verified_book_checks=len(learner.document),book_reliability=learner.book_reliability))
            for j,task in enumerate(TASKS):
                for i in range(HELDOUT_PER_TASK):
                    scene_seed=seed*1000+400+10*j+i
                    baseline=run_task(saved,cold,arm,scene_seed,task)
                    cpu=process_time()
                    e=run_task(saved,learner,arm,scene_seed,task)
                    elapsed=process_time()-cpu
                    e.update(seed=seed,cold_brier=baseline["prior_brier"],cpu_seconds=elapsed)
                    chronology.append(e)
                    rows.append(dict(seed=seed,arm=arm,task=task,scene_seed=scene_seed,**{k:e[k] for k in MEASURES}))
                    if arm=="preserved" and i==0:
                        all_records=[(mid,w) for weights in e["retrieved_records"] for mid,w in weights]
                        if all_records:
                            removed=max(all_records,key=lambda r:r[1])[0]
                            alt=run_task(saved,learner,arm,scene_seed,task,excluded=removed)
                            replays.append(dict(seed=seed,task=task,scene_seed=scene_seed,removed=removed,
                                                actual=e["choice"],without_record=alt["choice"],
                                                changed=e["choice"]!=alt["choice"],
                                                success_delta=e["success"]-alt["success"],
                                                forecast_delta=e["prior_brier"]-alt["prior_brier"]))
        print(f"Paired seed {seed} complete",flush=True)
    summary,contrasts=summarize(rows),paired(rows)
    write_csv(out/"results.csv",rows)
    write_csv(out/"summary.csv",summary)
    write_csv(out/"paired.csv",contrasts)
    write_csv(out/"practice.csv",practice)
    write_json(out/"counterfactuals.json",replays)
    with (out/"decisions.jsonl").open("w",encoding="utf-8") as f:
        for e in chronology:
            f.write(json.dumps(e,separators=(",",":"))+"\n")
    observatory(out,[e for e in chronology if e["seed"]==seeds[0] and e["arm"]=="preserved"],bank,replays)
    report(out,summary,contrasts,replays,practice)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("develop","lock","evaluate"))
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    protocol=config()
    if args.mode=="lock":
        with LOCK.open("x",encoding="utf-8") as f:
            json.dump(protocol,f,indent=2)
        return
    if args.mode=="evaluate" and protocol!=json.loads(LOCK.read_text(encoding="utf-8")):
        parser.error("protocol/source lock mismatch")
    if args.out is None:
        parser.error("--out is required")
    args.out.mkdir(parents=True)
    raw,saved=verified_checkpoint(SOURCE)
    checkpoint=args.out/"omega-1.4-final.pkl"
    checkpoint.write_bytes(raw)
    checkpoint.chmod(stat.S_IREAD)
    write_json(args.out/"migration.json",dict(sha256=digest(raw),identity=saved.core.id,age=saved.core.age,
                                             cognitive_state=cognitive_hashes(saved.core,saved.model)))
    write_json(args.out/"experiment_config.json",protocol)
    bank=memory_bank()
    write_json(args.out/"archive_records.json",[asdict(m) for m in bank])
    evaluate(args.out,DEV if args.mode=="develop" else EVAL,saved,bank)


if __name__=="__main__":
    main()
