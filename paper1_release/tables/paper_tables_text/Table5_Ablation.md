# Ablation study of the proposed dynamic RGB-D SLAM system.

| Variant | ATE | RPE | FPS | Failure Rate |
| --- | --- | --- | --- | --- |
| Baseline | 0.4314 | 0.0260 | -- | 0.0429 |
| A: Baseline+Semantic Mask | 0.4429 | 0.0667 | 13.34 | 0.3425 |
| B: Baseline+Temporal Consistency | 0.6561 | 0.1279 | 14.37 | 0.3192 |
| C: Baseline+Object-level Semantic Map | 0.4429 | 0.0667 | 12.54 | 0.3425 |
| D: Full Model | 0.4392 | 0.0552 | 14.98 | 0.3517 |
