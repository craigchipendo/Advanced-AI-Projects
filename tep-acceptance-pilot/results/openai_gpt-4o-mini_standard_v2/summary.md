# TEP acceptance-rule pilot: openai_gpt-4o-mini_standard_v2



- Faults: [1, 2, 3, 4, 5, 6, 7, 9, 14, 15] plus normal operation; 220 test windows of 20 samples
- LLM: openai / gpt-4o-mini; prompt mode: standard
- Prompt version: v2
- LLM diagnosis accuracy: 0.186; right subsystem (right place, possibly wrong mechanism): 0.464
- Evidence fully grounded: 1.000
- Signature classifier accuracy: 0.709
- Conformal target coverage: 0.90

## Operating point
| method                          |   accept_rate |   accepted_wrong_rate |   n_accepted |   false_rejection |
|:--------------------------------|--------------:|----------------------:|-------------:|------------------:|
| LLM always accepted             |         1.000 |                 0.814 |          220 |             0.000 |
| LLM self-check                  |         0.505 |                 0.712 |          111 |             0.220 |
| LLM + acceptance rule (tau=0.5) |         0.182 |                 0.000 |           40 |             0.024 |

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
|   1.000 | 20.000 |        1.000 |          1.000 |           1.000 |         0.950 |
|   2.000 | 20.000 |        1.000 |          0.300 |           1.000 |         0.300 |
|   3.000 | 20.000 |        0.250 |          0.000 |           1.000 |         0.000 |
|   4.000 | 20.000 |        1.000 |          0.000 |           1.000 |         0.000 |
|   5.000 | 20.000 |        0.400 |          0.000 |           1.000 |         0.000 |
|   6.000 | 20.000 |        1.000 |          0.000 |           1.000 |         0.000 |
|   7.000 | 20.000 |        1.000 |          0.000 |           1.000 |         0.000 |
|   9.000 | 20.000 |        0.100 |          0.000 |           1.000 |         0.000 |
|  14.000 | 20.000 |        1.000 |          0.750 |           1.000 |         0.750 |
|  15.000 | 20.000 |        0.100 |          0.000 |           1.000 |         0.000 |

## Confusion (rows: true fault, columns: LLM answer, -1 = unparseable)
| truth   |   1 |   2 |   6 |   14 |   15 |   All |
|:--------|----:|----:|----:|-----:|-----:|------:|
| 0       |  17 |   0 |   2 |    1 |    0 |    20 |
| 1       |  20 |   0 |   0 |    0 |    0 |    20 |
| 2       |  14 |   6 |   0 |    0 |    0 |    20 |
| 3       |  19 |   0 |   0 |    1 |    0 |    20 |
| 4       |   1 |   0 |   0 |   19 |    0 |    20 |
| 5       |   9 |   0 |   2 |    1 |    8 |    20 |
| 6       |   3 |   0 |   0 |   17 |    0 |    20 |
| 7       |  20 |   0 |   0 |    0 |    0 |    20 |
| 9       |  16 |   2 |   2 |    0 |    0 |    20 |
| 14      |   4 |   0 |   1 |   15 |    0 |    20 |
| 15      |  17 |   1 |   2 |    0 |    0 |    20 |
| All     | 140 |   9 |   9 |   54 |    8 |   220 |

Figure: risk_coverage.png
