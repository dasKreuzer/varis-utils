import aiohttp

async def fetch_alerts(lat, lon):
    url = f"https://api.weather.gov/alerts/active?point={lat},{lon}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return data.get("features", [])
