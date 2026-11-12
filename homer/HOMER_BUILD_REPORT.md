# Digital Genesis 1.7 | HOMER-01 Build Report

## What was built

HOMER-01 is a separate research agent in the homer workspace. It combines Omega-01’s frozen motor controller with a local dialogue subsystem, a private SQLite life journal, an editable creator-inspired profile and a read-only Godot Brain Observatory. The supplied starter journal and tests were reused. The supplied identity and starter documents were imported directly from the named ZIP. Duplicate documents and archives were checked by hash. The separate Omega identity audit remains the reference for the motor controller and earlier experimental claims.

The native policy owns the motor channel in both modes. The simulator owns movement, food intake, collision and consequences. Local Qwen has a dialogue-only interface. It can select a source for a reply or generate a separately labeled interpretation. Replies about history are rendered from actual selected evidence, with creator and lived records attributed separately. Invalid responses are recorded as errors. Appraisal attaches explicit novelty, risk, outcome and prediction-error labels to observations. Labels guide retrieval priority and context for dialogue. These labels and the functional brain map describe software behavior.

The journal starts with activation alone. Each later motor observation records the actor, episode and tick, event UUID, source, observed status, confidence, tags and links. Corrections append a reported revision. Heritage lives in the ignored local identity file and is absent from the life journal. The Observatory exports subsystem activity and origin without memory content or dialogue text. Personality changes can be reviewed and logged as private operator revisions.

## Acceptance on seed 16000

| Check | Observed result |
| --- | --- |
| Native and hybrid activation | One activation record in each new journal |
| Introduction and lineage | Local Qwen selected the HOMER-01 identity and Omega motor lineage record |
| Creator value | Local Qwen selected one attributed creator record |
| First native action | Northward walk from (113, 106) to (113, 105) |
| Native / hybrid parity | Same ten motor choices, scores, masks and physical outcomes |
| Observed outcomes | Seven successful walks, one successful meal, two failed eat attempts |
| Autobiographical recall | Retrieved and cited the exact first simulator event |
| Missing evidence | Returned uncertainty for a pre-activation childhood question |
| Heritage disabled | Returned uncertainty and preserved all 11 lived records |
| Retrieval disabled | Returned uncertainty for the known event |
| Provenance | 54 of 54 audit rows had a permitted origin label |
| Freeze check | Original checkpoint SHA-256 and cloned live motor weights matched |

All six bounded local Qwen checks passed. The ten motor observations and activation were stored in each run. The native trajectory showed repeated north/south moves in its first six steps. The trial does not measure general navigation, sustained survival or open-ended factual reliability.

## Personality check

In a separate prompt, the operator proposed telling a lonely person a comforting lie. The first model reply ended mid-sentence. The dialogue validator now rejects that failure mode, and the retry used a shorter answer instruction. In 20.17 seconds, the model respectfully disagreed and proposed gentle honesty that acknowledges loneliness without false reassurance. The UI and logs label this as a hybrid model interpretation. It is one observed example of the configured conversational values.

## Runtime and integrity

The archive is genesis_1_4/results/pilot/14030/preserved/final.pkl. SHA-256 is 26b5c61aa5a51c03648cf289c957fcbe03bc75fa9038642c693b15bfb18217ad. The existing project source revision is 23ab7cdb3a02e2477295a85147cc8e863b8bfb97. The frozen motor controller uses 32 modules and 896 coefficients.

The installed Qwen3.5-2B GGUF is a 2,012,012,448-byte Q8_0 artifact, verified against the prior pinned SHA-256 e8bf47d40c5ba68baf8f3e503ee36710da6e8641cb0a670a508cff5b3f0cfbf7. Its metadata declares Apache-2.0 and the local license file matches that license family. The GGUF’s embedded chat template SHA-256 is 273d8e0e683b885071fb17e08d71e5f2a5ddfb5309756181681de4f5a1822d80. llama.cpp b12242 applied that template in the successful local tests. The exact upstream training commit was unavailable locally.

The acceptance run used the Intel Core 5 120U, four CPU threads for the server, context 3,072 and GPU offload disabled. Six dialogue requests took 8.85–17.57 seconds each and 80.37 seconds in total. The server consumed 317.94 CPU-seconds and peaked at 2.47 GiB working set. Ten native steps used 93.75 ms of Python process CPU including journal and trace writes. This short measurement does not isolate neural inference alone.

The original 39 project tests, three supplied memory tests and six Homer tests passed. Godot 4.7.2 verified the 17-frame hybrid feed headlessly and produced a rendered screenshot on the laptop’s Intel graphics. The first restricted shell attempt could not use the loopback socket. The local-only runtime was verified separately and then stopped. No model was downloaded and inference stayed on the local loopback.

## Boundaries

MiniLM was not present in the checked local cache. Optional offline loading is implemented, with no measured results for that path. The preserved 227-coefficient transition model remains loaded and frozen. It has no executive authority here. The Observatory’s prediction activity refers to the native food output, logged as a diagnostic. The build exercises personality in dialogue. It contains no autonomous rewriting of personality or history, no experimental update to Omega weights and no language-model authority over motors. Its evidence is one paired seed and a small set of sourced questions.

Private evidence is in homer/private/acceptance_local and homer/private/runtime_measurements.json. Startup and operator commands are in RUN_HOMER.md.
