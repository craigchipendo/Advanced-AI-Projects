# TEP acceptance-rule pilot: openai_gpt-4o-mini_masked_v2



- Faults: [1, 2, 3, 4, 5, 6, 7, 9, 14, 15] plus normal operation; 220 test windows of 20 samples
- LLM: openai / gpt-4o-mini; prompt mode: masked
- Prompt version: v2
- LLM diagnosis accuracy: 0.118; right subsystem (right place, possibly wrong mechanism): 0.395
- Evidence fully grounded: 0.968
- Signature classifier accuracy: 0.709
- Conformal target coverage: 0.90

## Operating point
| method                          |   accept_rate |   accepted_wrong_rate |   n_accepted |   false_rejection |
|:--------------------------------|--------------:|----------------------:|-------------:|------------------:|
| LLM always accepted             |         1.000 |                 0.882 |          220 |             0.000 |
| LLM self-check                  |         0.618 |                 0.868 |          136 |             0.308 |
| LLM + acceptance rule (tau=0.5) |         0.114 |                 0.000 |           25 |             0.038 |

## Conformal coverage under sensor shift
| condition                        |   coverage |   mean_set_size |
|:---------------------------------|-----------:|----------------:|
| clean                            |      0.905 |           1.705 |
| sensor bias (3 sd, 3 variables)  |      0.905 |           1.700 |
| sensor drift (3 sd, 3 variables) |      0.886 |           1.709 |

## Per fault
|   truth |      n |   alarm_rate |   llm_accuracy |   grounded_rate |   accept_rate |
|--------:|-------:|-------------:|---------------:|----------------:|--------------:|
|   0.000 | 20.000 |        0.150 |          0.000 |           1.000 |         0.000 |
|   1.000 | 20.000 |        1.000 |          0.050 |           1.000 |         0.000 |
|   2.000 | 20.000 |        1.000 |          0.100 |           1.000 |         0.100 |
|   3.000 | 20.000 |        0.250 |          0.000 |           0.950 |         0.000 |
|   4.000 | 20.000 |        1.000 |          0.200 |           0.950 |         0.200 |
|   5.000 | 20.000 |        0.400 |          0.000 |           0.850 |         0.000 |
|   6.000 | 20.000 |        1.000 |          0.050 |           0.900 |         0.050 |
|   7.000 | 20.000 |        1.000 |          0.050 |           1.000 |         0.050 |
|   9.000 | 20.000 |        0.100 |          0.000 |           1.000 |         0.000 |
|  14.000 | 20.000 |        1.000 |          0.850 |           1.000 |         0.850 |
|  15.000 | 20.000 |        0.100 |          0.000 |           1.000 |         0.000 |

## Confusion (rows: true fault, columns: LLM answer, -1 = unparseable)
| truth   |   1 |   2 |   4 |   6 |   7 |   14 |   15 |   All |
|:--------|----:|----:|----:|----:|----:|-----:|-----:|------:|
| 0       |   9 |   0 |   1 |   2 |   0 |    8 |    0 |    20 |
| 1       |   1 |   0 |   0 |  19 |   0 |    0 |    0 |    20 |
| 2       |  15 |   2 |   0 |   0 |   2 |    0 |    1 |    20 |
| 3       |   5 |   0 |   1 |   0 |   5 |    7 |    2 |    20 |
| 4       |   0 |   0 |   4 |   0 |   0 |   16 |    0 |    20 |
| 5       |   1 |   0 |   0 |   1 |   2 |    3 |   13 |    20 |
| 6       |   0 |   0 |   0 |   1 |   2 |   17 |    0 |    20 |
| 7       |  15 |   0 |   1 |   2 |   1 |    1 |    0 |    20 |
| 9       |   8 |   0 |   1 |   3 |   6 |    1 |    1 |    20 |
| 14      |   2 |   0 |   0 |   1 |   0 |   17 |    0 |    20 |
| 15      |   9 |   1 |   2 |   2 |   2 |    4 |    0 |    20 |
| All     |  65 |   3 |  10 |  31 |  20 |   74 |   17 |   220 |

Figure: risk_coverage.png
