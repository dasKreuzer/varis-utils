import aiohttp

class PterodactylAPI:
    def __init__(self, config_manager):
        self.config_manager = config_manager

    async def handle_action(self, action, server_id):
        api_key = await self.config_manager.get_ptero_api_key()
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        url = f"https://your.pterodactyl.panel/api/client/servers/{server_id}/power"

        async with aiohttp.ClientSession(headers=headers) as session:
            if action in ["start", "stop", "restart"]:
                payload = {"signal": action}
                async with session.post(url, json=payload) as resp:
                    if resp.status == 204:
                        return f"Server {action} command sent successfully."
                    return f"Failed to {action} server: {resp.status}"
            elif action == "status":
                async with session.get(f"{url}/resources") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return f"Server status: {data['attributes']['current_state']}"
                    return f"Failed to fetch server status: {resp.status}"
