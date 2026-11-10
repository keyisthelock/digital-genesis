"""Checkpoint migration, short matched life trials and offline observation."""

import argparse
import csv
import json
from pathlib import Path
import pickle
import signal
import stat
from statistics import mean
from time import process_time

from embodied import ARMS, DEV, EVAL, ROOT, SOURCE, TICKS, HumanTrial, archive, cognitive_hashes, digest
from settlement import Action, Body, DIRS, Settlement, WALKABLE, offset
from dawn import atomic, write_json


LOCK=ROOT/"protocol.lock.json"
SOURCES=("embodied.py","settlement.py","run_human.py","../genesis_1_3_4/social_trial.py",
         "../v03_social/cognition.py","../genesis_1_3_1/inquiry.py","../genesis_1_3_2/revision.py",
         "../genesis_1_1/model.py","../organism.py")


def protocol():
    return dict(version="1.4",source_sha256=json.loads(SOURCE.with_suffix(".json").read_text())["sha256"],
                source_selection="Last validated boundary, combined treatment, lowest archive pilot seed.",
                dev=list(DEV),eval=list(EVAL),arms=list(ARMS),ticks=TICKS,
                heldout_audit="Seven evaluator-only one-step probes on seed+91700, frozen original vs final forecaster.",
                primary="Survival, chosen actions and common audited energy forecast MAE. Technical pilot.",
                sources={name:digest((ROOT/name).read_bytes()) for name in SOURCES})


def checkpoint(path,trial):
    data=pickle.dumps(trial,protocol=5)
    atomic(path,data)
    write_json(path.with_suffix(".json"),dict(sha256=digest(data),tick=trial.world.tick,
                                             identity=trial.core.id,alive=trial.body.alive))


def csv_out(path,rows):
    with path.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def audit(trial):
    """The action battery scores models on new scenes and does not train either."""
    rows=[]
    for name in ("walk","drink","rest","grasp","work_empty","work_tool","trade"):
        s=Settlement(trial.seed+91700)
        sites={tile:p for p,tile in s.sites.items()}
        p={"drink":sites["well"],"rest":sites["house"],"grasp":sites["workshop"],
           "work_empty":sites["workshop"],"work_tool":sites["workshop"],"trade":sites["market"]}.get(name,s.spawn)
        b=Body(p,energy=49.,water=35.,fatigue=47.,holding="hand tool" if name=="work_tool" else None)
        if name=="walk":
            i,target=next((i,q) for i,d in enumerate(DIRS)
                          if (q:=offset(p,d)) in s.tiles and s.tiles[q] in WALKABLE)
            a=Action(name,target,i)
        else:
            a=Action("work" if name.startswith("work_") else name,p)
        local=s.local(b)
        old=trial.body
        trial.body=b
        original=trial.forecast(a,local,trial.frozen_model)[0][0]*10.
        learned=trial.forecast(a,local,trial.model)[0][0]*10.
        trial.body=old
        result=s.act(b,a)
        actual=b.energy-49.
        rows.append(dict(seed=trial.seed,arm=trial.arm,probe=name,success=int(result["success"]),
                         actual=actual,original_prediction=original,final_prediction=learned,
                         original_error=abs(actual-original),final_error=abs(actual-learned)))
    return rows


ACTION_NAMES=("walk","turn","eat","drink","rest","trade","grasp","work","read","inspect","ask","report","cooperate")


def life(path, trial, should_stop):
    path.mkdir()
    checkpoint(path/"initial.pkl",trial)
    history=[]
    first_cpu=process_time()
    brain_start=trial.core.brain.ops
    updates=trial.core.brain.updates
    with (path/"life.jsonl").open("w",encoding="utf-8") as stream:
        for _ in range(TICKS):
            if should_stop() or not trial.body.alive:
                break
            event=trial.step()
            history.append(event)
            stream.write(json.dumps(event,separators=(",",":"))+"\n")
    elapsed=process_time()-first_cpu
    checkpoint(path/"final.pkl",trial)
    if not trial.body.alive:
        checkpoint(path/"death.pkl",trial)
    review=audit(trial)
    row=dict(seed=trial.seed,arm=trial.arm,ticks=trial.world.tick,alive=int(trial.body.alive),
             reached_horizon=int(trial.world.tick==TICKS and trial.body.alive),death=trial.body.cause or "",
             age=trial.core.age,energy=trial.body.energy,water=trial.body.water,fatigue=trial.body.fatigue,
             temperature=trial.body.temperature,health=trial.body.health,coins=trial.body.coins,
             visits=len(trial.core.visited),new_relationships=sum(s["bond"]>=.15 for s in trial.core.social.people.values()),
             new_trust_peers=sum(peer>=101 and kind=="hint" for peer,kind in trial.core.local_life.trust),
             structured_questions=trial.metrics["structured"],hints_received=trial.metrics["received_hints"],
             hints_checked=trial.metrics["checked_hints"],retained=trial.metrics["retained"],
             **{k:trial.metrics[k] for a in ACTION_NAMES for k in ("action_"+a,"successful_"+a)},
             life_error=trial.metrics["error"]/max(1,len(history)),
             frozen_error_same_actions=trial.metrics["frozen_error"]/max(1,len(history)),
             audit_original_mae=mean(r["original_error"] for r in review),
             audit_final_mae=mean(r["final_error"] for r in review),
             neural_ops=trial.core.brain.ops-brain_start,neural_updates=trial.core.brain.updates-updates,
             forecast_ops=trial.metrics["forecast_ops"],inquiry_ops=trial.metrics["inquiry_ops"],
             message_energy=trial.metrics["message_energy"],energy_spent=trial.metrics["energy_spent"],
             cpu_seconds=elapsed)
    write_json(path/"chronology.json",history)
    observe(path,history)
    return row,review


def observe(path,history):
    raw=json.dumps(history,separators=(",",":")).replace("<","\\u003c")
    html="""<!doctype html><html lang="en"><meta charset="utf-8"><title>Omega Human Experiment</title>
<style>body{background:#101c2a;color:#eef4fa;font:16px system-ui;margin:2rem auto;max-width:68rem;padding:0 1rem}
section{display:grid;grid-template-columns:170px 1fr;gap:1rem}svg,pre{background:#192c3e;padding:.7rem;border-radius:.5rem}
pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#8fe4cb}input{width:65%}</style>
<h1>Omega Human Experiment</h1><p>Recorded articulated pose and local perception. <a href="life.jsonl">Life trace</a></p>
<label>Tick <input id="tick" type="range" min="0" value="0"></label>
<section><svg id="pose" viewBox="0 0 130 180" aria-label="Recorded humanoid pose">
<circle cx="65" cy="27" r="13" fill="#8fe4cb"/><path id="torso" stroke="#8fe4cb" stroke-width="6"/>
<path id="left_arm" stroke="#b9d9e8" stroke-width="4"/><path id="right_arm" stroke="#b9d9e8" stroke-width="4"/>
<path id="left_leg" stroke="#b9d9e8" stroke-width="5"/><path id="right_leg" stroke="#b9d9e8" stroke-width="5"/>
</svg><pre id="condition"></pre></section><pre id="observed"></pre>
<script type="application/json" id="data">/*DATA*/</script><script>
const $=id=>document.getElementById(id), rows=JSON.parse($('data').textContent), tick=$('tick');
tick.max=Math.max(0,rows.length-1);
function limb(id,x,y,len,angle,tip){
 const r=angle*Math.PI/180, px=x+Math.sin(r)*len, py=y+Math.cos(r)*len;
 $(''+id).setAttribute('d','M '+x+' '+y+' L '+px+' '+py+' l '+tip+' 4');
}
function show(){
 const s=rows[Number(tick.value)]; if(!s)return;
 const b=s.body,j=b.joints;
 limb('torso',65,44,43,j.torso,0);
 limb('left_arm',56,50,37,j.left_arm,-(j.left_hand/18+3));
 limb('right_arm',74,50,37,j.right_arm,j.right_hand/18+3);
 limb('left_leg',58,85,56,j.left_leg,-(j.left_foot/9+6));
 limb('right_leg',72,85,56,j.right_leg,j.right_foot/9+6);
 $('condition').textContent=JSON.stringify({tick:s.tick,age:s.age,action:s.action,outcome:s.outcome,
   energy:b.energy,hydration:b.water,fatigue:b.fatigue,temperature:b.temperature,health:b.health,
   alive:b.alive,terminal_cause:b.cause,holding:b.holding,prediction:s.prediction,actual:s.observed_energy_delta},null,2);
 const {body,action,outcome,...remaining}=s;
 $('observed').textContent=JSON.stringify(remaining,null,2);
}
tick.oninput=show;show();
</script></html>"""
    atomic(path/"observatory.html",html.replace("/*DATA*/",raw).encode())


def report(out,rows):
    lines=["# Digital Genesis 1.4 - The Human Experiment","",
           "The verified 1.3.4 final checkpoint came from the combined arm of the lowest-numbered pilot seed. "
           "Omega's identity, age, neural weights, recurrent state, world model, episodic and semantic stores, "
           "partner estimates and hypothesis state were migrated. Old locations and partner identities remain "
           "in a separate legacy namespace. Radio packets in flight and body-specific proprioception do not carry over. "
           "Every arm starts with the same ordinary human energy, health, water, fatigue and resources.","",
           "| Arm | Horizon | Mean CPU s | Mean audit MAE before | Mean audit MAE after | Trades | Works | Verified hints |",
           "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for arm in ARMS:
        group=[r for r in rows if r["arm"]==arm]
        if group:
            a=lambda k:mean(r[k] for r in group)
            lines.append(f"| {arm} | {sum(r['reached_horizon'] for r in group)}/{len(group)} | "
                         f"{a('cpu_seconds'):.2f} | {a('audit_original_mae'):.3f} | {a('audit_final_mae'):.3f} | "
                         f"{sum(r['successful_trade'] for r in group)} | {sum(r['successful_work'] for r in group)} | "
                         f"{sum(r['hints_checked'] for r in group)} |")
    lines.extend(("", "The one-step audit uses unseen physical scenes and common scripted evaluator probes. "
                  "It measures energy forecast transfer and adaptation. It does not measure independently planned "
                  "task completion in a new world. The three-seed pilot gives descriptive comparisons.","",
                  "The human prototype uses a top-down grid with joint-limited procedural poses. Walking, turning, grasping, "
                  "reach, collisions and physiology are abstract. PyBullet and MuJoCo were absent in the local runtime. "
                  "Neither GPU nor rigid-body physics was benchmarked. The village and its documents are fictional, "
                  "with preindustrial objects as inspiration. NPCs follow local memory and occupational routines.","",
                  "All arms share the affordance ranker. The preserved and standardized-memory arms use the same archived "
                  "motor weights, recurrent state and world-model weights. The standardized arm clears episodic, semantic "
                  "and social priors. The reference arm uses the existing WeightedPolicy and fixed persistence forecast. "
                  "Limited inquiry keeps the ordinary action menu and learned controller but disables active question "
                  "scoring and structural revision. The normal trial leaves the stagnation influence off.","",
                  "The affordance adapter supplies needs and action availability. Any rendered question originates in a "
                  "selected internal structure. Working, trading or surviving in this scaffold does not establish human-level cognition.",""))
    atomic(out/"REPORT.md","\n".join(lines).encode())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("pilot","lock","evaluate"))
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    cfg=protocol()
    if args.mode=="lock":
        with LOCK.open("x",encoding="utf-8") as f:
            json.dump(cfg,f,indent=2)
        return
    if args.mode=="evaluate" and cfg!=json.loads(LOCK.read_text()):
        p.error("protocol/source lock mismatch")
    if args.out is None:
        p.error("--out is required")
    args.out.mkdir(parents=True)
    raw,core,model=archive()
    path=args.out/"omega-original.pkl"
    atomic(path,raw)
    path.chmod(stat.S_IREAD)
    write_json(args.out/"migration.json",dict(identity=core.id,age=core.age,source_sha256=digest(raw),
               source_cognition=cognitive_hashes(core,model),nontransferable=["old coordinates and peer IDs are namespaced",
               "old in-flight packets are archived only","old physical reserves replaced by matched human starting state",
               "new senses and joint constraints are represented by typed affordances"]))
    write_json(args.out/"experiment_config.json",cfg)
    stop=False
    def halt(*unused):
        nonlocal stop
        stop=True
    signal.signal(signal.SIGINT,halt)
    should_stop=lambda:stop or (args.out/"STOP").exists()
    rows,review=[],[]
    for seed in DEV if args.mode=="pilot" else EVAL:
        base=args.out/str(seed)
        base.mkdir()
        for arm in ARMS:
            row,audit_rows=life(base/arm,HumanTrial(seed,arm,core,model),should_stop)
            rows.append(row)
            review.extend(audit_rows)
            print(f"{seed} {arm}: {row['ticks']} ticks, alive={row['alive']}, questions={row['structured_questions']}",
                  flush=True)
            if should_stop():
                break
        if should_stop():
            break
    csv_out(args.out/"results.csv",rows)
    csv_out(args.out/"audit.csv",review)
    report(args.out,rows)


if __name__=="__main__":
    main()
