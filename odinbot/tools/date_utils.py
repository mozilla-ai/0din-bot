import httpx
from typing import Dict, Any
from datetime import datetime
import pytz


async def get_current_gmt_time() -> Dict[str, Any]:
    """
    Get the current GMT time by calling a time API.
    
    Returns:
        Dict containing the current GMT time information
    """
    try:
        # Using worldtimeapi.org which provides accurate GMT time
        async with httpx.AsyncClient() as client:
            response = await client.get("http://worldtimeapi.org/api/timezone/Etc/GMT")
            response.raise_for_status()
            data = response.json()
            
            return {
                "current_gmt_time": data["datetime"],
                "gmt_date": data["datetime"].split("T")[0],  # YYYY-MM-DD format
                "gmt_time": data["datetime"].split("T")[1].split(".")[0],  # HH:MM:SS format
                "timezone": "GMT",
                "utc_offset": data["utc_offset"],
                "day_of_week": data["day_of_week"],
                "day_of_year": data["day_of_year"]
            }
    except Exception as e:
        # Fallback to local time conversion if API fails
        gmt_tz = pytz.timezone('GMT')
        now = datetime.now(gmt_tz)
        
        return {
            "current_gmt_time": now.isoformat(),
            "gmt_date": now.strftime("%Y-%m-%d"),
            "gmt_time": now.strftime("%H:%M:%S"),
            "timezone": "GMT",
            "utc_offset": "+00:00",
            "day_of_week": now.strftime("%A"),
            "day_of_year": now.timetuple().tm_yday,
            "note": "Using fallback local time conversion"
        } 