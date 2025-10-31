"""Test script to verify OpenWeatherMap API access and rate limiting."""
import time
from weather_service import WeatherService

def test_api():
    service = WeatherService(api_key="bd5e378503939ddaee76f12ad7a97608")
    cities = ["London", "Paris", "New York", "Tokyo", "Sydney"]
    
    print("Testing OpenWeatherMap API access with rate limit handling:")
    print("-" * 50)
    
    for i in range(3):  # Test multiple rounds
        print(f"\nRound {i+1}:")
        for city in cities:
            try:
                data = service.get_weather(city)
                print(f"{city}:")
                print(f"  Temperature: {data['temperature']}°C")
                print(f"  Humidity: {data['humidity']}%")
                print(f"  Wind: {data['wind']} km/h")
                print(f"  Condition: {data['condition']}")
            except Exception as e:
                print(f"Error fetching {city}: {e}")
            time.sleep(1)  # Small delay between requests
            print()
        
        if i < 2:  # Don't wait after the last round
            print("Waiting 5 seconds before next round...")
            time.sleep(5)

if __name__ == "__main__":
    test_api()