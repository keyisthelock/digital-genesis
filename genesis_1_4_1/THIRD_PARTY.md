# Third-party components

No GitHub code or package was imported. The simulation uses Python's standard library and the existing Digital Genesis code. Report generation uses the already-installed workspace ReportLab runtime.

| Repository reviewed | Role considered | Decision |
|---|---|---|
| [Farama Foundation Gymnasium](https://github.com/Farama-Foundation/Gymnasium) | Standardized environment API | The existing deterministic runner already provides matched scenes and state replay. |
| [Bullet Physics](https://github.com/bulletphysics/bullet3) | Articulated-body physics | The memory experiment uses the existing grid and motor controls. |
| [MuJoCo](https://github.com/google-deepmind/mujoco) | Articulated-body physics | A different physics model would change the comparison. |

No version or commit is pinned because none of these components is a dependency. No remote scripts or installations were executed.
