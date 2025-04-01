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
        return await self.config.custom("intents").all()

    async def set_ptero_api_key(self, api_key):
        await self.config.custom("api_keys").ptero.set(api_key)

    async def get_ptero_api_key(self):
        return await self.config.custom("api_keys").ptero()

    async def set_gpt_api_key(self, api_key):
        await self.config.custom("api_keys").gpt.set(api_key)

    async def get_gpt_api_key(self):
        return await self.config.custom("api_keys").gpt()
