import json

import anthropic


def build_prompt(template: str, card_data: str, mechanics: str) -> str:
    """Substitute placeholders into the prompt template."""
    prompt = template.replace("CARD_LIST_PLACEHOLDER", card_data)
    return prompt.replace("MECHANICS_PLACEHOLDER", mechanics)


def strip_markdown_fences(text: str) -> str:
    """Remove leading/trailing markdown code fences from a string."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def parse_claude_response(raw_text: str):
    """Strip fences and parse JSON; return raw string on failure."""
    text = strip_markdown_fences(raw_text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return raw_text


DEFAULT_MODEL = "claude-opus-4-8"


def call_claude(api_key: str, prompt: str, model: str = DEFAULT_MODEL):
    """Call the Anthropic API. Returns (result, error_response) tuple.

    On success: (parsed_result, None).
    On failure: (None, (error_dict, status_code)).
    """
    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = message.content[0].text
        return parse_claude_response(raw_text), None
    except anthropic.AuthenticationError:
        return None, ({"error": "Invalid API key"}, 401)
    except anthropic.APIError as e:
        return None, ({"error": f"API error: {e.message}"}, 502)
