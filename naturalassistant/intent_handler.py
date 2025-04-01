async def match_intent(message, config_manager):
    intents = await config_manager.list_intents()
    for phrase, intent in intents.items():
        if phrase.lower() in message.lower():
            return intent
    return None
