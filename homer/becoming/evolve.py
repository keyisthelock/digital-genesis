"""Offline evolution of task-to-method bits, with frozen held-out checks."""
import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import random

from .curriculum import INTRO_SKILLS, generate, score, solve_method
from .runner import archive_hashes

SKILLS=tuple(s for s in INTRO_SKILLS if s not in ("history","poetry","access","design"))
SPLITS={"training":tuple(range(18000,18012)),"validation":tuple(range(18100,18108)),
        "heldout":tuple(range(18200,18220))}
SEED=180018
GENERATIONS=6
POPULATION=10


@dataclass(frozen=True)
class Candidate:
    id: int
    parent: int | None
    bits: tuple


def evaluate(candidate, tasks):
    result={s:[0,0] for s in SKILLS}
    for task in tasks:
        bit=candidate.bits[SKILLS.index(task.skill)]
        answer=solve_method(task,"worked" if bit else "shortcut")
        result[task.skill][0]+=int(score(task,answer)[0])
        result[task.skill][1]+=1+bit
    return {"passed":sum(v[0] for v in result.values()),"trials":len(tasks),
            "method_cost":sum(v[1] for v in result.values()),
            "by_skill":{k:{"passed":v[0],"cost":v[1]} for k,v in result.items()}}


def rank(metrics):
    return (metrics["passed"],-metrics["method_cost"])


def qualifies(candidate, baseline):
    return rank(candidate)>rank(baseline) and all(
        candidate["by_skill"][s]["passed"]>=baseline["by_skill"][s]["passed"] for s in SKILLS)


def task_splits():
    seen=set()
    result={}
    for split,seeds in SPLITS.items():
        tasks=result.setdefault(split,[])
        for seed in seeds:
            for skill in SKILLS:
                for index in range(100):
                    task=generate(skill,seed,index)
                    signature=json.dumps(task.packet(),sort_keys=True)
                    if signature not in seen:
                        seen.add(signature)
                        tasks.append(task)
                        break
                else:
                    raise ValueError("Curriculum could not create a distinct instance")
    return result


def run(out):
    before=archive_hashes()
    out.mkdir(parents=True,exist_ok=False)
    tasks=task_splits()
    rng=random.Random(SEED)
    baseline=Candidate(-1,None,(1,)*len(SKILLS))
    shortcut=Candidate(-2,None,(0,)*len(SKILLS))
    pool=[Candidate(i,None,tuple(rng.randrange(2) for _ in SKILLS)) for i in range(POPULATION)]
    next_id=POPULATION
    lineage=[]
    final={}
    for generation in range(GENERATIONS):
        scored=[]
        for c in pool:
            train=evaluate(c,tasks["training"])
            scored.append((rank(train),c))
            lineage.append(dict(generation=generation,id=c.id,parent=c.parent,bits=c.bits,training=train))
            final[c.id]=c
        elite=[c for _,c in sorted(scored,key=lambda x:x[0],reverse=True)[:3]]
        if generation+1<GENERATIONS:
            pool=[]
            for i in range(POPULATION):
                parent=elite[i%len(elite)]
                bits=list(parent.bits)
                if i>=3:
                    idx=rng.randrange(len(bits))
                    bits[idx]^=1
                pool.append(Candidate(next_id,parent.id,tuple(bits)))
                next_id+=1
    # Validation picks one candidate before the held-out labels are evaluated.
    candidate=max(elite,key=lambda c:rank(evaluate(c,tasks["validation"])))
    metrics={split:{name:evaluate(c,items) for name,c in
                    (("candidate",candidate),("worked_baseline",baseline),("shortcut_baseline",shortcut))}
             for split,items in tasks.items()}
    eligible=all(qualifies(metrics[split]["candidate"],metrics[split]["worked_baseline"])
                 for split in ("validation","heldout"))
    with (out/"lineage.jsonl").open("x",encoding="utf-8") as stream:
        for entry in lineage:
            stream.write(json.dumps(entry)+"\n")
    result=dict(seed=SEED,splits=SPLITS,skills=SKILLS,generations=GENERATIONS,population=POPULATION,
                policy=dict(id=candidate.id,parent=candidate.parent,bits=candidate.bits),
                metrics=metrics,promoted=eligible,archives=before,
                task_keys={split:[t.key for t in items] for split,items in tasks.items()})
    if eligible:
        (out/"promoted_adapter.json").write_text(json.dumps(result["policy"],indent=2),encoding="utf-8")
    assert archive_hashes()==before
    (out/"evolution.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    for split,arms in metrics.items():
        print(split,{k:(v["passed"],v["trials"],v["method_cost"]) for k,v in arms.items()})
    print("promoted",eligible)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("out",type=Path)
    run(p.parse_args().out)
