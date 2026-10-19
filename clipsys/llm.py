import json
import re
import anthropic
from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL

_client = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("Set ANTHROPIC_API_KEY in .env")
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def ask_json(system: str, user: str, max_tokens: int = 4000):
    """Ask Claude and parse a JSON object/array out of the reply."""
    msg = client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system + "\nReply with valid JSON only, no prose, no code fences.",
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    return json.loads(text)
