# TEP acceptance-rule pilot: openai_gpt-4o-mini_standard



- Faults: [1, 2, 3, 4, 5, 6, 7, 9, 14, 15] plus normal operation; 220 test windows of 20 samples
- LLM: openai / gpt-4o-mini; prompt mode: standard
- LLM diagnosis accuracy: 0.027; evidence fully grounded: 0.959
- Signature classifier accuracy: 0.709
- Conformal target coverage: 0.90

## Operating point
| method                          |   accept_rate |   accepted_wrong_rate |   n_accepted |   false_rejection |
|:--------------------------------|--------------:|----------------------:|-------------:|------------------:|
| LLM always accepted             |         1.000 |                 0.973 |          220 |             0.000 |
| LLM self-check                  |         0.636 |                 0.964 |          140 |             0.167 |
| LLM + acceptance rule (tau=0.5) |         0.023 |                 0.000 |            5 |             0.167 |

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
|   1.000 | 20.000 |        1.000 |          0.150 |           1.000 |         0.100 |
|   2.000 | 20.000 |        1.000 |          0.050 |           1.000 |         0.050 |
|   3.000 | 20.000 |        0.250 |          0.000 |           1.000 |         0.000 |
|   4.000 | 20.000 |        1.000 |          0.000 |           0.600 |         0.000 |
|   5.000 | 20.000 |        0.400 |          0.000 |           1.000 |         0.000 |
|   6.000 | 20.000 |        1.000 |          0.050 |           1.000 |         0.050 |
|   7.000 | 20.000 |        1.000 |          0.000 |           0.950 |         0.000 |
|   9.000 | 20.000 |        0.100 |          0.000 |           1.000 |         0.000 |
|  14.000 | 20.000 |        1.000 |          0.050 |           1.000 |         0.050 |
|  15.000 | 20.000 |        0.100 |          0.000 |           1.000 |         0.000 |

Figure: risk_coverage.png
