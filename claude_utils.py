import json
import re

import anthropic


def build_prompt(template: str, card_data: str, mechanics: str) -> str:
    """Substitute placeholders into the prompt template."""
    prompt = template.replace("CARD_LIST_PLACEHOLDER", card_data)
    return prompt.replace("MECHANICS_PLACEHOLDER", mechanics)


def build_feedback_prompt(template: str, card_data: str, mechanics: str, pass1_json: str) -> str:
    """Substitute placeholders into a feedback/review prompt template."""
    prompt = build_prompt(template, card_data, mechanics)
    return prompt.replace("PASS1_RESULTS_PLACEHOLDER", pass1_json)


def strip_markdown_fences(text: str) -> str:
    """Remove leading/trailing markdown code fences from a string."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def extract_fenced_json(text: str):
    """Parse the last fenced code block containing valid JSON, or None.

    Handles responses where prose (e.g. recall lines) precedes the JSON block.
    """
    fences = re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    for candidate in reversed(fences):
        try:
            return json.loads(candidate.strip())
        except json.JSONDecodeError:
            continue
    return None


def parse_claude_response(raw_text: str):
    """Extract and parse JSON from the response; return raw string on failure."""
    parsed = extract_fenced_json(raw_text)
    if parsed is not None:
        return parsed
    text = strip_markdown_fences(raw_text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return raw_text


DEFAULT_MODEL = "claude-opus-4-8"


def call_claude(api_key: str, prompt: str, model: str = DEFAULT_MODEL, temperature: float = None, system: str = None):
    """Call the Anthropic API. Returns (result, error_response) tuple.

    On success: (parsed_result, None).
    On failure: (None, (error_dict, status_code)).

    system: optional system prompt (e.g. to enforce JSON-only output).
    """
    try:
        client = anthropic.Anthropic(api_key=api_key)
        kwargs = dict(model=model, max_tokens=16000, messages=[{"role": "user", "content": prompt}])
        if temperature is not None:
            kwargs["temperature"] = temperature
        if system is not None:
            kwargs["system"] = system
        message = client.messages.create(**kwargs)
        text_block = next((b for b in message.content if b.type == "text"), None)
        if text_block is None:
            return None, ({"error": f"No text block in response (blocks: {[b.type for b in message.content]})"}, 502)
        return parse_claude_response(text_block.text), None
    except anthropic.AuthenticationError:
        return None, ({"error": "Invalid API key"}, 401)
    except anthropic.APIError as e:
        return None, ({"error": f"API error: {e.message}"}, 502)
