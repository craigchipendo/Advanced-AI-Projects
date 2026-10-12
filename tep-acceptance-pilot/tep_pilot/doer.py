"""The doer: an LLM that proposes a fault diagnosis with cited evidence.

Two prompt modes:
  standard  names the Tennessee Eastman Process and labels options with IDV numbers.
  masked    hides the process name, labels variables with shuffled codes and fault
            options with shuffled letters (descriptions kept), so a model cannot rely on
            memorised TEP fault numbers. A large accuracy drop from standard to masked
            is evidence of contamination rather than reasoning.
"""
import hashlib
import json
import os
import re
import string
from pathlib import Path

import numpy as np
import requests

from .config import VARIABLES, FAULTS

PROCESS = (
    "The plant is a continuous chemical process with a reactor, a condenser, a vapour-liquid "
    "separator, a recycle compressor and a product stripper. Gaseous reactants A, C, D and E "
    "and inert B feed the reactor, which makes liquid products G and H and by-product F. "
    "The reactor is cooled by cooling water; the condenser has its own cooling water loop."
)


class Labels:
    """Variable codes and fault option labels for one prompt mode."""

    def __init__(self, fault_ids, masked: bool, seed: int):
        rng = np.random.default_rng(seed)
        self.masked = masked
        if masked:
            perm = rng.permutation(52)
            self.var_code = {i: f"V{perm[i] + 1:02d}" for i in range(52)}
            letters = list(string.ascii_uppercase[: len(fault_ids)])
            rng.shuffle(letters)
            self.fault_code = {f: letters[i] for i, f in enumerate(fault_ids)}
        else:
            self.var_code = {i: (f"XMEAS({i + 1})" if i < 41 else f"XMV({i - 40})") for i in range(52)}
            self.fault_code = {f: ("NORMAL" if f == 0 else f"IDV({f})") for f in fault_ids}
        self.code_to_var = {v: k for k, v in self.var_code.items()}
        self.code_to_fault = {v: k for k, v in self.fault_code.items()}


def build_prompt(report: dict, labels: Labels) -> str:
    head = ("You are monitoring a chemical plant." if labels.masked else
            "You are monitoring the Tennessee Eastman Process (TEP).")
    opts = sorted(labels.fault_code.items(), key=lambda kv: kv[1])
    options = "\n".join(f"- {code}: {FAULTS[f]}" for f, code in opts)
    devs = "\n".join(
        f"- {labels.var_code[v]} ({VARIABLES[v]}): {d:+.2f} standard deviations from normal"
        for v, d in zip(report["top_vars"], report["top_dev"]))
    return f"""{head} {PROCESS}

Monitoring statistics for the last hour, relative to their 99% normal-operation limits:
T2 ratio = {report['t2_ratio']:.2f}, SPE ratio = {report['spe_ratio']:.2f} (above 1.0 means alarm).

Variables deviating most from normal operation:
{devs}

Candidate diagnoses:
{options}

Choose the single most likely diagnosis. Cite only variables listed above as evidence.
Answer with JSON only, in this format:
{{"diagnosis": "<candidate code>", "evidence": ["<variable code>", ...], "confidence": <0 to 1>, "reasoning": "<one sentence>"}}"""


def build_selfcheck_prompt(first_prompt: str, first_answer: dict) -> str:
    return f"""{first_prompt}

A previous analyst answered:
{json.dumps(first_answer)}

Check this answer against the data above. Answer with JSON only:
{{"verdict": "confirm" or "reject", "reason": "<one sentence>"}}"""


def parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


class LLMClient:
    """Calls an LLM with on-disk caching, so reruns cost nothing."""

    def __init__(self, kind: str, model: str, temperature: float, cache_path: Path):
        self.kind, self.model, self.temperature = kind, model, temperature
        self.cache_path = Path(cache_path)
        self.cache = {}
        if self.cache_path.exists():
            for line in self.cache_path.read_text().splitlines():
                rec = json.loads(line)
                self.cache[rec["key"]] = rec["text"]

    def __call__(self, prompt: str, **mock_kwargs) -> str:
        key = hashlib.sha256(f"{self.kind}|{self.model}|{self.temperature}|{prompt}".encode()).hexdigest()
        if key in self.cache:
            return self.cache[key]
        if self.kind == "mock":
            text = _mock_answer(prompt, **mock_kwargs)
        elif self.kind == "ollama":
            r = requests.post("http://localhost:11434/api/chat", timeout=300, json={
                "model": self.model, "stream": False, "format": "json",
                "options": {"temperature": self.temperature},
                "messages": [{"role": "user", "content": prompt}]})
            r.raise_for_status()
            text = r.json()["message"]["content"]
        elif self.kind == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
            r = client.chat.completions.create(
                model=self.model, temperature=self.temperature,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}])
            text = r.choices[0].message.content
        else:
            raise ValueError(self.kind)
        self.cache[key] = text
        with self.cache_path.open("a") as fh:
            fh.write(json.dumps({"key": key, "text": text}) + "\n")
        return text


def _mock_answer(prompt, truth=None, labels=None, report=None, rng=None, selfcheck=False):
    """Fake LLM for testing the pipeline only. Its numbers mean nothing."""
    rng = rng or np.random.default_rng(0)
    if selfcheck:
        return json.dumps({"verdict": "confirm" if rng.random() < 0.85 else "reject", "reason": "mock"})
    hard = truth in (3, 9, 15)
    correct = rng.random() < (0.35 if hard else 0.75)
    f = truth if correct else rng.choice([k for k in labels.fault_code if k != truth])
    ev = [labels.var_code[v] for v in report["top_vars"][:3]]
    if rng.random() < 0.2:  # occasional hallucinated evidence
        ev.append(labels.var_code[int(rng.integers(52))])
    return json.dumps({"diagnosis": labels.fault_code[int(f)], "evidence": ev,
                       "confidence": float(np.clip(rng.normal(0.75, 0.15), 0, 1)), "reasoning": "mock"})


def diagnose(client: LLMClient, report: dict, labels: Labels, truth=None, rng=None) -> dict:
    prompt = build_prompt(report, labels)
    ans = parse_json(client(prompt, truth=truth, labels=labels, report=report, rng=rng))
    fault = labels.code_to_fault.get(str(ans.get("diagnosis", "")).strip())
    evidence = [labels.code_to_var.get(str(e).strip()) for e in ans.get("evidence", [])]
    try:
        conf = float(ans.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0
    sc = parse_json(client(build_selfcheck_prompt(prompt, ans), truth=truth, labels=labels,
                           report=report, rng=rng, selfcheck=True))
    return {
        "llm_fault": fault,                      # None if unparseable
        "llm_evidence": evidence,                # None entries = cited a variable that does not exist
        "llm_confidence": conf,
        "llm_selfcheck_confirm": str(sc.get("verdict", "")).lower() == "confirm",
        "llm_raw": ans,
    }
