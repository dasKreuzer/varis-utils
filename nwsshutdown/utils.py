import aiohttp
import logging
from bs4 import BeautifulSoup

log = logging.getLogger("nwsshutdown")

async def fetch_alerts(lat, lon):
    url = f"https://api.weather.gov/alerts/active?point={lat},{lon}"
    async with aiohttp.ClientSession() as session:  # Reuse session
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
        async with aiohttp.ClientSession() as session:  # Reuse session
            # Get the weather station ID from the point endpoint
            point_url = f"https://api.weather.gov/points/{lat},{lon}"
            async with session.get(point_url) as point_resp:
                if point_resp.status != 200:
                    log.error(f"Failed to fetch station info: HTTP {point_resp.status}")
                    return None
                point_data = await point_resp.json()
                station_url = point_data.get("properties", {}).get("observationStations")
                if not station_url:
                    log.error("No observation stations found for the given location.")
                    return None

            # Fetch the latest observation from the first station
            async with session.get(station_url) as stations_resp:
                if stations_resp.status != 200:
                    log.error(f"Failed to fetch station list: HTTP {stations_resp.status}")
                    return None
                stations_data = await stations_resp.json()
                stations = stations_data.get("observationStations", [])
                if not stations:
                    log.error("No stations available for the given location.")
                    return None
                station_id = stations[0].split("/")[-1]

            obs_url = f"https://api.weather.gov/stations/{station_id}/observations/latest"
            async with session.get(obs_url) as obs_resp:
                if obs_resp.status != 200:
                    log.error(f"Failed to fetch current conditions: HTTP {obs_resp.status}")
                    return None
                obs_data = await obs_resp.json()
                return obs_data.get("properties", {})
    except Exception as e:
        log.error(f"Error fetching current conditions: {e}")
        return None

async def fetch_mesoscale_discussions():
    """
    Fetch the latest mesoscale discussions from the SPC.
    """
    url = "https://www.spc.noaa.gov/products/md/"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    log.error(f"Failed to fetch mesoscale discussions: HTTP {resp.status}")
                    return None
                html = await resp.text()

        # Parse the HTML to extract mesoscale discussions (basic scraping)
        soup = BeautifulSoup(html, "html.parser")
        discussions = []
        for item in soup.select("pre a"):
            if "md" in item["href"]:  # Filter links to mesoscale discussions
                discussions.append({
                    "title": item.text.strip(),
                    "link": f"https://www.spc.noaa.gov/products/md/{item['href']}"
                })

        return discussions
    except Exception as e:
        log.error(f"Error fetching mesoscale discussions: {e}")
        return None
