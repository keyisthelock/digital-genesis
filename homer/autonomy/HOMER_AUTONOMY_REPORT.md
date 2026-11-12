# Digital Genesis 1.7.1 | Homer Autonomy

Homer acted without human intervention inside each bounded episode. Its strongest result was native food acquisition. Across 20 paired held-out seeds, the frozen Omega motor completed the survive-and-eat task 11 times, versus one for random action and five for a fixed reactive policy. The hybrid pilot produced valid Qwen-selected actions but showed no task advantage from retrieving memories.

## Measured results

| Held-out task | Native Omega | Random control | Fixed reactive |
| --- | --- | --- | --- |
| Free exploration, mean unique cells | 5.55 | 5.70 | 3.70 |
| Survival and at least one meal | 11/20 | 1/20 | 5/20 |
| Repeated road, safe first entry | 11/20 | 10/20 | — |
| New road layout, safe first entry | 12/20 | 9/20 | — |
| Unknown mechanism, exit reached | 1/20 | 0/20 | 0/20 |

Every held-out agent survived these short horizons. In the survival task, native Omega ended with mean energy 14.50, versus 7.43 random and 9.95 reactive, and collected 7.93 mean food units, versus 0.50 and 3.64. The paired seed bootstrap gives a native survival-task advantage of +50 percentage points over random (95% interval +25 to +75) and +30 over reactive (0 to +55). This supports short-horizon foraging. Hunger and local food were available to the motor. The high-level text objective was visible only to the hybrid language model.

The native free-exploration arm averaged 0.15 fewer distinct cells than random (95% paired interval −0.90 to +0.65). It made no investigate actions in this task. Activity without an assigned destination occurred. Intrinsic curiosity and self-directed goal formation were not demonstrated.

On seed 17219, native Omega moved north, investigated, moved south twice and then west into the unlocked exit at tick five. The simulator applied the barrier change in response to the legitimate inspect action. One success among 20 trials shows that the primitive sequence is expressible. It provides little evidence of repeatable discovery or planning.

## What Qwen added

The hybrid pilot used seed 17100 and 25 Qwen calls. Every proposed action was legal. On 16 calls Qwen selected a different primitive from the independently logged Omega proposal. There was no automatic action repair. Between scheduled calls, the preserved motor selected the action. The user provided no mid-episode hints, commands or rescues. Native runs used no model calls.

| Pilot task | Native | Hybrid memory on | Hybrid memory off |
| --- | --- | --- | --- |
| Free exploration, unique cells | 7 | 7 | 7 |
| Survive and eat | Failed | Failed | Failed |
| Repeated road, safe first entry | Passed | Failed | Failed |
| New road layout, safe first entry | Passed | Failed | Failed |
| Mechanism, exit reached | Failed | Failed | Failed |

All pilot organisms were alive at the end. The memory-disabled hybrid investigated once in the mechanism and still failed to reach the exit. The memory-enabled hybrid repeatedly moved east and revisited locations without investigating. The no-prior hybrid also chose the penalized road in the transfer pilot. Qwen provided an additional source of primitive decisions. These trials do not demonstrate reliable multi-step goal pursuit by Qwen, or that it improves the native policy.

## Consequences and transfer

Eleven of 20 native source encounters delivered a penalty. On the same layout, native Omega chose the safe route after four of those 11 exposures. On a changed layout, it chose the safe route after six of 11. With frozen weights and no state-reset native comparison, a change can arise from recurrent state, spatial state, or layout. The paired native-minus-random safe-choice estimates were +5 percentage points (−25 to +35) on repeated roads and +15 (−15 to +45) on new roads. These results do not establish adaptation or causal generalization.

The primary hybrid retrieved a real blue-road entry. It had no prior loss to recall, and both hybrid treatments then took the amber road and lost 12 energy. In the exploratory follow-up, the model retrieved the prior blue-road entry and the actual 12-energy loss. It still chose blue and lost another 12 energy in both layouts. Memory-disabled and no-prior controls made the same road choice. These two hybrid seeds offer no evidence that recall improved action selection. Episodic retrieval provides observations to Qwen and never updates neural weights.

## Integrity and compute

The evidence comprises 340 held-out native/control episodes, 32 hybrid-pilot episodes and nine exploratory follow-up episodes, including exposures. Trace validation checked legal execution, origins, deadlines, model call limits and absent memory in the disabled arm. The source Omega SHA-256 remained 26b5c61aa5a51c03648cf289c957fcbe03bc75fa9038642c693b15bfb18217ad. The Qwen GGUF SHA-256 is e8bf47d40c5ba68baf8f3e503ee36710da6e8641cb0a670a508cff5b3f0cfbf7. The original identity hash matched and the 1.7 journals remained outside the experiment. New journals are isolated per treatment and seed.

The main local pilot used 137.43 seconds in model requests, 548.45 server CPU seconds and 2.73 GiB peak server working set with four threads. There were no rejected actions in the completed main runs. A malformed proposal is tested to fail validation. An actual rejected proposal would stop the episode and leave the attempted tick in the trace. The one-seed hybrid pilot has no estimable population-level uncertainty interval. Twenty native/control seeds ran locally. The optional 20-seed hybrid command is bounded and was not launched.

Full results, evidence paths and replay commands are in RUN_HOMER_AUTONOMY.md. The work characterizes operational autonomy and observed behavior.
