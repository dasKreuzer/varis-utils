import aiohttp
import logging

log = logging.getLogger("nwsshutdown")

async def fetch_alerts(lat, lon):
    url = f"https://api.weather.gov/alerts/active?point={lat},{lon}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    log.error(f"Failed to fetch alerts: HTTP {resp.status}")
                    return []
                data = await resp.json()
                return data.get("features", [])
        except Exception as e:
            log.error(f"Error fetching alerts: {e}")
            return []
