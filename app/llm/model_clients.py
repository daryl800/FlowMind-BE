import json
from typing import Dict


# ---------------------------
# Base interface
# ---------------------------

def _mock_response(prompt: str) -> Dict:
    """
    Deterministic fake response for testing pipeline integrity.
    Replace with real API calls later.
    """
    return {
        "mock": True,
        "prompt_hash": hash(prompt) % 100000
    }


# ---------------------------
# OpenAI-style (oa)
# ---------------------------

def call_oa(prompt: str, temperature: float = 0.2) -> Dict:
    print("[OA] temperature =", temperature)
    return _mock_response(prompt)


# ---------------------------
# Qwen / Tongyi (qw)
# ---------------------------

def call_qw(prompt: str, temperature: float = 0.3) -> Dict:
    print("[QW] temperature =", temperature)
    return _mock_response(prompt)


# ---------------------------
# Hunyuan / hybrid (hy)
# ---------------------------

def call_hy(prompt: str, temperature: float = 0.25) -> Dict:
    print("[HY] temperature =", temperature)
    return _mock_response(prompt)
