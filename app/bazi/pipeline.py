from typing import Dict
from app.llm.prompt_contract import PromptContract, PromptMode
from app.llm.model_clients import call_oa, call_qw, call_hy


MODEL_DISPATCH = {
    "oa": call_oa,
    "qw": call_qw,
    "hy": call_hy
}


def run_bazi_analysis(
    payload: Dict,
    model: str,
    mode: PromptMode,
    year: int = 2026,
    lang: str = "en"
) -> Dict:
    if model not in MODEL_DISPATCH:
        raise ValueError(f"Unsupported model: {model}")

    contract = PromptContract(
        mode=mode,
        year=year,
        lang=lang
    )

    prompt = contract.build_prompt(payload)

    # Deterministic temperatures per mode
    temperature = 0.15 if mode == PromptMode.CALCULATION_LOCKED else 0.45

    result = MODEL_DISPATCH[model](
        prompt=prompt,
        temperature=temperature
    )

    return {
        "model": model,
        "mode": mode.value,
        "result": result
    }
