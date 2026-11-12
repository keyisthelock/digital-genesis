# Run Homer 1.8

From the repository root, use Python 3.12 or later and a new output folder for each run. The educational runner works with a clean checkout. If the optional original Omega archive is present at the historical path, the runner checks its hash. The published evidence contains the hashes recorded during the original experiments.

```powershell
$python = "python"
& $python -B -m unittest homer.becoming.test_becoming -q
& $python -B -m homer.becoming.runner --suite vertical --out homer/becoming/output/vertical_recheck
& $python -B -m homer.becoming.runner --suite expanded --out homer/becoming/output/expanded_recheck
& $python -B -m homer.becoming.evolve homer/becoming/output/evolution_recheck
```

For optional Qwen runs, start your local llama.cpp server with the verified Qwen3.5-2B GGUF (SHA-256 e8bf47d40c5ba68baf8f3e503ee36710da6e8641cb0a670a508cff5b3f0cfbf7). Use alias qwen3.5:2b, bind to 127.0.0.1:11440, and use offline mode. The runtime and weights are separate local dependencies.

```powershell
& $python -B -m homer.becoming.runner --suite qwen --out homer/becoming/output/qwen_recheck
& $python -B -m homer.becoming.runner --suite qwen_curriculum --out homer/becoming/output/curriculum_recheck
```

Create STOP in the run folder to stop at the next attempt boundary. Each model request has a 30-second socket timeout. The two suites allow eight and seven requests, respectively. All educational responses are data. Profile revisions are opt-in. Use the preferences module with an existing experiment journal and a new output folder to generate a candidate profile, then pass its profile.json to the runner with --personality.

The measured combined CSV, decision traces, dashboard and replay feed are under homer/becoming/evidence. Open Homer_Capability_Dashboard.html locally or use Godot.

```powershell
$feed = (Resolve-Path homer/becoming/evidence/observatory.jsonl).Path
godot --path homer/becoming/observatory -- $feed
```

Use keys 1–5 for the chapters and Left/Right for actual attempts. To aggregate another set of runs, pass a fresh output folder, the evolution JSON and the completed run folders to python -B -m homer.becoming.dashboard.
