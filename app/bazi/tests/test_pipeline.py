from app.bazi.pipeline import run_bazi_analysis
from app.llm.prompt_contract import PromptMode


PAYLOAD = {
    "four_pillars": {
        "year": "乙巳",
        "month": "丁酉",
        "day": "庚子",
        "hour": "壬午"
    },
    "five_elements": {
        "wood": "weak",
        "fire": "moderate",
        "earth": "weak",
        "metal": "strong",
        "water": "moderate"
    },
    "day_master": "庚金"
}


def test_all_models():
    for model in ["oa", "qw", "hy"]:
        print("\n==============================")
        print("MODEL:", model)
        print("==============================")

        res = run_bazi_analysis(
            payload=PAYLOAD,
            model=model,
            mode=PromptMode.CALCULATION_LOCKED,
            year=2026,
            lang="en"
        )

        print(res)


if __name__ == "__main__":
    test_all_models()
