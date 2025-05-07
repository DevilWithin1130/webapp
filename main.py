import json
import os
import pathlib
import requests
import random
import pycountry
import smtplib
import pytz
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from openai import OpenAI

def obtain_weather_data(config, location=None):
    """Fetch weather data from OpenWeatherMap API."""   
    # Accessing weather configuration
    weather_config = config.get('api', {}).get('weather')

    if weather_config is None:
        raise ValueError("Weather configuration not found in configuration.json")
    
    # Get API key and endpoint
    api_key = weather_config.get('apiKey')
    weather_endpoint = weather_config.get('weatherEndpoint')
    geo_endpoint = weather_config.get('geoEndpoint')
    
    # Get location from parameters or fall back to default location
    if location is None:
        location = config.get('preferences', {}).get('defaultLocation', {})
    
    city = location.get('city')
    country = location.get('country')

    if not city or not country:
        raise ValueError("Location information is missing or incomplete")

    # Construct the URL for geocoding
    geo_url = f"{geo_endpoint}q={city},{country}&limit=1&appid={api_key}"

    # Make requests to obtain the coordinates
    response = requests.get(geo_url)
    response.raise_for_status()
    geo_data = response.json()
        
    if not geo_data:
        raise ValueError(f"No location found for {city}, {country}")
            
    # Extract coordinates from the first result
    lat = geo_data[0]['lat']
    lon = geo_data[0]['lon']

    # Construct the URL for weather data
    weather_url = f"{weather_endpoint}lat={lat}&lon={lon}&appid={api_key}&units=metric"
    
    # Make request to obtain weather data
    response = requests.get(weather_url)
    response.raise_for_status()
    weather_data = response.json()
    print(f"Raw Weather Data for {city}, {country}: \n", weather_data)
    return weather_data

def obtain_forecast_data(config, location=None):
    """Fetch weather forecast data from OpenWeatherMap One Call API 3.0."""
    # Accessing weather configuration
    weather_config = config.get('api', {}).get('weather')

    if weather_config is None:
        raise ValueError("Weather configuration not found in configuration.json")
    
    # Get API key and endpoint
    api_key = weather_config.get('apiKey')
    onecall_endpoint = weather_config.get('oneCallEndpoint')
    geo_endpoint = weather_config.get('geoEndpoint')
    
    # Get location from parameters or fall back to default location
    if location is None:
        location = config.get('preferences', {}).get('defaultLocation', {})
    
    city = location.get('city')
    country = location.get('country')

    if not city or not country:
        raise ValueError("Location information is missing or incomplete")

    # Construct the URL for geocoding
    geo_url = f"{geo_endpoint}q={city},{country}&limit=1&appid={api_key}"

    # Make requests to obtain the coordinates
    response = requests.get(geo_url)
    response.raise_for_status()
    geo_data = response.json()
        
    if not geo_data:
        raise ValueError(f"No location found for {city}, {country}")
            
    # Extract coordinates from the first result
    lat = geo_data[0]['lat']
    lon = geo_data[0]['lon']

    # Construct the URL for one call API
    # Include current weather, hourly forecast, and daily forecast
    # Exclude minutely alerts to reduce data size
    onecall_url = f"{onecall_endpoint}lat={lat}&lon={lon}&appid={api_key}&units=metric&exclude=minutely,alerts"
    
    # Make request to obtain forecast data
    response = requests.get(onecall_url)
    response.raise_for_status()
    forecast_data = response.json()
    print(f"Raw Forecast Data for {city}, {country}: \n", forecast_data)
    return forecast_data

def handle_weather_data(weather_data):
    """Process weather data and extract relevant information."""
    if not weather_data or 'main' not in weather_data:
        print("Weather data not available")
        return None
    
    # Location information
    location = weather_data.get('name', 'Unknown location')
    country = weather_data.get('sys', {}).get('country', '')
    
    # Weather information
    current_temperature = weather_data['main']['temp']
    temp_min = weather_data['main']['temp_min']
    temp_max = weather_data['main']['temp_max']
    feels_like = weather_data['main']['feels_like']
    weather_type = weather_data.get('weather', [{}])[0].get('main', 'unknown')
    weather_description = weather_data.get('weather', [{}])[0].get('description', 'unknown')
    humidity = weather_data['main']['humidity']
    pressure = weather_data['main']['pressure']
    wind_speed = weather_data.get('wind', {}).get('speed','Unknown')
    wind_direction = weather_data.get('wind', {}).get('deg', 'Unknown')
    visibility = weather_data.get('visibility', 'Unknown') / 1000
    dt_timestamp = weather_data.get('dt')
    sunrise_timestamp = weather_data.get('sys', {}).get('sunrise')
    sunset_timestamp = weather_data.get('sys', {}).get('sunset')

    # Convert timestamps to human-readable format
    current_time = datetime.fromtimestamp(dt_timestamp).strftime('%Y-%m-%d %H:%M:%S') if dt_timestamp else 'Unknown'
    sunrise_time = datetime.fromtimestamp(sunrise_timestamp).strftime('%H:%M:%S') if sunrise_timestamp else 'Unknown'
    sunset_time = datetime.fromtimestamp(sunset_timestamp).strftime('%H:%M:%S') if sunset_timestamp else 'Unknown'
    
    # Format the weather information
    weather_info = {
        'location': f"{location}",
        'temperature': f"{current_temperature}°C (feels like {feels_like}°C)",
        'temperature_range': f"Min: {temp_min}°C, Max: {temp_max}°C",
        'weather_type': f"{weather_type.capitalize()}: {weather_description}",
        'current_time': current_time,
        'daylight': f"Sunrise-{sunrise_time}, Sunset-{sunset_time}",
        'humidity': f"{humidity}%",
        'pressure': f"{pressure} hPa",
        'wind': f"{wind_speed} m/s, direction {wind_direction}°",
        'visibility': f"{visibility} km"
    }
    
    print("Processed Weather Data: \n", weather_info)
    return weather_info

def process_forecast_data(forecast_data):
    """Process forecast data from the One Call API and extract relevant information."""
    if not forecast_data:
        print("Forecast data not available")
        return {}
    
    # Extract current weather data
    current = forecast_data.get('current', {})
    hourly = forecast_data.get('hourly', [])
    daily = forecast_data.get('daily', [])
    
    # Weather information from current data
    current_temp = current.get('temp', 'Unknown')
    feels_like = current.get('feels_like', 'Unknown')
    humidity = current.get('humidity', 'Unknown')
    pressure = current.get('pressure', 'Unknown')
    wind_speed = current.get('wind_speed', 'Unknown')
    wind_direction = current.get('wind_deg', 'Unknown')
    visibility = current.get('visibility', 'Unknown') / 1000 if 'visibility' in current else 'Unknown'
    uvi = current.get('uvi', 'Unknown')
    clouds = current.get('clouds', 'Unknown')
    
    # Get weather condition
    weather_type = current.get('weather', [{}])[0].get('main', 'unknown')
    weather_description = current.get('weather', [{}])[0].get('description', 'unknown')
    
    # Get sunrise and sunset times
    sunrise = datetime.fromtimestamp(current.get('sunrise', 0)).strftime('%H:%M:%S') if 'sunrise' in current else 'Unknown'
    sunset = datetime.fromtimestamp(current.get('sunset', 0)).strftime('%H:%M:%S') if 'sunset' in current else 'Unknown'
    
    # Process hourly forecast data for specific times
    hourly_forecasts = {}
    time_slots = {
        'morning_6': 6, 'morning_8': 8, 'morning_10': 10,
        'afternoon_12': 12, 'afternoon_14': 14, 'afternoon_16': 16,
        'evening_18': 18, 'evening_20': 20, 'evening_22': 22
    }
    
    # Find min and max temperature from daily data
    temp_min = 100  # Start with a high value
    temp_max = -100  # Start with a low value
    
    if daily and len(daily) > 0:
        today = daily[0]
        temp_min = today.get('temp', {}).get('min', temp_min)
        temp_max = today.get('temp', {}).get('max', temp_max)
    
    # Find the highest precipitation probability and its time
    max_precip = 0
    max_precip_time = "None"
    max_precip_hour = None
    
    # Process hourly data
    for hour in hourly:
        dt = hour.get('dt', 0)
        hour_datetime = datetime.fromtimestamp(dt)
        hour_of_day = hour_datetime.hour
        
        # Store hourly forecast for specific times
        for slot_name, slot_hour in time_slots.items():
            if hour_of_day == slot_hour:
                hour_temp = hour.get('temp', 'Unknown')
                hour_pop = hour.get('pop', 0) * 100  # Convert to percentage
                hour_weather = hour.get('weather', [{}])[0].get('main', 'Unknown')
                
                hourly_forecasts[f"{slot_name}_temp"] = f"{hour_temp}°C"
                hourly_forecasts[f"{slot_name}_precip"] = f"{hour_pop:.0f}%"
                hourly_forecasts[f"{slot_name}_weather"] = hour_weather
        
        # Check for max precipitation probability
        pop = hour.get('pop', 0) * 100  # Convert to percentage
        if pop > max_precip:
            max_precip = pop
            max_precip_hour = hour_datetime
            max_precip_time = hour_datetime.strftime('%H:%M')
    
    # Determine main weather type for the day
    weather_counts = {}
    for hour in hourly[:24]:  # Consider only first 24 hours
        w_type = hour.get('weather', [{}])[0].get('main', 'Unknown')
        weather_counts[w_type] = weather_counts.get(w_type, 0) + 1
    
    weather_main_type = max(weather_counts.items(), key=lambda x: x[1])[0] if weather_counts else 'Unknown'
    
    # Format all the forecast information
    forecast_info = {
        'weather_type': f"{weather_type.capitalize()}: {weather_description}",
        'weather_temperature': f"{current_temp}°C (feels like {feels_like}°C)",
        'weather_temperature_range': f"Min: {temp_min}°C, Max: {temp_max}°C",
        'weather_humidity': f"{humidity}%",
        'weather_pressure': f"{pressure} hPa",
        'weather_wind': f"{wind_speed} m/s, direction {wind_direction}°",
        'weather_visibility': f"{visibility} km",
        'weather_uvi': f"{uvi}",
        'weather_clouds': f"{clouds}%",
        'weather_daylight': f"Sunrise-{sunrise}, Sunset-{sunset}",
        'temp_min': f"{temp_min}",
        'temp_max': f"{temp_max}",
        'max_precip': f"{max_precip:.0f}",
        'max_precip_time': max_precip_time,
        'weather_main_type': weather_main_type
    }
    
    # Add hourly forecasts to the forecast info
    forecast_info.update(hourly_forecasts)
    
    print("Processed Forecast Data: \n", forecast_info)
    return forecast_info

def generate_activity_suggestions(weather_info, language='en'):
    """
    Generate activity suggestions based on weather information.
    
    Args:
        weather_info: Weather information dictionary
        language: Language code for suggestions (default: 'en')
    
    Returns:
        A dictionary containing activity suggestions
    """
    # Extract relevant weather data
    weather_type = weather_info.get('weather_main_type', '').lower()
    temp_min = float(weather_info.get('temp_min', 0))
    temp_max = float(weather_info.get('temp_max', 0))
    max_precip = float(weather_info.get('max_precip', 0))
    
    # Initialize suggestion lists
    suggestions = []
    
    # Generate suggestions based on weather type and conditions
    if language.startswith('zh'):
        # Chinese suggestions
        if 'clear' in weather_type or weather_type == 'sun':
            suggestions.extend([
                "<li>晴朗的天气非常适合户外活动，如远足、野餐或公园漫步。</li>",
                "<li>在阳光下活动时，请记得涂抹防晒霜并多喝水。</li>",
                "<li>今天是拍摄户外照片的绝佳时机！</li>"
            ])
        elif 'cloud' in weather_type:
            suggestions.extend([
                "<li>多云天气适合轻度户外活动，如散步、慢跑或骑自行车。</li>",
                "<li>这是参观博物馆、美术馆或购物中心的好时机。</li>",
                "<li>多云天气下的摄影也很有质感，试试抓拍云朵变化！</li>"
            ])
        elif 'rain' in weather_type:
            suggestions.extend([
                "<li>雨天最适合室内活动，可以访问博物馆、电影院或咖啡厅。</li>",
                "<li>如需外出，请携带雨伞或穿着防水外套。</li>",
                "<li>这是在家享受阅读或看电影的好时机。</li>"
            ])
        elif 'snow' in weather_type:
            suggestions.extend([
                "<li>雪天适合冬季运动，如滑雪、雪橇或堆雪人。</li>",
                "<li>外出时请穿着保暖衣物，注意路面可能湿滑。</li>",
                "<li>这是在家享受热饮和温暖活动的好时机。</li>"
            ])
        elif 'thunder' in weather_type or 'storm' in weather_type:
            suggestions.extend([
                "<li>雷暴天气请尽量避免户外活动，留在室内安全地方。</li>",
                "<li>确保电子设备已充电，以防停电。</li>",
                "<li>这是在家享受阅读或娱乐活动的好时机。</li>"
            ])
        elif 'fog' in weather_type or 'mist' in weather_type:
            suggestions.extend([
                "<li>雾天驾驶请减速并打开车灯，保持安全距离。</li>",
                "<li>适合近距离活动，避免长途旅行。</li>",
                "<li>雾天氛围独特，摄影爱好者可以捕捉迷人景色。</li>"
            ])
        else:
            suggestions.extend([
                "<li>请根据实时天气状况调整您的活动计划。</li>",
                "<li>出门前检查最新天气预报。</li>",
                "<li>随时准备适合当天天气的服装和装备。</li>"
            ])
        
        # Temperature-based suggestions (Chinese)
        if temp_max > 30:
            suggestions.append("<li>高温天气请避免剧烈运动，多喝水并寻找阴凉处。</li>")
        elif temp_min < 5:
            suggestions.append("<li>低温天气请穿着保暖衣物，特别是保护头部、手部和脚部。</li>")
        
        # Precipitation-based suggestions (Chinese)
        if max_precip > 50:
            suggestions.append("<li>有较高降水可能，外出请携带雨具。</li>")
        
    else:
        # English suggestions
        if 'clear' in weather_type or weather_type == 'sun':
            suggestions.extend([
                "<li>Perfect weather for outdoor activities like hiking, picnics, or walks in the park.</li>",
                "<li>Remember to apply sunscreen and stay hydrated when out in the sun.</li>",
                "<li>Great day for outdoor photography!</li>"
            ])
        elif 'cloud' in weather_type:
            suggestions.extend([
                "<li>Cloudy weather is good for light outdoor activities like walking, jogging, or cycling.</li>",
                "<li>Good time to visit museums, art galleries, or shopping centers.</li>",
                "<li>Cloudy days offer great lighting for photography without harsh shadows.</li>"
            ])
        elif 'rain' in weather_type:
            suggestions.extend([
                "<li>Rainy weather is perfect for indoor activities - visit museums, cinemas, or cafes.</li>",
                "<li>If you need to go out, carry an umbrella or wear a waterproof jacket.</li>",
                "<li>Great time for reading or movie watching at home.</li>"
            ])
        elif 'snow' in weather_type:
            suggestions.extend([
                "<li>Snow weather is great for winter sports like skiing, sledding, or building snowmen.</li>",
                "<li>Wear warm layers when going outside and be cautious of slippery surfaces.</li>",
                "<li>Perfect time for warm drinks and cozy activities at home.</li>"
            ])
        elif 'thunder' in weather_type or 'storm' in weather_type:
            suggestions.extend([
                "<li>During thunderstorms, avoid outdoor activities and stay inside a safe building.</li>",
                "<li>Ensure electronic devices are charged in case of power outages.</li>",
                "<li>Great time for indoor reading or entertainment.</li>"
            ])
        elif 'fog' in weather_type or 'mist' in weather_type:
            suggestions.extend([
                "<li>Drive slowly with lights on during foggy conditions and maintain safe distances.</li>",
                "<li>Better for close-to-home activities, avoid long-distance travel if possible.</li>",
                "<li>Fog creates unique atmospheres for photographers to capture.</li>"
            ])
        else:
            suggestions.extend([
                "<li>Adjust your activities according to the current weather conditions.</li>",
                "<li>Check the latest forecast before heading out.</li>",
                "<li>Be prepared with appropriate clothing and gear for the day's weather.</li>"
            ])
        
        # Temperature-based suggestions (English)
        if temp_max > 30:
            suggestions.append("<li>Avoid strenuous activities in high temperatures, stay hydrated, and seek shade.</li>")
        elif temp_min < 5:
            suggestions.append("<li>Dress warmly in cold temperatures, especially protecting your head, hands, and feet.</li>")
        
        # Precipitation-based suggestions (English)
        if max_precip > 50:
            suggestions.append("<li>High chance of precipitation, bring rain gear when going out.</li>")
    
    # Randomly select three suggestions if we have more than three
    import random
    if len(suggestions) > 3:
        selected_suggestions = random.sample(suggestions, 3)
    else:
        selected_suggestions = suggestions
    
    # Create a dictionary with the activity suggestions
    activity_suggestions = {}
    for i, suggestion in enumerate(selected_suggestions, 1):
        activity_suggestions[f'activity_suggestion_{i}'] = suggestion
    
    # Fill in any missing suggestions up to 3
    for i in range(len(selected_suggestions) + 1, 4):
        if language.startswith('zh'):
            activity_suggestions[f'activity_suggestion_{i}'] = "<li>请根据天气状况做好相应准备。</li>"
        else:
            activity_suggestions[f'activity_suggestion_{i}'] = "<li>Be prepared according to weather conditions.</li>"
    
    return activity_suggestions

def get_eludecia_response(config, weather_info, character_prompt=None, language=None, timezone=None):
    """
    Use DeepSeek API to generate a response from Eludecia about the weather.
    
    Args:
        config: Application configuration
        weather_info: Weather information dictionary
        character_prompt: Custom character prompt to use instead of default
        language: Preferred language for the response
        timezone: Preferred timezone for time references
    """
    # Get DeepSeek API key from configuration
    deepseek_config = config.get('api', {}).get('deepseek', {})
    api_key = deepseek_config.get('apiKey')
    base_url = deepseek_config.get('endpoint')
    
    # Extract weather type for potential error messages
    weather_type = weather_info.get('weather_type', '').split(':')[0].strip() if weather_info else 'current'
    
    # Use provided parameters or fall back to defaults from config
    if language is None:
        language = config.get('preferences', {}).get('servicePreference', {}).get('language', 'en')
    if timezone is None:
        timezone = config.get('preferences', {}).get('servicePreference', {}).get('timezone', 'UTC')
    
    # Default character prompt if none provided
    if character_prompt is None:
        character_prompt = "You are the succubus paladin Eludecia. Respond in a seductive yet protective character style. Be flirty but maintain a hint of nobility from your paladin side."
    
    if not api_key or not base_url:
        return "DeepSeek API configuration missing. Unable to generate Eludecia's response."
    
    try:
        # Create OpenAI client with DeepSeek configuration
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        # Create prompt for the API, including language and timezone preferences
        prompt = f"""
        {character_prompt}
        Respond to the following weather information. The response should be in the format of a letter 
        and should cover all the useful information in the weather information. 
        Keep your response under 400 words. Also remember to give some suggestions based on the weather condition.
        
        Weather Information:{weather_info}
        Language: {language}
        Timezone: {timezone}
        
        IMPORTANT: Remember to response in the way the character will do, including mouth addiction, ways of talking .etc. Remember not to use markdown format, just use the plain text as response. If the user's language is not English, respond in that language.
        For example, if language is 'fr', respond in French; if 'de', respond in German; etc.
        Make sure your response reflects local time considerations based on the timezone.
        """
        
        # Make API request
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": character_prompt},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        
        # Extract and return the generated text
        return response.choices[0].message.content
    except Exception as e:
        print(f"Failed to get response from DeepSeek API: {e}")
        # Use weather_type extracted at the beginning of the function
        return f"Sorry, I'm unable to provide a personalized weather description for {weather_type.lower()} weather at the moment."

def construct_email(config, weather_info, suggestion_path, recipient=None):
    """
    Construct the email body with weather information.
    
    Args:
        config: Application configuration
        weather_info: Weather information dictionary
        suggestion_path: Path to suggestion.json
        recipient: Optional recipient information dictionary (email, location, characterPrompt, etc.)
    """  
    with open(suggestion_path, 'r', encoding='utf-8') as suggestion_file:
        suggestion_dict = json.load(suggestion_file)
    
    # Get weather condition from weather info
    weather_type = weather_info['weather_type'].split(':')[0].strip()
    if weather_type not in suggestion_dict:
        suggestion = "Weather condition not recognized. Stay safe!"
    else:
        # Randomly select one suggestion from the list for the current weather type
        suggestion = random.choice(suggestion_dict.get(weather_type, ["Have a great day!"]))
    
    # Get language preference (from recipient or global settings)
    language = config.get('preferences', {}).get('servicePreference', {}).get('language', 'en')
    timezone = config.get('preferences', {}).get('servicePreference', {}).get('timezone', 'UTC')
    character_prompt = None
    
    # If recipient is provided, use their specific settings
    if recipient:
        language = recipient.get('language', language)
        timezone = recipient.get('timezone', timezone)
        character_prompt = recipient.get('characterPrompt')
        
    # For Chinese language, use Chinese suggestions if available
    if (language == 'zh' or language == 'zh-cn') and weather_type in suggestion_dict:
        # Check if there are Chinese suggestions with "chinese_" prefix
        chinese_key = f"chinese_{weather_type}"
        if chinese_key in suggestion_dict:
            suggestion = random.choice(suggestion_dict.get(chinese_key, ["祝您有美好的一天！"]))

    # Get personalized response from Eludecia via DeepSeek API
    eludecia_response = get_eludecia_response(config, weather_info, character_prompt, language, timezone)

    # Generate activity suggestions based on weather
    activity_suggestions = generate_activity_suggestions(weather_info, language)

    # Construct the email body
    email_body = f"""
    {eludecia_response}
    """

    # Obtain sender email address from configuration
    sender_email = config.get('api', {}).get('email', {}).get('senderEmail')
    if sender_email is None:
        raise ValueError("Sender email not found in configuration.json")

    sender_name = config.get('api', {}).get('email', {}).get('senderName')
    if sender_name is None:
        raise ValueError("Sender name not found in configuration.json")
    
    # Use recipient's email or fall back to config
    to_emails = [recipient.get('email')] if recipient and 'email' in recipient else config.get('api', {}).get('email', {}).get('toEmails')
    
    if not to_emails:
        raise ValueError("Recipient email not found")

    # Create a subject line with weather information
    subject = f"{weather_info['current_time'].split()[0] if 'current_time' in weather_info else ''} | Weather for {weather_info.get('location', '')} | {suggestion}"
    
    # Create HTML version of the email based on language preference
    current_date = weather_info.get('current_time', '').split()[0] if 'current_time' in weather_info else datetime.now().strftime('%Y-%m-%d')
    current_year = datetime.now().year
    
    # Return the email components
    return {
        'sender_email': sender_email,
        'sender_name': sender_name,
        'to_emails': to_emails,
        'subject': subject,
        'body': email_body,
        'html_body': None,  # Not used in template-based email
        'weather_info': weather_info,
        'suggestion': suggestion,
        'eludecia_response': eludecia_response,
        'character_prompt': character_prompt,
        'activity_suggestions': activity_suggestions
    }

def send_email(config, mail_content):
    """Send an email using Tencent Cloud Email Service with template."""
    # Import Tencent Cloud modules
    from tencentcloud.common import credential
    from tencentcloud.common.profile.client_profile import ClientProfile
    from tencentcloud.common.profile.http_profile import HttpProfile
    from tencentcloud.ses.v20201002 import ses_client, models
    import json
    
    # Accessing email configuration
    email_config = config.get('api', {}).get('email')
    if email_config is None:
        raise ValueError("Email configuration not found in configuration.json")
    
    # Get Tencent Cloud configuration
    secret_id = email_config.get('secretId')
    secret_key = email_config.get('secretKey')
    region = email_config.get('region', 'ap-guangzhou')  # Default to Guangzhou region if not specified
    
    if not secret_id or not secret_key:
        raise ValueError("Tencent Cloud API credentials (secretId and secretKey) are required")
    
    sender_email = email_config.get('senderEmail')
    sender_name = email_config.get('senderName', '')
    to_emails = mail_content['to_emails']
    
    try:
        # Initialize Tencent Cloud credentials
        cred = credential.Credential(secret_id, secret_key)
        
        # Configure HTTP settings
        httpProfile = HttpProfile()
        httpProfile.endpoint = "ses.tencentcloudapi.com"
        
        # Configure client profile
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        
        # Create Tencent Cloud Email Service client
        client = ses_client.SesClient(cred, region, clientProfile)
        
        # Prepare email request
        req = models.SendEmailRequest()
        
        # Set destination addresses
        req.Destination = to_emails
        
        # Set email subject - This is required even with templates
        req.Subject = mail_content['subject']
        
        # Set from address
        req.FromEmailAddress = f"{sender_name} <{sender_email}>"
        
        # Get current weather info and other data
        weather_info = mail_content.get('weather_info', {})
        current_date = weather_info.get('current_time', '').split()[0] if 'current_time' in weather_info else ''
        current_year = datetime.now().year
        eludecia_response = mail_content.get('eludecia_response', '')
        suggestion = mail_content.get('suggestion', '')
        
        # Extract weather type for conditional content
        weather_type = weather_info.get('weather_type', '')
        weather_type_simple = weather_type.split(':')[0].strip() if ':' in weather_type else weather_type
        
        # Prepare conditional content for road, transit and traffic conditions
        is_clear_weather = '晴' in weather_type or 'Clear' in weather_type
        is_rainy_weather = '雨' in weather_type or '雷' in weather_type or 'Rain' in weather_type or 'Thunder' in weather_type
        
        weather_road_condition = '良好' if is_clear_weather else '可能受影响，请谨慎驾驶'
        weather_transit_condition = '可能有所延误' if is_rainy_weather else '按时运行'
        weather_traffic_condition = '流畅' if is_clear_weather else '可能拥堵，请预留充足时间'
        
        # Extract character name from prompt or use default
        character_prompt = mail_content.get('character_prompt', '')
        if character_prompt:
            # Try to extract character name from the prompt
            import re
            name_match = re.search(r"You are (?:the |a |an )?([A-Za-z\s]+)", character_prompt, re.IGNORECASE)
            character_name = name_match.group(1).strip() if name_match else "Weather Assistant"
        else:
            character_name = "你的天气助手"  # Default character name
        
        # Get activity suggestions
        activity_suggestions = mail_content.get('activity_suggestions', {})
        activity_suggestion_1 = activity_suggestions.get('activity_suggestion_1', '<li>根据今日天气状况安排活动。</li>')
        activity_suggestion_2 = activity_suggestions.get('activity_suggestion_2', '<li>请关注实时天气变化。</li>')
        activity_suggestion_3 = activity_suggestions.get('activity_suggestion_3', '<li>做好相应的准备工作。</li>')
        
        # Data source and update time
        data_source = "OpenWeatherMap API"
        weather_update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Create template data matching EXACTLY the variable names used in the template
        template_data = {
            # Location and date information
            "weather_location": weather_info.get('location', ''),
            "current_date": current_date,
            "current_year": current_year,
            
            # Current weather data
            "weather_type": weather_info.get('weather_type', ''),
            "weather_temperature": weather_info.get('weather_temperature', ''),
            "weather_temperature_range": weather_info.get('weather_temperature_range', ''),
            "weather_humidity": weather_info.get('weather_humidity', ''),
            "weather_pressure": weather_info.get('weather_pressure', ''),
            "weather_wind": weather_info.get('weather_wind', ''),
            "weather_visibility": weather_info.get('weather_visibility', ''),
            "weather_uvi": weather_info.get('weather_uvi', 'Unknown'),
            "weather_clouds": weather_info.get('weather_clouds', 'Unknown'),
            "weather_daylight": weather_info.get('weather_daylight', ''),
            
            # Morning forecast (6:00, 8:00, 10:00)
            "morning_6_weather": weather_info.get('morning_6_weather', 'Unknown'),
            "morning_6_temp": weather_info.get('morning_6_temp', 'Unknown'),
            "morning_6_precip": weather_info.get('morning_6_precip', 'Unknown'),
            "morning_8_weather": weather_info.get('morning_8_weather', 'Unknown'),
            "morning_8_temp": weather_info.get('morning_8_temp', 'Unknown'),
            "morning_8_precip": weather_info.get('morning_8_precip', 'Unknown'),
            "morning_10_weather": weather_info.get('morning_10_weather', 'Unknown'),
            "morning_10_temp": weather_info.get('morning_10_temp', 'Unknown'),
            "morning_10_precip": weather_info.get('morning_10_precip', 'Unknown'),
            
            # Afternoon forecast (12:00, 14:00, 16:00)
            "afternoon_12_weather": weather_info.get('afternoon_12_weather', 'Unknown'),
            "afternoon_12_temp": weather_info.get('afternoon_12_temp', 'Unknown'),
            "afternoon_12_precip": weather_info.get('afternoon_12_precip', 'Unknown'),
            "afternoon_14_weather": weather_info.get('afternoon_14_weather', 'Unknown'),
            "afternoon_14_temp": weather_info.get('afternoon_14_temp', 'Unknown'),
            "afternoon_14_precip": weather_info.get('afternoon_14_precip', 'Unknown'),
            "afternoon_16_weather": weather_info.get('afternoon_16_weather', 'Unknown'),
            "afternoon_16_temp": weather_info.get('afternoon_16_temp', 'Unknown'),
            "afternoon_16_precip": weather_info.get('afternoon_16_precip', 'Unknown'),
            
            # Evening forecast (18:00, 20:00, 22:00)
            "evening_18_weather": weather_info.get('evening_18_weather', 'Unknown'),
            "evening_18_temp": weather_info.get('evening_18_temp', 'Unknown'),
            "evening_18_precip": weather_info.get('evening_18_precip', 'Unknown'),
            "evening_20_weather": weather_info.get('evening_20_weather', 'Unknown'),
            "evening_20_temp": weather_info.get('evening_20_temp', 'Unknown'),
            "evening_20_precip": weather_info.get('evening_20_precip', 'Unknown'),
            "evening_22_weather": weather_info.get('evening_22_weather', 'Unknown'),
            "evening_22_temp": weather_info.get('evening_22_temp', 'Unknown'),
            "evening_22_precip": weather_info.get('evening_22_precip', 'Unknown'),
            
            # Day summary
            "weather_main_type": weather_info.get('weather_main_type', 'Unknown'),
            "temp_min": weather_info.get('temp_min', 'Unknown'),
            "temp_max": weather_info.get('temp_max', 'Unknown'),
            "max_precip": weather_info.get('max_precip', 'Unknown'),
            "max_precip_time": weather_info.get('max_precip_time', 'Unknown'),
            
            # Activity suggestions
            "activity_suggestion_1": activity_suggestion_1,
            "activity_suggestion_2": activity_suggestion_2,
            "activity_suggestion_3": activity_suggestion_3,
            
            # Conditional content
            "weather_type_simple": weather_type_simple,
            "weather_road_condition": weather_road_condition,
            "weather_transit_condition": weather_transit_condition,
            "weather_traffic_condition": weather_traffic_condition,
            "weather_suggestion": suggestion,
            
            # Email information
            "eludecia_response": eludecia_response,
            "character_name": character_name,
            "recipient_email": to_emails[0] if to_emails else "",
            "sender_email": sender_email,
            
            # Data source information
            "data_source": data_source,
            "weather_update_time": weather_update_time
        }
        
        # Print the template data for debugging
        print("Template data being sent:")
        print(json.dumps(template_data, indent=2, ensure_ascii=False))
        
        # Set email template configuration
        template = {}
        template["TemplateID"] = 31550  # Using the specified template ID
        template["TemplateData"] = json.dumps(template_data)  # Convert data to JSON string
        req.Template = template
        
        # Send the email using Tencent Cloud API
        resp = client.SendEmail(req)
        print(f"Email sent successfully using template ID 31550! Message ID: {resp.MessageId}")
        
    except Exception as e:
        print(f"Failed to send email: {e}")
        print("Tip: Make sure your sender email is verified in Tencent Cloud")
        print("You need to follow Tencent Cloud's sender email verification process at: https://console.cloud.tencent.com/ses/sender")

def process_and_send_weather(config):
    """Main function to process weather data and send email."""
    # Check if there are specific recipients configured
    recipients = config.get('recipients', [])
    
    if not recipients:
        # No recipients configured, use the default location
        print("No specific recipients configured. Using default location.")
        weather_data = obtain_weather_data(config)
        weather_info = handle_weather_data(weather_data)
        
        # Fetch forecast data
        forecast_data = obtain_forecast_data(config)
        forecast_info = process_forecast_data(forecast_data)
        
        # Combine weather and forecast data
        complete_weather_info = {**weather_info, **forecast_info}
        
        mail_content = construct_email(config, complete_weather_info, base_dir / 'suggestion.json')
        send_email(config, mail_content)
    else:
        # Process weather data for each recipient with their specific location
        print(f"Sending weather updates to {len(recipients)} recipients with their specific locations...")
        for recipient in recipients:
            try:
                recipient_email = recipient.get('email')
                location = recipient.get('location')
                
                if not recipient_email or not location:
                    print(f"Skipping recipient with incomplete information: {recipient}")
                    continue
                
                print(f"Processing weather data for {recipient_email} at location {location.get('city')}, {location.get('country')}")
                
                # Get weather data for this recipient's location
                weather_data = obtain_weather_data(config, location)
                weather_info = handle_weather_data(weather_data)
                
                # Fetch forecast data for this recipient's location
                forecast_data = obtain_forecast_data(config, location)
                forecast_info = process_forecast_data(forecast_data)
                
                # Combine weather and forecast data
                complete_weather_info = {**weather_info, **forecast_info}
                
                # Create email with recipient-specific information
                mail_content = construct_email(config, complete_weather_info, base_dir / 'suggestion.json', recipient)
                
                # Send the email
                send_email(config, mail_content)
                print(f"Successfully sent weather update to {recipient_email}")
                
            except Exception as e:
                print(f"Error processing weather for recipient {recipient.get('email', 'unknown')}: {e}")
                continue

def get_country_iso_code(country_name):
    """
    Convert a country name to its ISO 3166-1 alpha-2 code.
    Returns the country name unchanged if no match is found.
    """
    # Try to get the country object by name
    country = pycountry.countries.get(name=country_name)
    if country:
        return country.alpha_2
        
    # Try with fuzzy matching if exact match fails
    countries = pycountry.countries.search_fuzzy(country_name)
    if countries:
        return countries[0].alpha_2
            
    # Return the original if no match found
    return country_name

def print_options():
    """Print available options for the user."""
    print("")
    print("--------------------------------------------------")
    print("Available Commands:")
    print("--------------------------------------------------")
    print("1. Get Weather Update")
    print("2. Update Default Location")
    print("3. Update Email Sender Settings")
    print("4. Update Weather API Key")
    print("5. Update Tencent Cloud API Credentials")
    print("6. Update Default Language and Timezone")
    print("7. Manage Recipients")
    print("8. Update DeepSeek API Key")
    print("9. Exit")
    print("--------------------------------------------------")
    userin=input("Enter your command[1-9]: ")

    return userin

def manage_recipients(config):
    """Manage recipient-specific settings for personalized weather updates."""
    recipients = config.get('recipients', [])
    
    while True:
        print("\n--------------------------------------------------")
        print("Recipient Management")
        print("--------------------------------------------------")
        print(f"Currently configured recipients: {len(recipients)}")
        
        # List current recipients
        for i, recipient in enumerate(recipients):
            email = recipient.get('email', 'Unknown')
            location = recipient.get('location', {})
            city = location.get('city', 'Unknown')
            country = location.get('country', 'Unknown')
            print(f"{i+1}. {email} - Location: {city}, {country}")
        
        print("\nOptions:")
        print("1. Add new recipient")
        print("2. Edit existing recipient")
        print("3. Remove recipient")
        print("4. Return to main menu")
        
        choice = input("Enter your choice [1-4]: ")
        
        if choice == '1':
            # Add new recipient
            print("\nAdd New Recipient")
            email = input("Enter recipient email address: ")
            
            # Location information
            print("\nLocation Settings:")
            city = input("Enter city: ")
            country_name = input("Enter country name: ")
            country = get_country_iso_code(country_name)
            
            # Preference settings
            print("\nPreference Settings:")
            language = input("Enter preferred language (e.g., en, fr, de, zh): ")
            
            # Show available timezones for reference
            print("\nSome common timezones:")
            common_timezones = ["America/New_York", "Europe/London", "Asia/Tokyo", 
                             "Australia/Sydney", "Europe/Berlin", "Asia/Shanghai", 
                             "America/Los_Angeles", "Asia/Dubai"]
            for tz in common_timezones:
                print(f"- {tz}")
                
            timezone = input("\nEnter timezone: ")
            
            # Try to validate timezone
            try:
                pytz.timezone(timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                print(f"Warning: '{timezone}' is not a recognized timezone. Using UTC instead.")
                timezone = "UTC"
            
            # Character prompt
            print("\nCharacter Settings:")
            print("You can customize the character that delivers weather updates.")
            print("Default is: 'You are the succubus paladin Eludecia. Respond in a seductive yet protective character style.'")
            character_prompt = input("Enter character prompt (or press Enter for default): ")
            
            if not character_prompt:
                character_prompt = "You are the succubus paladin Eludecia. Respond in a seductive yet protective character style. Be flirty but maintain a hint of nobility from your paladin side."
            
            # Create new recipient entry
            new_recipient = {
                "email": email,
                "location": {
                    "city": city,
                    "country": country
                },
                "characterPrompt": character_prompt,
                "language": language,
                "timezone": timezone
            }
            
            # Add to recipients list
            recipients.append(new_recipient)
            config['recipients'] = recipients
            update_config_file(config_path, config)
            print(f"\nRecipient {email} added successfully!")
            
        elif choice == '2':
            # Edit existing recipient
            if not recipients:
                print("No recipients to edit. Please add a recipient first.")
                continue
                
            recipient_index = input("Enter the number of the recipient to edit: ")
            try:
                index = int(recipient_index) - 1
                if index < 0 or index >= len(recipients):
                    print("Invalid recipient number.")
                    continue
                    
                recipient = recipients[index]
                print(f"\nEditing recipient: {recipient.get('email')}")
                
                # Edit email
                new_email = input(f"Email ({recipient.get('email')}): ")
                if new_email:
                    recipient['email'] = new_email
                
                # Edit location
                location = recipient.get('location', {})
                print("\nLocation Settings:")
                new_city = input(f"City ({location.get('city', 'Unknown')}): ")
                if new_city:
                    recipient.setdefault('location', {})['city'] = new_city
                    
                new_country = input(f"Country ({location.get('country', 'Unknown')}): ")
                if new_country:
                    recipient.setdefault('location', {})['country'] = get_country_iso_code(new_country)
                
                # Edit preferences
                print("\nPreference Settings:")
                new_language = input(f"Language ({recipient.get('language', 'en')}): ")
                if new_language:
                    recipient['language'] = new_language
                    
                new_timezone = input(f"Timezone ({recipient.get('timezone', 'UTC')}): ")
                if new_timezone:
                    try:
                        pytz.timezone(new_timezone)
                        recipient['timezone'] = new_timezone
                    except pytz.exceptions.UnknownTimeZoneError:
                        print(f"Warning: '{new_timezone}' is not a recognized timezone. Keeping previous value.")
                
                # Edit character prompt
                print("\nCharacter Settings:")
                current_prompt = recipient.get('characterPrompt', 
                                            "You are the succubus paladin Eludecia. Respond in a seductive yet protective character style.")
                print(f"Current character prompt: {current_prompt}")
                new_prompt = input("New character prompt (press Enter to keep current): ")
                if new_prompt:
                    recipient['characterPrompt'] = new_prompt
                
                # Update config
                recipients[index] = recipient
                config['recipients'] = recipients
                update_config_file(config_path, config)
                print(f"\nRecipient {recipient.get('email')} updated successfully!")
                
            except ValueError:
                print("Please enter a valid number.")
                
        elif choice == '3':
            # Remove recipient
            if not recipients:
                print("No recipients to remove.")
                continue
                
            recipient_index = input("Enter the number of the recipient to remove: ")
            try:
                index = int(recipient_index) - 1
                if index < 0 or index >= len(recipients):
                    print("Invalid recipient number.")
                    continue
                
                recipient = recipients[index]
                confirm = input(f"Are you sure you want to remove {recipient.get('email')}? (y/n): ")
                
                if confirm.lower() == 'y':
                    removed = recipients.pop(index)
                    config['recipients'] = recipients
                    update_config_file(config_path, config)
                    print(f"\nRecipient {removed.get('email')} removed successfully!")
            except ValueError:
                print("Please enter a valid number.")
                
        elif choice == '4':
            # Return to main menu
            break
            
        else:
            print("Invalid choice. Please try again.")

def main_menu(config):
    """Main menu for user interaction."""
    commandlist = ['1','2','3','4','5','6','7','8','9']
    print("Welcome to your weather assistant!")

    if config.get('preferences', {}).get('firstUse', True):
        print("--------------------------------------------------")
        print("This is your first time using the program. Please configure your preferences.")
        config['preferences']['firstUse'] = False
        weather_api_key = input("Enter your OpenWeatherMap API key (You can acquire the api key at: https://openweathermap.org/): ")
        sender_email = input("Enter your sender email address (must be verified in Tencent Cloud): ")
        sender_name = input("Enter the name of the assistant: ")
        
        # Tencent Cloud API credentials
        secret_id = input("Enter your Tencent Cloud API SecretId: ")
        secret_key = input("Enter your Tencent Cloud API SecretKey: ")
        region = input("Enter your preferred Tencent Cloud region (default: ap-guangzhou): ") or "ap-guangzhou"
        
        # DeepSeek API configuration
        deepseek_api_key = input("Enter your DeepSeek API key: ")
        deepseek_endpoint = input("Enter your DeepSeek API endpoint (default: https://api.deepseek.com): ") or "https://api.deepseek.com"
        
        # Default location information
        city = input("Enter your default city: ")
        country_name = input("Enter your default country name: ")
        country = get_country_iso_code(country_name)
        language = input("Enter your preferred language (e.g., en, fr, de): ")
        timezone = input("Enter your timezone (e.g., America/New_York, Europe/London): ")
        print("--------------------------------------------------")

        # Create default preference structure if not exists
        if 'preferences' not in config:
            config['preferences'] = {}
        if 'defaultLocation' not in config['preferences']:
            config['preferences']['defaultLocation'] = {}
        if 'servicePreference' not in config['preferences']:
            config['preferences']['servicePreference'] = {}

        # Set API settings
        config['api']['weather']['apiKey'] = weather_api_key
        config['api']['email']['senderEmail'] = sender_email
        config['api']['email']['senderName'] = sender_name
        config['api']['email']['secretId'] = secret_id
        config['api']['email']['secretKey'] = secret_key
        config['api']['email']['region'] = region
        
        # Set DeepSeek API configuration
        if 'deepseek' not in config['api']:
            config['api']['deepseek'] = {}
        config['api']['deepseek']['apiKey'] = deepseek_api_key
        config['api']['deepseek']['endpoint'] = deepseek_endpoint
        
        # Set default location and preferences
        config['preferences']['defaultLocation']['city'] = city
        config['preferences']['defaultLocation']['country'] = country
        config['preferences']['servicePreference']['language'] = language
        config['preferences']['servicePreference']['timezone'] = timezone
        
        # Initialize recipients list if not exists
        if 'recipients' not in config:
            config['recipients'] = []

        # Ask if user wants to add a recipient now
        add_recipient = input("Would you like to add a recipient now? (y/n): ")
        if add_recipient.lower() == 'y':
            email = input("Enter recipient email address: ")
            
            # Create recipient with same location as default
            recipient = {
                "email": email,
                "location": {
                    "city": city,
                    "country": country
                },
                "characterPrompt": "You are the succubus paladin Eludecia. Respond in a seductive yet protective character style. Be flirty but maintain a hint of nobility from your paladin side.",
                "language": language,
                "timezone": timezone
            }
            
            config['recipients'].append(recipient)
            print(f"Recipient {email} added successfully!")

        # Remove deprecated settings if they exist
        if 'toEmails' in config['api']['email']:
            config['api']['email'].pop('toEmails')
        if 'password' in config['api']['email']:
            config['api']['email'].pop('password')
        if 'smtpServer' in config['api']['email']:
            config['api']['email'].pop('smtpServer')
        if 'smtpPort' in config['api']['email']:
            config['api']['email'].pop('smtpPort')
        if 'location' in config['preferences']:
            config['preferences'].pop('location')

        update_config_file(config_path, config)
        print("---------------------------------------------------")
    
    command = print_options()
    while command != '9':
        if command not in commandlist:
            print("Invalid command. Please try again.")
        elif command == '1':
            process_and_send_weather(config)
        elif command == '2':
            print("\nUpdate Default Location")
            city = input("Enter your default city: ")
            country_name = input("Enter your default country name: ")
            country = get_country_iso_code(country_name)
            
            # Ensure defaultLocation exists
            if 'defaultLocation' not in config['preferences']:
                config['preferences']['defaultLocation'] = {}
                
            config['preferences']['defaultLocation']['city'] = city
            config['preferences']['defaultLocation']['country'] = country
            
            update_config_file(config_path, config)
        elif command == '3':
            print("\nUpdate Email Sender Settings")
            sender_email = input("Enter your sender email address (must be verified in Tencent Cloud): ")
            sender_name = input("Enter the name of the assistant: ")
            
            config['api']['email']['senderEmail'] = sender_email
            config['api']['email']['senderName'] = sender_name
            
            update_config_file(config_path, config)
        elif command == '4':
            print("\nUpdate Weather API Key")
            weather_api_key = input("Enter your OpenWeatherMap API key: ")
            config['api']['weather']['apiKey'] = weather_api_key
            
            update_config_file(config_path, config)
        elif command == '5':
            print("\nUpdate Tencent Cloud API Credentials")
            secret_id = input("Enter your Tencent Cloud API SecretId: ")
            secret_key = input("Enter your Tencent Cloud API SecretKey: ")
            region = input("Enter your preferred Tencent Cloud region (default: ap-guangzhou): ") or "ap-guangzhou"
            
            config['api']['email']['secretId'] = secret_id
            config['api']['email']['secretKey'] = secret_key
            config['api']['email']['region'] = region
            
            update_config_file(config_path, config)
        elif command == '6':
            print("\nUpdate Default Language and Timezone")
            language = input("Enter your preferred language (e.g., en, fr, de): ")
            
            # Show available timezones for reference
            print("\nSome common timezones:")
            common_timezones = ["America/New_York", "Europe/London", "Asia/Tokyo", 
                              "Australia/Sydney", "Europe/Berlin", "Asia/Shanghai", 
                              "America/Los_Angeles", "Asia/Dubai"]
            for tz in common_timezones:
                print(f"- {tz}")
                
            timezone = input("\nEnter your timezone: ")
            
            # Validate the timezone
            try:
                pytz.timezone(timezone)
                config['preferences']['servicePreference']['language'] = language
                config['preferences']['servicePreference']['timezone'] = timezone
                update_config_file(config_path, config)
            except pytz.exceptions.UnknownTimeZoneError:
                print(f"Error: '{timezone}' is not a valid timezone. Please try again.")
        elif command == '7':
            manage_recipients(config)
        elif command == '8':
            print("\nUpdate DeepSeek API Key")
            deepseek_api_key = input("Enter your DeepSeek API key: ")
            deepseek_endpoint = input("Enter your DeepSeek API endpoint: ")
            
            if 'deepseek' not in config['api']:
                config['api']['deepseek'] = {}
            
            config['api']['deepseek']['apiKey'] = deepseek_api_key
            config['api']['deepseek']['endpoint'] = deepseek_endpoint
            
            update_config_file(config_path, config)
        command = print_options()

def update_config_file(config_path, config):
    """Manipulate the configuration file."""
    with open(config_path, 'w') as config_file:
        json.dump(config, config_file, indent=4)
    print("Configuration file updated successfully.")

if __name__ == "__main__":
    # Set the directory path for later file manipulation
    base_dir = pathlib.Path(__file__).resolve().parent
    config_path = base_dir / 'configuration.json'
    with open(config_path, 'r',encoding='utf-8') as config_file:
        config = json.load(config_file)

    main_menu(config)

