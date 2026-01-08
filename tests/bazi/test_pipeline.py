from app.bazi.pipeline import run_bazi_analysis
from app.llm.prompt_contract import PromptMode


PAYLOAD = {
        "pillars": {
            "year": {"gan": "Bing", "zhi": "Wu"},
            "month": {"gan": "Wu", "zhi": "Xu"},
            "day": {"gan": "Xin", "zhi": "Chou"},
            "hour": {"gan": "Xin", "zhi": "Mao"},
        },
        "day_master": "Xin",
        "five_elements_strength": {            
            "Wood": 1,
            "Fire": 3,
            "Earth": 2,
            "Metal": 2,
            "Water": 0
        }
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
