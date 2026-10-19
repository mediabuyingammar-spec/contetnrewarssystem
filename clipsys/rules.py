"""Reads campaign terms & conditions and turns them into machine-checkable rules."""
from .llm import ask_json

RULES_SYSTEM = """You analyse content-reward / clipping campaign terms and conditions.
Extract rules as JSON with exactly these keys:
{
 "clipping_allowed": true|false,          // are third-party clips of the creator's content explicitly allowed?
 "allowed_source_urls": [str],            // source video/channel URLs the campaign provides or allows
 "min_seconds": int|null,
 "max_seconds": int|null,
 "required_hashtags": [str],
 "required_mentions_or_credit": str|null,
 "required_platforms": [str],             // e.g. ["tiktok","youtube","instagram"] or [] if unrestricted
 "banned_content": [str],
 "other_requirements": [str],
 "unclear_points": [str]                  // anything ambiguous or missing
}
If the text does not clearly allow clipping, set clipping_allowed to false. Never assume permission."""


def extract_rules(terms_text: str) -> dict:
    return ask_json(RULES_SYSTEM, terms_text[:30000])


def campaign_usable(rules: dict) -> tuple[bool, str]:
    if not rules.get("clipping_allowed"):
        return False, "campaign does not clearly allow clipping"
    if not rules.get("allowed_source_urls"):
        return False, "campaign lists no source URLs"
    return True, "ok"


def check_clip(rules: dict, duration: float, caption: str) -> tuple[bool, str]:
    """Hard gate every clip must pass before it can be queued for posting."""
    lo, hi = rules.get("min_seconds"), rules.get("max_seconds")
    if lo and duration < lo:
        return False, f"shorter than {lo}s"
    if hi and duration > hi:
        return False, f"longer than {hi}s"
    low = caption.lower()
    for tag in rules.get("required_hashtags", []):
        if tag.lower() not in low:
            return False, f"missing required hashtag {tag}"
    credit = rules.get("required_mentions_or_credit")
    if credit and credit.lower() not in low:
        return False, f"missing required credit {credit}"
    return True, "ok"
