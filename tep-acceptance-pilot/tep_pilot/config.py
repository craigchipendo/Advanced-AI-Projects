"""Experiment settings for the TEP acceptance-rule pilot."""
from dataclasses import dataclass, field
from pathlib import Path

# 41 measured variables (XMEAS 1-41) followed by 11 manipulated variables (XMV 1-11),
# in the column order of the Braatz Tennessee Eastman dataset.
VARIABLES = [
    "A feed (stream 1)", "D feed (stream 2)", "E feed (stream 3)", "A and C feed (stream 4)",
    "Recycle flow (stream 8)", "Reactor feed rate (stream 6)", "Reactor pressure", "Reactor level",
    "Reactor temperature", "Purge rate (stream 9)", "Separator temperature", "Separator level",
    "Separator pressure", "Separator underflow (stream 10)", "Stripper level", "Stripper pressure",
    "Stripper underflow (stream 11)", "Stripper temperature", "Stripper steam flow", "Compressor work",
    "Reactor cooling water outlet temperature", "Separator cooling water outlet temperature",
    "Reactor feed analysis A", "Reactor feed analysis B", "Reactor feed analysis C",
    "Reactor feed analysis D", "Reactor feed analysis E", "Reactor feed analysis F",
    "Purge gas analysis A", "Purge gas analysis B", "Purge gas analysis C", "Purge gas analysis D",
    "Purge gas analysis E", "Purge gas analysis F", "Purge gas analysis G", "Purge gas analysis H",
    "Product analysis D", "Product analysis E", "Product analysis F", "Product analysis G",
    "Product analysis H",
    "D feed flow valve", "E feed flow valve", "A feed flow valve", "A and C feed flow valve",
    "Compressor recycle valve", "Purge valve", "Separator liquid flow valve",
    "Stripper liquid product flow valve", "Stripper steam valve", "Reactor cooling water flow valve",
    "Condenser cooling water flow valve",
]
assert len(VARIABLES) == 52

# Standard IDV fault descriptions. 0 = normal operation.
FAULTS = {
    0: "No fault: normal operation",
    1: "A/C feed ratio step, B composition constant (stream 4)",
    2: "B composition step, A/C ratio constant (stream 4)",
    3: "D feed temperature step (stream 2)",
    4: "Reactor cooling water inlet temperature step",
    5: "Condenser cooling water inlet temperature step",
    6: "A feed loss step (stream 1)",
    7: "C header pressure loss, reduced availability (stream 4)",
    8: "A, B, C feed composition random variation (stream 4)",
    9: "D feed temperature random variation (stream 2)",
    10: "C feed temperature random variation (stream 4)",
    11: "Reactor cooling water inlet temperature random variation",
    12: "Condenser cooling water inlet temperature random variation",
    13: "Reaction kinetics slow drift",
    14: "Reactor cooling water valve sticking",
    15: "Condenser cooling water valve sticking",
    21: "Stream 4 valve fixed at steady-state position",
}


@dataclass
class Config:
    data_dir: Path = Path("data")
    results_dir: Path = Path("results")
    # Faults under study (0 = normal is always added). 3, 9 and 15 are known to be
    # nearly undetectable, which makes them the test of whether the rule defers.
    faults: list = field(default_factory=lambda: [1, 2, 3, 4, 5, 6, 7, 9, 14, 15])
    window: int = 20            # samples per window (3-minute sampling, so 1 hour)
    train_stride: int = 5       # overlap for training windows
    test_stride: int = 20       # non-overlapping test windows
    test_fault_start: int = 160 # in *_te.dat files the fault starts after sample 160
    windows_per_class: int = 20 # test windows per class sent to the LLM
    calib_fraction: float = 0.4 # last part of each training file used for conformal calibration
    top_k: int = 6              # deviating variables shown to the LLM
    alpha: float = 0.1          # conformal miscoverage level
    max_set_size: int = 1       # conformal set must be this small to accept
    seed: int = 0
    # LLM
    llm: str = "mock"           # mock | ollama | openai
    model: str = "llama3.1:8b"  # e.g. "qwen2.5:7b" for ollama, "gpt-4o-mini" for openai
    masked: bool = False        # contamination control: hide TEP name, shuffle IDs
    temperature: float = 0.0
