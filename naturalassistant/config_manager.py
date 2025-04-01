class ConfigManager:
    def __init__(self, config):
        self.config = config

    async def add_intent(self, phrase, action, server_id, roles):
        intents = await self.config.custom("intents").all()
        intents[phrase] = {"action": action, "server_id": server_id, "roles": roles}
        await self.config.custom("intents").set(intents)

    async def remove_intent(self, phrase):
        intents = await self.config.custom("intents").all()
        intents.pop(phrase, None)
        await self.config.custom("intents").set(intents)

    async def list_intents(self):
        intents = await self.config.custom("intents").all()
        return intents or {}

    async def set_ptero_api_key(self, api_key):
        api_keys = await self.config.custom("api_keys").all()
        if not api_keys:
            api_keys = {"ptero": None, "gpt": None}  # Ensure default structure
        api_keys["ptero"] = api_key
        await self.config.custom("api_keys").set(api_keys)

    async def get_ptero_api_key(self):
        api_keys = await self.config.custom("api_keys").all()
        if not api_keys:
            api_keys = {"ptero": None, "gpt": None}  # Ensure default structure
        return api_keys.get("ptero", None)

    async def set_gpt_api_key(self, api_key):
        api_keys = await self.config.custom("api_keys").all()
        if not api_keys:
            api_keys = {"ptero": None, "gpt": None}  # Ensure default structure
        api_keys["gpt"] = api_key
        await self.config.custom("api_keys").set(api_keys)

    async def get_gpt_api_key(self):
        api_keys = await self.config.custom("api_keys").all()
        if not api_keys:
            api_keys = {"ptero": None, "gpt": None}  # Ensure default structure
        return api_keys.get("gpt", None)
