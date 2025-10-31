"""Test script to verify Visual Crossing Weather API integration."""
from weather_service import WeatherService

def test_api():
    # Initialize with Visual Crossing API key
    service = WeatherService(api_key="TYPZAV86LVECNE9JMXGJYTFNT")
    
    # Test with Mumbai, London and a few other cities
    cities = ["Mumbai", "London", "Delhi", "Bangalore"]
    
    print("Testing Visual Crossing Weather API access:")
    print("-" * 40)
    
    for city in cities:
        try:
            data = service.get_weather(city)
            print(f"\n{city}:")
            print(f"  Temperature: {data['temperature']}°C")
            print(f"  Humidity: {data['humidity']}%")
            print(f"  Wind: {data['wind']} km/h")
            print(f"  Condition: {data['condition']}")
        except Exception as e:
            print(f"\nError fetching {city}: {str(e)}")

if __name__ == "__main__":
    test_api()