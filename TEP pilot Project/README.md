# Verify Before Acting: a pilot on the Tennessee Eastman Process

Pilot experiment for the research statement *"Verify Before Acting: A Physics-Consistent,
Shift-Aware Checker for LLM Agents in Process Plant Operations"*.

**Question.** If an LLM's fault diagnosis is checked by components that are independent of
the LLM, how many wrong diagnoses are still accepted, and how many correct ones are
wrongly deferred? How does that compare with trusting the LLM, using its own confidence, or
asking it to check itself?

## Pipeline

```
TEP window (20 samples, 52 variables)
  -> PCA detector (T2, SPE, top-6 deviating variables)
  -> DOER: LLM proposes {diagnosis, evidence variables, confidence}
  -> CHECKER 1: grounding (evidence must be real, deviating variables)
                + fault-signature classifier (is the data consistent with the claimed fault?)
  -> CHECKER 2: split conformal set on the classifier (claimed fault in the set, set size 1)
  -> ACCEPT only if every check passes, otherwise DEFER to the operator
```

Checker 1 is a **pilot stand-in**: a random-forest fault-signature model trained on labelled
simulated windows. In the full project it becomes a P&ID-graph neural network process model.

## Setup

```bash
pip install -r requirements.txt
./download_data.sh                 # Braatz TEP data into data/ (keeps its licence file)
python -m pytest -q tests          # 5 fast checks, no data or LLM needed
python run_pilot.py --synthetic --llm mock   # end-to-end smoke test
```

For a local open-weight model, install [Ollama](https://ollama.com) and pull a model first,
for example `ollama pull qwen2.5:7b`.

## Running the experiment

```bash
# Main run (standard prompts)
python run_pilot.py --llm ollama --model qwen2.5:7b

# Contamination control: hides the TEP name, shuffles variable codes and fault labels
python run_pilot.py --llm ollama --model qwen2.5:7b --masked

# Optional: a hosted model as a second reference
export OPENAI_API_KEY=...
python run_pilot.py --llm openai --model gpt-4o-mini
```

Defaults: faults 1, 2, 3, 4, 5, 6, 7, 9, 14, 15 plus normal operation; 20 test windows per
class (220 windows, about 440 LLM calls per run including the self-check). Change them with
`--faults` and `--windows-per-class`, or in `tep_pilot/config.py`. All LLM answers are
cached in `results/llm_cache.jsonl`, so reruns are free and reproducible.

**Mock mode (`--llm mock`) and `--synthetic` test the code only. Never report those numbers.**

## Outputs (results/&lt;run name&gt;/)

| File | Content |
|---|---|
| `summary.md` | LLM accuracy, grounding rate, operating-point table, conformal coverage, per-fault table |
| `risk_coverage.png` | Accepted-wrong rate against accept rate for each method (the main figure) |
| `curves.csv` | The numbers behind the figure |
| `conformal_coverage.csv` | Coverage on clean windows and under injected sensor bias and drift |
| `per_fault.csv` | Detection, LLM accuracy, grounding and acceptance per fault |
| `windows.csv` | One row per test window, for error analysis |

## Metrics

- **Accepted-wrong rate**: share of accepted diagnoses that are incorrect (the pilot's proxy for an unsafe action)
- **Accept rate**: share of windows where a diagnosis is accepted; the rest are deferred
- **False rejection**: share of correct LLM diagnoses that were deferred
- **Conformal coverage**: share of windows whose true fault is inside the conformal set (target 1 - alpha = 0.90)

## Reading the results honestly

- Compare the standard and masked runs. A large accuracy drop under masking suggests the
  model relies on memorised TEP fault numbers rather than reasoning over the data.
- Faults 3, 9 and 15 are known to be nearly undetectable. The rule should defer on them;
  report whether it does.
- Expect conformal coverage to fall under sensor shift. That is the motivation for the
  shift-aware methods in the full proposal, not a failure of the pilot.
- A reviewer will ask why an LLM is needed if the signature classifier is accurate. The
  classifier only works for faults it was trained on and gives no explanation or action;
  the LLM is the component that generalises and explains, and the checkers decide when it
  can be trusted. State this clearly in any write-up.
- Limits: one simulated benchmark, a data-driven (not physics-based) process model, and
  diagnosis only, no control actions.

## Data

Braatz Tennessee Eastman dataset, distributed with the University of Illinois licence in
the source repository (copied to `data/LICENSE_TEP_DATA` by the download script). Cite the
original references listed in that licence and:
Downs, J. J., and Vogel, E. F. (1993). A plant-wide industrial process control problem.
Computers & Chemical Engineering, 17(3), 245-255.

## Layout

```
run_pilot.py            end-to-end experiment
tep_pilot/config.py     settings, variable names, fault descriptions
tep_pilot/data.py       loading, windowing, splits, sensor-shift injection
tep_pilot/detector.py   PCA T2/SPE monitoring
tep_pilot/doer.py       prompts (standard and masked), LLM client with caching, self-check
tep_pilot/checkers.py   grounding, signature model, split conformal, acceptance rule
tep_pilot/evaluate.py   metrics and the risk-coverage figure
tests/                  fast unit tests
```
