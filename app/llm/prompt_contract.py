import json
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List


class PromptMode(str, Enum):
    CALCULATION_LOCKED = "calculation_locked"
    EXPLORATORY = "exploratory"


class PromptContractError(Exception):
    pass


class PayloadValidationError(PromptContractError):
    pass


@dataclass
class PromptContract:
    mode: PromptMode
    lang: str = "en"
    year: int = 2026

    required_fields: List[str] = field(default_factory=lambda: [
        "four_pillars",
        "five_elements",
        "day_master"
    ])

    def validate_payload(self, payload: Dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise PayloadValidationError("Payload must be a dict")

        missing = [f for f in self.required_fields if f not in payload]
        if missing:
            raise PayloadValidationError(f"Missing fields: {missing}")

        fp = payload["four_pillars"]
        for k in ["year", "month", "day", "hour"]:
            if k not in fp:
                raise PayloadValidationError(f"four_pillars missing {k}")

    def system_role(self) -> str:
        return "You are a professional Chinese BaZi analyst."

    def constraints(self) -> str:
        rules = [
            "The provided Four Pillars are FINAL and AUTHORITATIVE.",
            "DO NOT recalculate or infer pillars.",
            "DO NOT rebalance or reinterpret Five Elements strength.",
            "INTERPRETATION ONLY, not calculation.",
            "Ignore contradictory or redundant data."
        ]
        if self.mode == PromptMode.EXPLORATORY:
            rules.append(
                "Exploratory reasoning is allowed but must not modify the pillars."
            )
        return "\n".join(f"- {r}" for r in rules)

    def output_schema(self) -> Dict[str, Any]:
        return {
            "lucky_elements": {
                "favorable_elements": [],
                "unfavorable_elements": []
            },
            "lucky_colors_numbers": {
                "colors": [],
                "numbers": []
            },
            "regional_advice": {
                "suitable_regions": [],
                "avoid_regions": [],
                "directions": "",
                "reasoning": ""
            },
            "career_and_investment": {
                "suitable_careers": [],
                "unsuitable_careers": [],
                "investment_tendency": ""
            },
            f"year_{self.year}_outlook": {
                "theme": "",
                "health": "",
                "relationships": "",
                "career": "",
                "investment": "",
                "key_advice": ""
            },
            "amulet": ""
        }

    def instructions(self) -> str:
        base = [
            f"Focus on what is unique in {self.year}.",
            "Avoid generic advice.",
            "Ground reasoning strictly in BaZi logic.",
            "Return JSON ONLY."
        ]
        if self.mode == PromptMode.CALCULATION_LOCKED:
            base.append("Do NOT speculate beyond given data.")
        return "\n".join(f"{i+1}. {b}" for i, b in enumerate(base))

    def build_prompt(self, payload: Dict[str, Any]) -> str:
        self.validate_payload(payload)

        return f"""
{self.system_role()}

MODE: {self.mode.value}

CONSTRAINTS:
{self.constraints()}

INPUT:
{json.dumps(payload, ensure_ascii=False, indent=2)}

OUTPUT SCHEMA:
{json.dumps(self.output_schema(), ensure_ascii=False, indent=2)}

INSTRUCTIONS:
{self.instructions()}

Language: {self.lang}
""".strip()
