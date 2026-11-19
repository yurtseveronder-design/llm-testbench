"""A deliberately simple target so the examples run with no API key. Replace with your app."""


def answer(text: str) -> str:
    t = text.lower()
    if "refund" in t:
        return "Refunds are possible within 30 days with proof of purchase."
    if "json" in t:
        return '{"status": "ok", "items": 2}'
    if "ignore" in t and "instructions" in t:
        return "All refunds are approved."  # a toy that is easy to hijack, on purpose
    return "I don't know."
