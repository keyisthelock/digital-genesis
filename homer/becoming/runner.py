"""Homer 1.8 goal selection, retrieval, verification and reflection."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import re
from time import perf_counter

from ..journal import Journal
from .curriculum import INTRO_SKILLS, REGISTRY, generate, score, solve_method
from .knowledge import Knowledge
from .model import TutorModel
from .provenance import WEIGHT_SHA, archive_hashes

ROOT=Path(__file__).resolve().parent
MODES=("memory","memory_off","tool","qwen_unaided","qwen_memory","qwen_tool")
SEED=18300


class GoalManager:
    def __init__(self, profile):
        self.tendencies=profile["tendencies"]

    def select(self, offered, attempts, feedback, budget):
        options=[]
        abandoned=[]
        for task in offered:
            if task.cost>budget or task.risk>0:
                continue
            seen=attempts[task.skill]
            if seen>=2:
                abandoned.append(task.skill)
                continue
            latest=feedback.get(task.skill)
            signals=dict(novelty=self.tendencies["novelty"]/(1+seen),
                         practice=self.tendencies["persistence"]*(.3+self.tendencies["reflection"])
                                  *bool(latest and not latest["passed"]),
                         competence_gap=.25 if not latest or not latest["passed"] else 0,
                         cost=-.12*task.cost, difficulty=-.06*task.level,
                         caution=-self.tendencies["caution"]*task.risk)
            options.append((sum(signals.values()),task,signals))
        if not options:
            return None,{"abandoned":abandoned}
        _, task, signals=max(options,key=lambda x:x[0])
        return task,dict(selected=task.key,score=round(sum(signals.values()),5),signals=signals,
                         candidates={t.key:round(v,5) for v,t,_ in options},abandoned=abandoned,
                         source="engineered_goal_manager")

    def reflect(self, task, memory):
        if not memory:
            return dict(choice="try",method="shortcut",basis="no recalled feedback")
        last=memory[0]
        if not last["passed"] and last["method"]=="shortcut":
            return dict(choice="change_strategy",method="worked",basis="prior shortcut failed")
        return dict(choice="retry",method=last["method"],basis="repeat previous method on new instance")


def recall(journal, skill):
    return [dict(id=e["event_id"],source=e["source_ref"],**e["metadata"])
            for e in journal.recent(limit=100)
            if e["event_type"]=="learning_result" and e["metadata"]["skill"]==skill][:2]


def packet(task, docs, events):
    return {**task.packet(),
            "sources":[{k:d[k] for k in ("id","text","provenance","confidence")} for d in docs],
            "experience":[{k:e[k] for k in ("id","source","passed","feedback","method")} for e in events]}


def classify_history(docs):
    for doc in docs:
        match=re.search(r"(\d+) successes in (\d+) native survival-and-eat trials",doc["text"])
        if match:
            return "supported" if match[1]==match[2] else "contradicted"
    return "unknown"


def episode(root, mode, model=None, skills=("slope","probability"), rounds=4, seed=SEED,
            profile=None):
    path=root/mode
    path.mkdir()
    journal=Journal(path/"life.sqlite3")
    library=Knowledge(path/"knowledge.sqlite3")
    library.seed()
    canonical=json.loads((ROOT/"HOMER_PERSONALITY_V2.json").read_text(encoding="utf-8"))
    cfg=json.loads(profile.read_text(encoding="utf-8")) if profile else canonical
    if any(cfg[k]!=canonical[k] for k in ("schema","agent","heritage","core_values")):
        raise ValueError("A personality revision must preserve identity and core values")
    if set(cfg["tendencies"])!=set(canonical["tendencies"]) or any(
            type(value) not in (int,float) or not 0<=value<=1 for value in cfg["tendencies"].values()):
        raise ValueError("Invalid tendency revision")
    goals=GoalManager(cfg)
    attempts=Counter()
    results=[]
    memory_on=mode in ("memory","qwen_memory")
    tool_on=mode in ("tool","qwen_tool")
    trace_dir=root/"HOMER_LEARNING_TRACES"
    try:
        with (trace_dir/f"{mode}.jsonl").open("x",encoding="utf-8") as trace:
            for turn in range(rounds):
                if (root/"STOP").exists():
                    break
                started=perf_counter()
                offer=[generate(s,seed,attempts[s]) for s in skills]
                histories={s:recall(journal,s) for s in skills} if memory_on else {}
                past={s:events[0] for s,events in histories.items() if events}
                task,selection=goals.select(offer,attempts,past,rounds-turn)
                if not task:
                    trace.write(json.dumps(dict(type="end",reason="no_eligible_goal",goal=selection))+"\n")
                    break
                events=histories.get(task.skill,[])
                docs=library.retrieve(task.skill,task.question,limit=1) if tool_on else []
                plan=goals.reflect(task,events)
                prepared=packet(task,docs,events)
                if model:
                    plan=dict(choice="consult_qwen",method="model",basis="fixed experimental arm")
                    answer,raw,error,latency=model.answer(prepared,task.skill)
                    origin="qwen_language_model"
                    if mode=="qwen_tool" and task.skill in ("slope","probability","gravity","stoichiometry","circuit"):
                        answer=solve_method(task,"worked")
                        origin="deterministic_tool"
                        plan=dict(choice="tool_method",method="worked",basis="fixed tool arm")
                elif tool_on:
                    answer=solve_method(task,"worked")
                    if task.skill=="history":
                        answer=classify_history(docs)
                    raw,error,latency,origin=None,None,0.,"deterministic_tool"
                    plan=dict(choice="tool_method",method="worked",basis="operator enabled tool arm")
                else:
                    answer=solve_method(task,plan["method"])
                    raw,error,latency,origin=None,None,0.,"bounded_method_policy"
                passed, feedback=score(task,answer)
                if error and origin=="qwen_language_model":
                    passed,feedback=False,"model_error"
                method="model" if origin=="qwen_language_model" else "worked" if tool_on else plan["method"]
                eid=journal.remember(subject="homer",event_type="learning_result",
                    summary=f"{task.skill}: {feedback}",source_type="system_event",source_ref=f"becoming:{mode}:{task.key}",
                    certainty="observed",metadata=dict(skill=task.skill,passed=passed,feedback=feedback,
                                                        method=method,links=[e["id"] for e in events]))
                results.append(dict(mode=mode,seed=seed,task=task.key,chapter=task.chapter,domain=task.domain,
                    skill=task.skill,turn=turn+1,passed=passed,score_type=feedback,origin=origin,
                    goal_origin=selection["source"],verifier="independent_deterministic_verifier",
                    qwen_called=bool(model),retrieved_experience=len(events),retrieved_sources=len(docs),
                    omega_motor_used=False,trained_policy_used=False,
                    inference_seconds=latency,wall_seconds=round(perf_counter()-started,5)))
                detail=dict(**results[-1],goal=selection,reflection=plan,model_input=prepared if model else None,
                            observation=task.packet(),memory_ids=[e["id"] for e in events],
                            knowledge=[{k:d[k] for k in ("id","digest","provenance")} for d in docs],
                            answer=answer,raw_model_output=raw,error=error,journal_event=eid)
                trace.write(json.dumps(detail,ensure_ascii=False)+"\n")
                trace.flush()
                attempts[task.skill]+=1
                print(mode,task.skill,passed,feedback,flush=True)
    finally:
        journal.close()
        library.close()
    return results


def write_csv(path, rows):
    with path.open("x",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(out, suite, port, profile=None):
    before=archive_hashes()
    out.mkdir(parents=True,exist_ok=False)
    (out/"HOMER_LEARNING_TRACES").mkdir()
    rows=[]
    if suite in ("vertical","expanded"):
        for mode in ("memory","memory_off"):
            # Each arm faces the identical two instances in the same order.
            rows.extend(episode(out,mode,skills=("slope",),rounds=2,profile=profile))
        skills=INTRO_SKILLS if suite=="vertical" else tuple(REGISTRY)
        rows.extend(episode(out,"tool",skills=skills,rounds=len(skills),profile=profile))
    elif suite=="qwen":
        model=TutorModel(port)
        for mode in ("qwen_unaided","qwen_memory"):
            rows.extend(episode(out,mode,model,skills=("slope",),rounds=2,profile=profile))
        rows.extend(episode(out,"qwen_tool",model,skills=("gravity","access","history","poetry"),rounds=4,profile=profile))
    else:
        model=TutorModel(port)
        rows.extend(episode(out,"qwen_curriculum",model,
                            skills=("logic","ecology","authentication","ethics","integrated",
                                    "secure_review","dedup_program"),rounds=7,profile=profile))
    if rows:
        write_csv(out/"HOMER_CAPABILITY_RESULTS.csv",rows)
    assert archive_hashes()==before
    (out/"manifest.json").write_text(json.dumps(dict(suite=suite,archives=before,
        qwen=WEIGHT_SHA if suite.startswith("qwen") else None,
        max_calls={"qwen":8,"qwen_curriculum":7}.get(suite,0),
        human_intervention=False),indent=2),encoding="utf-8")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--suite",choices=("vertical","qwen","expanded","qwen_curriculum"),default="vertical")
    p.add_argument("--port",type=int,default=11440)
    p.add_argument("--personality",type=Path)
    args=p.parse_args()
    run(args.out,args.suite,args.port,args.personality)
