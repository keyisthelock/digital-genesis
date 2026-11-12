"""Build a local capability dashboard, combined CSV, and Godot replay."""
import argparse
from collections import defaultdict
import csv
from html import escape
import json
from pathlib import Path

from .runner import write_csv


def build(out, folders, evolution):
    out.mkdir(parents=True,exist_ok=False)
    traces=out/"HOMER_LEARNING_TRACES"
    traces.mkdir()
    rows=[]
    groups=defaultdict(list)
    for path in folders:
        with (path/"HOMER_CAPABILITY_RESULTS.csv").open(encoding="utf-8",newline="") as stream:
            subset=[dict(suite=path.name,**r) for r in csv.DictReader(stream)]
        rows.extend(subset)
        for row in subset:
            groups[path.name,row["mode"],row["domain"],row["origin"]].append(row)
        for trace in sorted((path/"HOMER_LEARNING_TRACES").glob("*.jsonl")):
            (traces/f"{path.name}_{trace.name}").write_bytes(trace.read_bytes())
    write_csv(out/"HOMER_CAPABILITY_RESULTS.csv",rows)
    summary=[]
    for (suite,mode,domain,origin),items in sorted(groups.items()):
        summary.append([suite,mode,domain,origin,f"{sum(x['passed']=='True' for x in items)} / {len(items)}",
                        str(sum(int(x["retrieved_experience"]) for x in items)),
                        f"{sum(float(x['inference_seconds']) for x in items):.2f}"])
    adapter=json.loads(evolution.read_text(encoding="utf-8"))
    h=adapter["metrics"]["heldout"]
    tr="".join("<tr>"+"".join(f"<td>{escape(x)}</td>" for x in row)+"</tr>" for row in summary)
    with (out/"Homer_Capability_Dashboard.html").open("x",encoding="utf-8") as page:
        page.write("""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Homer 1.8 Capability Dashboard</title><style>
body{background:#101c24;color:#e2eef0;font:16px system-ui;margin:4vw}
h1,h2{color:#8ae0cd} table{border-collapse:collapse;width:100%;background:#172833}
th,td{text-align:left;padding:.5em;border-bottom:1px solid #314955} th{color:#8ae0cd}
p{max-width:75ch;line-height:1.6} .scroll{overflow:auto}</style>
<h1>HOMER-01 Capability Dashboard</h1><p>Educational episodes · Digital Genesis 1.8</p>
<p>Each row separates the source of the answer. Creative scores measure formal constraints only. The scheduler initiated all listed tasks without mid-episode human input.</p>
<div class=scroll><table><thead><tr><th>Run<th>Mode<th>Domain<th>Answer origin<th>Passed<th>Memory records<th>Model seconds</tr></thead><tbody>"""+tr+"""</tbody></table></div>
<h2>Held-out transfer of the method selector</h2>""")
        page.write(f"<p>Candidate {h['candidate']['passed']}/{h['candidate']['trials']}, "
                   f"reference {h['worked_baseline']['passed']}/{h['worked_baseline']['trials']}, "
                   f"shortcut {h['shortcut_baseline']['passed']}/{h['shortcut_baseline']['trials']}. "
                   f"Candidate cost {h['candidate']['method_cost']}, reference cost {h['worked_baseline']['method_cost']}. "
                   f"Promoted: {'yes' if adapter['promoted'] else 'no'}.</p>")
    with (out/"observatory.jsonl").open("x",encoding="utf-8") as stream:
        for name in ("expanded_verified_tool.jsonl","expanded_verified_memory.jsonl",
                     "qwen_curriculum_qwen_curriculum.jsonl"):
            path=traces/name
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                row=json.loads(line)
                if row.get("type")=="end":
                    continue
                frame=dict(mode=row["chapter"],origin=row["origin"],tick=row["turn"],
                           caption=row["skill"],active=["executive","memory",*(["language"] if row["qwen_called"] else [])],
                           retrieved_count=row["retrieved_experience"],error=not row["passed"],
                           research=dict(kind="learning",goal=row["observation"]["question"],
                                         observation=row["domain"],outcome=row["score_type"],
                                         refs=", ".join(x[:8] for x in row["memory_ids"]) or "None",
                                         consequence=("consult_qwen" if row["origin"]=="qwen_language_model" else
                                                      "tool_method" if row["origin"]=="deterministic_tool" else
                                                      row["reflection"]["choice"])))
                stream.write(json.dumps(frame)+"\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("out",type=Path)
    p.add_argument("evolution",type=Path)
    p.add_argument("runs",nargs="+",type=Path)
    args=p.parse_args()
    build(args.out,args.runs,args.evolution)
