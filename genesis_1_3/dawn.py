"""Explicit launcher, crash recovery and read-only monitoring for Genesis 1.3."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import pickle
import sys
import threading
import time

from population import ARMS, CAP, OPTIONS, PHASES, POPULATION, REGIONS, ROOT, Population, load_founder, means, outcomes
from cognitive import Frame

SESSION_SECONDS = 28800
CHECKPOINT_SECONDS = 900
MIDPOINT_SECONDS = 14400
FINAL_RESERVE = 45
ROUND_SECONDS = 1.
PHASE_TICKS = 5750
SEEDS = (13031,13032,13033,13034)


def utc():
    return datetime.now(timezone.utc).isoformat()


def atomic(path, data):
    temp = path.with_name(path.name+".tmp")
    with temp.open("wb") as file:
        file.write(data)
        file.flush()
        os.fsync(file.fileno())
    for attempt in range(6):
        try:
            os.replace(temp,path)
            return
        except PermissionError:
            if attempt==5:
                raise
            time.sleep(.04)


def write_json(path, value):
    atomic(path,(json.dumps(value,indent=2)+"\n").encode())


@contextmanager
def writer_lock(out):
    import msvcrt
    with (out/"writer.lock").open("a+b") as handle:
        if not handle.tell():
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        except OSError as error:
            raise RuntimeError("This run already has a writer") from error
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def protocol(smoke=False):
    paths = [ROOT/name for name in ("dawn.py","population.py","cognitive.py","founder/trained_32.json","founder/model.json")]
    return dict(version="1.3",smoke=smoke,regions=REGIONS,arms=ARMS,seeds=SEEDS,phase_order=PHASES,
                phase_ticks=PHASE_TICKS,round_seconds=ROUND_SECONDS,duration_seconds=SESSION_SECONDS,
                midpoint_seconds=MIDPOINT_SECONDS,checkpoint_seconds=CHECKPOINT_SECONDS,
                start_population=POPULATION,cap=CAP,sources={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in paths})


def populations(phase_ticks=PHASE_TICKS):
    gene,model = load_founder()
    return [Population(region,arm,seed,gene,model,phase_ticks) for region,seed in zip(REGIONS,SEEDS) for arm in ARMS]


def checkpoint(out, state):
    tick = state["populations"][0].world.tick
    generation = state["serial"]+1
    stem = f"{generation:04d}-{tick:06d}"
    chunk = f"events-{stem}.jsonl.gz"
    queues = [p.events for p in state["populations"]]
    lines = [json.dumps(dict(region=p.region,arm=p.arm,**event),separators=(",",":"))
             for p,events in zip(state["populations"],queues) for event in events]
    atomic(out/chunk,gzip.compress(("\n".join(lines)+("\n" if lines else "")).encode(),mtime=0))
    for p in state["populations"]:
        p.events = []
    saved = dict(state,serial=generation,archives=[*state["archives"],chunk])
    try:
        data = pickle.dumps(saved,protocol=5)
        name = f"state-{stem}.pkl"
        atomic(out/name,data)
        write_json(out/"latest.json",dict(file=name,sha256=digest(data),tick=tick,serial=generation))
    except BaseException:
        for p,events in zip(state["populations"],queues):
            p.events = events
        raise
    state.update(serial=generation,archives=saved["archives"])


def restore(out):
    pointer = json.loads((out/"latest.json").read_text())
    name = pointer["file"]
    if not name.startswith("state-") or Path(name).name!=name or not name.endswith(".pkl"):
        raise ValueError("invalid checkpoint name")
    data = (out/name).read_bytes()
    if digest(data)!=pointer["sha256"]:
        raise ValueError("checkpoint checksum mismatch")
    # This local run directory is trusted operator data. No external pickle input exists.
    state = pickle.loads(data)
    if any(not (out/name).is_file() for name in state["archives"]):
        raise ValueError("checkpoint archive is incomplete")
    return state


def status(out, state, stage, elapsed):
    metrics = [p.metrics() for p in state["populations"]]
    value = dict(stage=stage,updated_at=utc(),elapsed_seconds=round(elapsed,1),
                 deadline_utc=state["deadline_utc"],tick=metrics[0]["tick"],checkpoint=state["serial"],
                 populations=metrics)
    write_json(out/"status.json",value)
    return value


def audit(population, deadline):
    late = population.latest_gene
    results = []
    for label,gene in (("founder",population.first_gene),("latest_max_generation",late)):
        if time.monotonic()+2>=deadline:
            break
        sample = Population(population.region,population.arm,population.seed+50000,gene,
                            population.model,5,frozen=True)
        for _ in range(25):
            if time.monotonic()+1>=deadline:
                break
            sample.step()
        results.append(dict(genome=label,generation=population.generation if label!="founder" else 0,
                            **sample.metrics()))
    final = []
    truth = [outcomes(population.rule(),c) for c in OPTIONS]
    unseen = [outcomes(sample.rule(),c) for c in OPTIONS] if results else []
    for body in population.organisms:
        predictions = means(body.lifetime.beliefs.weights)
        scores = [sum(abs(a-x)+abs(b-y) for (a,b),(x,y) in zip(predictions,target))/4
                  for target in (truth,unseen)] if unseen else [None,None]
        final.append(dict(id=body.id,generation=body.generation,beliefs=body.lifetime.best(),
                          local_error=scores[0],unseen_rule_error=scores[1],forecast=predictions))
    return dict(region=population.region,arm=population.arm,frozen_genome_trials=results,live_belief_audit=final)


def report(out,state,stage,deadline):
    data = [p.metrics() for p in state["populations"]]
    audits = []
    for p in state["populations"]:
        if time.monotonic()+3>=deadline:
            break
        audits.append(audit(p,deadline))
    write_json(out/"final_metrics.json",dict(stage=stage,populations=data,audits=audits,
                                           archive_manifest=state["archives"],round_cpu_seconds=state["cpu"]))
    rows = ["# Digital Genesis 1.3 — The Dawn of Thought","",
            f"Session status **{stage}**. Matched simulated ticks **{data[0]['tick']}**.","",
            "| Region | Arm | Living | Births | Max generation | Inquiries | Symbol packets delivered |",
            "|---|---|---:|---:|---:|---:|---:|"]
    for p in data:
        questions = sum(p.get(f"inquiry_{k}",0) for k in ("trial","library","peer"))
        rows.append(f"| {p['region']} | {p['arm']} | {p['alive']} | {p['births']} | {p['max_generation']} | "
                    f"{questions} | {p.get('packets_delivered',0)} |")
    rows.extend(["","| Region | Arm | Validated social predictions | Mean self-model error | Food acquired | Neural energy |",
                 "|---|---|---:|---:|---:|---:|"])
    for p in data:
        error = p.get("self_error_sum",0.)/max(1,p.get("self_count",0))
        rows.append(f"| {p['region']} | {p['arm']} | {p.get('social_correct',0)}/{p.get('social_validated',0)} | "
                    f"{error:.3f} | {p.get('food',0.):.2f} | {p.get('neural_energy',0.):.3f} |")
    rows.extend(["",f"Accumulated population stepping used **{state['cpu']:.3f} CPU seconds**.",
                 "The JSON audit records the frozen founder and latest highest-generation genotype, plus living agents' "
                 "predictions on the local and independently generated rule. The archives preserve the exact question "
                 "fields, observed evidence, follow-up actions, symbol frames, new associations, births and deaths.",
                 "", "The symbolic grammar and hypothesis family were supplied. Learned signal weights, associations "
                 "and decisions are measured inside that scaffold. The comparison varies both symbolic language and "
                 "foundational references. Each region has one paired seed. These observations cannot establish "
                 "consciousness or general intelligence.","",
                 "| Region | Arm | Frozen founder food | Frozen later genome food | Local belief MAE | Unseen rule MAE |",
                 "|---|---|---:|---:|---:|---:|"])
    for item in audits:
        trials = item["frozen_genome_trials"]
        beliefs = item["live_belief_audit"]
        if len(trials)==2:
            averages = [sum(b[key] for b in beliefs)/len(beliefs) if beliefs else None
                        for key in ("local_error","unseen_rule_error")]
            formatted = [f"{value:.2f}" if value is not None else "—" for value in averages]
            rows.append(f"| {item['region']} | {item['arm']} | {trials[0].get('food',0):.2f} | "
                        f"{trials[1].get('food',0):.2f} | {formatted[0]} | {formatted[1]} |")
    rows.extend(["","Archived examples of organism-initiated inquiries and messages",""])
    found = set()
    for name in state["archives"]:
        if time.monotonic()+3>=deadline or len(found)>=5:
            break
        with gzip.open(out/name,"rt",encoding="utf-8") as file:
            for line in file:
                if time.monotonic()+3>=deadline or len(found)>=5:
                    break
                if '"kind":"inquiry"' not in line and '"kind":"symbol"' not in line:
                    continue
                event = json.loads(line)
                label = event.get("channel") or event["frame"]["act"]
                if label in found:
                    continue
                found.add(label)
                raw = event.get("frame") or {k:event[k] for k in ("channel","topic","settings","hypothesis","uncertainty","trigger")}
                rows.append(f"- {event['region']}/{event['arm']}, tick {event['tick']}, organism "
                            f"{event.get('id',event.get('sender'))}. `{json.dumps(raw,separators=(',',':'))}`")
                if event.get("frame"):
                    rows.append(f"  {Frame.parse(event['frame']).render()}")
    atomic(out/"REPORT.md",("\n".join(rows)+"\n").encode())


def live(out,resume):
    with writer_lock(out):
        now = time.time()
        startup = time.monotonic()
        if resume:
            state = restore(out)
            if json.loads((out/"protocol.json").read_text())!=json.loads(json.dumps(protocol())):
                raise ValueError("run protocol or source files changed")
            previous = json.loads((out/"status.json").read_text()) if (out/"status.json").exists() else {}
            if previous.get("stage") in ("finished","deadline"):
                raise ValueError("session already finalized")
            remaining = min(state["remaining"],state["deadline_epoch"]-now)
            if remaining<=FINAL_RESERVE:
                raise ValueError("the original session has insufficient time to resume")
        else:
            write_json(out/"protocol.json",protocol())
            state = dict(populations=populations(),serial=0,archives=[],cpu=0.,deadline_epoch=now+SESSION_SECONDS,
                         deadline_utc=datetime.fromtimestamp(now+SESSION_SECONDS,timezone.utc).isoformat(),
                         remaining=SESSION_SECONDS)
            remaining = SESSION_SECONDS-(time.monotonic()-startup)
        origin = time.monotonic()
        end = origin+remaining
        closed = threading.Event()

        def watchdog():
            if not closed.wait(max(0.,end-time.monotonic())):
                os._exit(124)

        threading.Thread(target=watchdog,daemon=True,name="session-cutoff").start()
        elapsed = lambda: SESSION_SECONDS-max(0.,end-time.monotonic())
        last_save = elapsed()
        next_checkpoint = (int(last_save//CHECKPOINT_SECONDS)+1)*CHECKPOINT_SECONDS
        due = origin
        next_status = origin
        stage = "finished"
        try:
            state["remaining"] = max(0.,end-time.monotonic())
            checkpoint(out,state)
            status(out,state,"running",elapsed())
            while state["populations"][0].world.tick<PHASE_TICKS*len(PHASES):
                current = time.monotonic()
                if end-current<=FINAL_RESERVE:
                    stage = "deadline"
                    break
                if current<due:
                    time.sleep(min(.25,due-current))
                    continue
                started = time.process_time()
                for p in state["populations"]:
                    p.step()
                state["cpu"] += time.process_time()-started
                due = max(due+ROUND_SECONDS,time.monotonic())
                passed = elapsed()
                if passed>=next_checkpoint:
                    state["remaining"] = max(0.,end-time.monotonic())
                    checkpoint(out,state)
                    next_checkpoint = (int(passed//CHECKPOINT_SECONDS)+1)*CHECKPOINT_SECONDS
                if passed>=MIDPOINT_SECONDS and not (out/"midpoint.json").exists():
                    value = status(out,state,"running",passed)
                    value["checkpoint_checksum_valid"] = verify_latest(out)
                    value["matched_tick"] = len({p["tick"] for p in value["populations"]})==1
                    value["extinct_populations"] = [f"{p['region']}/{p['arm']}" for p in value["populations"] if not p["alive"]]
                    write_json(out/"midpoint.json",value)
                if current>=next_status:
                    status(out,state,"running",passed)
                    next_status = current+30
        except KeyboardInterrupt:
            stage = "paused"
        except BaseException:
            # An interrupted round is never published. The last complete checkpoint remains authoritative.
            if (out/"latest.json").exists():
                status(out,restore(out),"crashed",elapsed())
            raise
        else:
            if time.monotonic()>=end:
                return
        finally:
            if sys.exc_info()[0] is not None:
                closed.set()
        try:
            # Ctrl+C can arrive halfway through a paired round. Save only complete rounds.
            if len({p.world.tick for p in state["populations"]})!=1 or stage=="paused":
                state = restore(out)
            state["remaining"] = max(0.,end-time.monotonic())
            checkpoint(out,state)
            status(out,state,"finalizing" if stage!="paused" else stage,elapsed())
            if stage!="paused":
                report(out,state,stage,end)
                status(out,state,stage,elapsed())
        finally:
            closed.set()


def verify_latest(out):
    pointer = json.loads((out/"latest.json").read_text())
    return digest((out/pointer["file"]).read_bytes())==pointer["sha256"]


def monitor(out, midpoint):
    name = "midpoint.json" if midpoint else "status.json"
    while True:
        if (out/name).exists():
            print((out/name).read_text(encoding="utf-8"))
            return
        if not midpoint:
            raise FileNotFoundError(out/name)
        if (out/"status.json").exists():
            current = json.loads((out/"status.json").read_text())
            deadline = datetime.fromisoformat(current["deadline_utc"])
            if current["stage"] in ("finished","deadline","crashed","paused") or datetime.now(timezone.utc)>=deadline:
                print(json.dumps(current,indent=2))
                return
        time.sleep(10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    for flag in ("run","resume","monitor","smoke"):
        modes.add_argument("--"+flag,action="store_true")
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--midpoint",action="store_true")
    args = parser.parse_args()
    if args.monitor:
        monitor(args.out,args.midpoint)
    elif args.smoke:
        smoke(args.out)
    else:
        if args.run:
            args.out.mkdir(parents=True,exist_ok=False)
        live(args.out,args.resume)


def smoke(out):
    out.mkdir(parents=True,exist_ok=False)
    start = time.process_time()
    state = dict(populations=populations(60),serial=0,archives=[],cpu=0.,deadline_epoch=0.,
                 deadline_utc=utc(),remaining=0.)
    for _ in range(300):
        for p in state["populations"]:
            p.step()
    state["cpu"] = time.process_time()-start
    checkpoint(out,state)
    original = restore(out)
    recovered = restore(out)
    for group in (original,recovered):
        for _ in range(5):
            for p in group["populations"]:
                p.step()
    assert pickle.dumps(original)==pickle.dumps(recovered)
    status(out,state,"smoke",0)
    report(out,state,"smoke",time.monotonic()+30)
    print(json.dumps(dict(cpu_seconds=state["cpu"],cpu_ms_per_round=1000*state["cpu"]/300,
                          checkpoint_bytes=(out/json.loads((out/"latest.json").read_text())["file"]).stat().st_size,
                          populations=[p.metrics() for p in state["populations"]]),indent=2))


if __name__=="__main__":
    main()
