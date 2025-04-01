from .gpt_formatter import format_response_with_gpt

async def match_intent(message, config_manager):
    intents = await config_manager.list_intents()
    for phrase, intent in intents.items():
        if phrase.lower() in message.lower():
            return intent

    # Fallback: Use GPT to predict intent
    try:
        predicted_intent = await format_response_with_gpt(
            f"Predict the intent of this message: '{message}'. "
            "Return the action, server_id, and roles in JSON format."
        )
        return eval(predicted_intent)  # Convert GPT's JSON-like response to a Python dictionary
    except Exception:
        return None
