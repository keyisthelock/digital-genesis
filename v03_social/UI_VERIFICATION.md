# Digital Genesis - Research Laboratory UI verification

The updated Pygame interface was launched on this Windows machine. The Earth remains the original tile world; the coast highlights, terrain textures, waves, lighting, membranes, nucleus, motion interpolation and event effects are rendered separately. No terrain, energy, fitness, mutation, learning, reproduction or death rules changed. The preview uses its own new output directory.

## Changed files

- `main.py`: loads the dashboard only in visual mode; the classic renderer remains available as a callable fallback.
- `run_v03.py`: graphics preset, animation, start-paused and visible benchmark options.
- `ui_lab/`: dashboard layout and controls, cached terrain, organism visuals, bounded telemetry, and the state/mind/social inspector. The graph draws one active module from real connectivity. Sharing effects come from measured transfers; loss color uses the exposed numerical signal.
- `README.md`: launch and controls reference. The workspace is not a Git repository, so the renderer is isolated in its own package rather than a branch.

## Controls

| Control | Action |
|---|---|
| Space or Pause / Play | Pause or resume biological time |
| `+` / `-` | Change target simulation speed |
| Wheel / right or middle drag / Home | Zoom / pan / fit Earth |
| Click organism / `F` | Inspect / follow selected organism |
| `[` / `I` or `]` / `C` | Hide population / inspector / chart panels |
| Drag side-panel border | Resize panel |
| State, Mind, Social tabs; wheel on side panels | Inspect and scroll fields |
| Click chart / Esc | Expand chart / close overlay |
| `T` / `L` / `O` | Terrain layers / labels / neural and social overlays |
| `Q` / `A` | Graphics quality / animation toggle |
| `H` or `?` / Esc | Shortcut reference / exit when no overlay is open |

## Verification

- Compared the pre-change source snapshot with the updated dashboard path for rule and social-neural populations at seeds 0 and 2, up to 360 ticks each. All 27 checkpoint hashes matched, including organism positions, health, energy, genetic and learned weights, RNG states, memories, relationships, terrain and food. The paired cases included 11 births, 40 deaths and 257 sharing events per side across the four runs.
- The 180-tick headless CLI comparison at seed 7 with eight modules produced identical metrics and seven byte-identical scientific logs: generations, ancestry, births, cognition, social events, learning and gateway events.
- Nine engine/experiment source hashes and ten recorded archive/source hashes matched. Older experiments and conserved Organism 36 were preserved.
- Exercised pause, speed, zoom, pan, Home, selection, follow, panel toggles, chart expansion, labels, layers, overlays and quality through the actual event handlers. Verified telemetry against engine data during the comparisons. Tested the rule versus neural action-label distinction separately.
- In the native window, observed moving organisms, then used Pause, zoom, organism selection and the speed button. Biological time stayed at tick 97 across the paused views, including zoom to 1.56x and the change from target 2 to 4 ticks/s. The inspector showed actual sharing history for the selected specimen.

## Visible performance

Seven seconds per preset, default 12 founders and 67-module social treatment at a target 20 ticks/s. FPS excludes the first second. CPU is process time as a percentage of one core, including simulation and rendering. Memory is peak process working set.

| Preset | Window | Mean FPS | 95th percentile frame | CPU / one core | Peak memory | Biological ticks |
|---|---:|---:|---:|---:|---:|---:|
| Low | 1480 × 900 | 29.85 | 34 ms | 43.5% | 76.45 MiB | 139 |
| Medium | 1920 × 1057 | 28.78 | 34 ms | 53.8% | 87.05 MiB | 138 |
| High | 1920 × 1057 | 57.40 | 20 ms | 65.1% | 92.38 MiB | 138 |

These are short, visible-window observations at different window sizes, not a controlled preset cost comparison or a guarantee at larger populations. Low and Medium target 30 FPS; High targets 60. Measurements are saved in each `results/ui_bench_*/ui_benchmark.json`.

## Limits

The dashboard samples at five-tick intervals and at population changes; the sample tick is displayed. It holds up to 240 chart samples and is not a replacement for scientific logs. Ancestry and event lists cover bounded observations in the current view. The inspector reports unavailable fields rather than inferring them. Animation and decorative terrain colors carry no experimental meaning. No scientific parameter can be changed from the dashboard.
