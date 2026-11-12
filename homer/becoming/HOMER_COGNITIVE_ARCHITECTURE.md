# Homer cognitive architecture

The educational runner lives in homer/becoming. Existing motor and dialogue experiments remain independently runnable. The shared educational boundary is Task.packet, the goal manager, the local model request, the independent scorer, and a journal record linked to any recalled feedback.

| Subsystem | Reused component | Function in 1.8 |
| --- | --- | --- |
| Embodied controller | Homer motor and verified Omega archive | Existing simulator integration. Loaded only as needed by prior motor paths. Educational actions have no motor authority. |
| Autobiography | Homer Journal and starter SQLite schema | Stores observed verification results and links to prior attempts. Each condition has its own journal. |
| Knowledge | Local SQLite store and token retrieval | Source IDs, confidence, topic and chapter, content hashes and corrective revisions. No private heritage is retrieved. |
| Language | Existing Qwen weights and localhost llama.cpp transport | Typed bounded answer only. No tool calls or action execution. |
| Personality | Original identity plus versioned public preferences | Stable values and logged scheduler settings. Separate operator-approved preference profile. |
| Goal manager | Deterministic candidate scoring | Selects and reschedules only permitted exercises. |
| Verification | Python exact fractions, comparisons and restricted program interpreter | Scores independent of Qwen. Hidden arrays remain in the evaluator. |
| Research view | Godot Observatory scene pattern | Replays actual educational events and their decision origins. |

The loop is observe, retrieve, score a goal, plan, answer, verify, journal and reconsider. The bounded method policy can switch methods after recalled failure. Knowledge retrieval and procedure selection do not update neural weights. Evolution uses a separate offline process and never changes the active learner.

The current source store uses sparse word overlap and exact topic labels. It cannot reliably resolve paraphrases or establish factual truth. A correction is a new attributed source with a reference to the superseded one. Content provenance and confidence are supplied metadata and retained separately from biography.
