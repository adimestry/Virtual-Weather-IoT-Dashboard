"""Real-world weather data service using Visual Crossing Weather API.

This module handles fetching and caching weather data from Visual Crossing.
Requires an API key from https://www.visualcrossing.com/ (free tier available).
"""
import os
import time
import json
from datetime import datetime, timezone
from typing import Dict, Optional
import requests

class WeatherService:
    """Visual Crossing Weather API client with caching."""
    
    BASE_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"
    CACHE_DURATION = 300  # Cache weather data for 5 minutes
    CACHE_DURATION = 600  # Cache weather data for 10 minutes (API updates every ~10 min)
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the weather service.
        
        Args:
            api_key: OpenWeatherMap API key. If None, looks for OPENWEATHERMAP_API_KEY env var.
        """
        self.api_key = api_key or os.getenv('OPENWEATHERMAP_API_KEY')
        if not self.api_key:
            raise ValueError(
                "OpenWeatherMap API key required. Either pass as api_key or "
                "set OPENWEATHERMAP_API_KEY environment variable."
            )
        
        # Cache structure: {city: (timestamp, data)}
        self._cache: Dict[str, tuple[float, dict]] = {}
    
    def get_weather(self, city: str, use_cache_on_error: bool = True) -> dict:
        """Get current weather for a city.
        
        Returns cached data if available and fresh, otherwise fetches from API.
        
        Args:
            city: Name of the city (e.g., "London", "Paris")
            use_cache_on_error: If True, returns cached data even if expired when API fails
            
        Returns:
            dict with weather data normalized to our format:
            {
                "temperature": float (°C),
                "humidity": float (%),
                "wind": float (km/h),
                "condition": str (emoji)
            }
        
        Raises:
            requests.RequestException: On API error if no cached data available
            ValueError: On invalid city
        """
        # Check cache first
        cached_data = None
        if city in self._cache:
            timestamp, data = self._cache[city]
            if time.time() - timestamp < self.CACHE_DURATION:
                return data.copy()  # Return cached data if fresh
            cached_data = data  # Save expired cache for fallback
        
        # Fetch from API
        params = {
            "unitGroup": "metric",
            "key": self.api_key,
            "contentType": "json"
        }
        
        try:
            url = f"{self.BASE_URL}/{city}"
            print(f"Fetching weather data for {city}...")
            response = requests.get(url, params=params)
            response.raise_for_status()  # Raises on 4XX/5XX errors
            print(f"Received data for {city}: {response.text[:200]}...")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429 and use_cache_on_error and cached_data:
                print(f"Rate limited for {city}, using cached data")
                return cached_data.copy()
            if e.response.status_code == 429:
                print(f"API rate limit exceeded. Please wait a few minutes or check API key status.")
            elif e.response.status_code == 401:
                print(f"Invalid API key or key not yet activated. Please check your API key.")
            raise
        
        raw = response.json()
        
        # Convert API response to our format
        current = raw['currentConditions']
        data = {
            "temperature": round(current["temp"], 1),
            "humidity": round(current["humidity"], 1),
            "wind": round(current["windspeed"] * 1.60934, 1),  # Convert mph to km/h
        }
        
        # Map Visual Crossing conditions to our emoji
        conditions = current["conditions"].lower()
        if "thunder" in conditions:
            data["condition"] = "⛈️"
        elif "rain" in conditions or "drizzle" in conditions or "shower" in conditions:
            data["condition"] = "🌧️"
        elif "snow" in conditions or "ice" in conditions or "sleet" in conditions:
            data["condition"] = "🌨️"
        elif "fog" in conditions or "mist" in conditions or "haze" in conditions:
            data["condition"] = "🌫️"
        elif "clear" in conditions and "cloud" not in conditions:
            data["condition"] = "☀️"
        elif "partly cloudy" in conditions or "scattered clouds" in conditions:
            data["condition"] = "🌤️"
        elif "cloud" in conditions or "overcast" in conditions:
            data["condition"] = "☁️"
        else:
            # If no condition matches, store the actual condition for debugging
            print(f"Unknown condition: {conditions}")
            data["condition"] = "❓"
        
        # Cache the result
        self._cache[city] = (time.time(), data)
        return data.copy()