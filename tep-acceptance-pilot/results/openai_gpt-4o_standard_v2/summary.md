# TEP acceptance-rule pilot: openai_gpt-4o_standard_v2



- Faults: [1, 2, 3, 4, 5, 6, 7, 9, 14, 15] plus normal operation; 55 test windows of 20 samples
- LLM: openai / gpt-4o; prompt mode: standard
- Prompt version: v2
- LLM diagnosis accuracy: 0.182; right subsystem (right place, possibly wrong mechanism): 0.491
- Evidence fully grounded: 1.000
- Signature classifier accuracy: 0.709
- Conformal target coverage: 0.90

## Operating point
| method                          |   accept_rate |   accepted_wrong_rate |   n_accepted |   false_rejection |
|:--------------------------------|--------------:|----------------------:|-------------:|------------------:|
| LLM always accepted             |         1.000 |                 0.818 |           55 |             0.000 |
| LLM self-check                  |         0.745 |                 0.756 |           41 |             0.000 |
| LLM + acceptance rule (tau=0.5) |         0.182 |                 0.000 |           10 |             0.000 |

## Conformal coverage under sensor shift
| condition                        |   coverage |   mean_set_size |
|:---------------------------------|-----------:|----------------:|
| clean                            |      0.909 |           1.855 |
| sensor bias (3 sd, 3 variables)  |      0.873 |           1.673 |
| sensor drift (3 sd, 3 variables) |      0.873 |           1.745 |

## Per fault
|   truth |     n |   alarm_rate |   llm_accuracy |   grounded_rate |   accept_rate |
|--------:|------:|-------------:|---------------:|----------------:|--------------:|
|   0.000 | 5.000 |        0.200 |          0.000 |           1.000 |         0.000 |
|   1.000 | 5.000 |        1.000 |          1.000 |           1.000 |         1.000 |
|   2.000 | 5.000 |        1.000 |          0.000 |           1.000 |         0.000 |
|   3.000 | 5.000 |        0.000 |          0.000 |           1.000 |         0.000 |
|   4.000 | 5.000 |        1.000 |          0.000 |           1.000 |         0.000 |
|   5.000 | 5.000 |        0.400 |          0.000 |           1.000 |         0.000 |
|   6.000 | 5.000 |        1.000 |          0.000 |           1.000 |         0.000 |
|   7.000 | 5.000 |        1.000 |          0.000 |           1.000 |         0.000 |
|   9.000 | 5.000 |        0.000 |          0.000 |           1.000 |         0.000 |
|  14.000 | 5.000 |        1.000 |          1.000 |           1.000 |         1.000 |
|  15.000 | 5.000 |        0.200 |          0.000 |           1.000 |         0.000 |

## Confusion (rows: true fault, columns: LLM answer, -1 = unparseable)
| truth   |   1 |   6 |   7 |   14 |   15 |   All |
|:--------|----:|----:|----:|-----:|-----:|------:|
| 0       |   2 |   1 |   1 |    1 |    0 |     5 |
| 1       |   5 |   0 |   0 |    0 |    0 |     5 |
| 2       |   4 |   0 |   0 |    0 |    1 |     5 |
| 3       |   1 |   0 |   0 |    4 |    0 |     5 |
| 4       |   0 |   0 |   0 |    5 |    0 |     5 |
| 5       |   0 |   0 |   1 |    0 |    4 |     5 |
| 6       |   0 |   0 |   0 |    5 |    0 |     5 |
| 7       |   4 |   0 |   0 |    1 |    0 |     5 |
| 9       |   0 |   0 |   1 |    4 |    0 |     5 |
| 14      |   0 |   0 |   0 |    5 |    0 |     5 |
| 15      |   4 |   0 |   0 |    1 |    0 |     5 |
| All     |  20 |   1 |   3 |   26 |    5 |    55 |

Figure: risk_coverage.png
