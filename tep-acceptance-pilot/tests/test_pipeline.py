"""Fast checks that run without data or an LLM."""
import numpy as np
from tep_pilot.checkers import SplitConformal, grounded, accept
from tep_pilot.doer import Labels, build_prompt, parse_json


def test_conformal_coverage_on_exchangeable_data():
    rng = np.random.default_rng(0)
    k, n = 4, 4000
    y = rng.integers(k, size=n)
    P = rng.dirichlet(np.ones(k), size=n)
    P[np.arange(n), y] += 1.0
    P /= P.sum(1, keepdims=True)
    classes = np.arange(k)
    conf = SplitConformal().fit(P[:2000], y[:2000], {c: c for c in classes}, alpha=0.1)
    sets = conf.sets(P[2000:], classes)
    cov = np.mean([t in s for t, s in zip(y[2000:], sets)])
    assert 0.87 <= cov <= 0.93


def test_grounding():
    assert grounded([3, 5], [3, 5, 7])
    assert not grounded([3, 9], [3, 5, 7])     # cites a variable that did not deviate
    assert not grounded([None], [3, 5])        # cites a variable that does not exist
    assert not grounded([], [3])


def test_accept_rule_requires_all_checks():
    row = {"llm_fault": 4, "grounded": True, "sig_proba": {4: 0.8}, "conf_set": {4}}
    assert accept(row, 0.5, 1)
    assert not accept({**row, "grounded": False}, 0.5, 1)
    assert not accept({**row, "conf_set": {4, 5}}, 0.5, 1)
    assert not accept({**row, "sig_proba": {4: 0.3}}, 0.5, 1)
    assert not accept({**row, "llm_fault": None}, 0.5, 1)


def test_masked_prompt_hides_tep_identifiers():
    labels = Labels([0, 1, 6], masked=True, seed=0)
    rep = {"t2_ratio": 2.0, "spe_ratio": 1.5, "top_vars": [0, 6], "top_dev": [-3.1, 2.2]}
    prompt = build_prompt(rep, labels)
    assert "Tennessee" not in prompt and "IDV(" not in prompt and "XMEAS(" not in prompt


def test_parse_json_tolerates_wrapping_text():
    assert parse_json('Sure! {"diagnosis": "A", "confidence": 0.7} done')["diagnosis"] == "A"
    assert parse_json("no json here") == {}
