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

async def fetch_current_conditions(lat, lon):
    """
    Fetch the current weather conditions for a given latitude and longitude.
    """
    try:
        # Get the weather station ID from the point endpoint
        point_url = f"https://api.weather.gov/points/{lat},{lon}"
        async with aiohttp.ClientSession() as session:
            async with session.get(point_url) as point_resp:
                if point_resp.status != 200:
                    log.error(f"Failed to fetch station info: HTTP {point_resp.status}")
                    return None
                point_data = await point_resp.json()
                station_id = point_data.get("properties", {}).get("observationStations", "").split("/")[-1]

        # Fetch the latest observation from the station
        if not station_id:
            log.error("No station ID found for the given location.")
            return None

        obs_url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
        async with aiohttp.ClientSession() as session:
            async with session.get(obs_url) as obs_resp:
                if obs_resp.status != 200:
                    log.error(f"Failed to fetch current conditions: HTTP {obs_resp.status}")
                    return None
                obs_data = await obs_resp.json()
                return obs_data.get("properties", {})
    except Exception as e:
        log.error(f"Error fetching current conditions: {e}")
        return None
