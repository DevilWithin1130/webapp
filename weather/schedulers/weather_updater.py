import logging
import requests
import json
import random
from datetime import datetime
from django.conf import settings
from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError
from apscheduler.schedulers.background import BackgroundScheduler

# Try to import OpenAI library, use requests as fallback if not available
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("OpenAI library is available and will be used for API requests")
except ImportError:
    OPENAI_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("OpenAI library not found, using requests library as fallback")

# Import DjangoJobStore and DjangoJobExecution conditionally to prevent errors
try:
    from django_apscheduler.jobstores import DjangoJobStore
    from django_apscheduler.models import DjangoJobExecution
    django_apscheduler_available = True
except (OperationalError, ProgrammingError):
    django_apscheduler_available = False

from weather.models import Weather_current, City, Character, CityCharacter

logger = logging.getLogger(__name__)

def ensure_default_data():
    """Ensure default cities and characters exist in the database"""
    # Create default characters
    eludecia_character = Character.objects.get_or_create(
        name="Eludecia the Succubus Paladin",
        defaults={
            'description': "A reformed succubus who has pledged herself to a holy order, constantly balancing between her demonic nature and righteous path. She speaks with both seductive charm and noble virtue when discussing the weather.",
            'avatar_color': '#800080'
        }
    )
    
    # Create default cities
    for city_data in settings.DEFAULT_CITIES:
        City.objects.get_or_create(
            name=city_data['name'],
            country=city_data['country']
        )
    
    # Get our new default character
    default_char = Character.objects.get(name="Eludecia the Succubus Paladin")
    
    # For each city, create a relation with Eludecia if one doesn't already exist
    cities = City.objects.all()
    for city in cities:
        CityCharacter.objects.get_or_create(
            city=city,
            character=default_char,
            defaults={'is_active': True}
        )

def fetch_weather_data(city=None, country=None):
    """
    Fetch weather data from OpenWeather API
    """
    city = city or settings.DEFAULT_WEATHER_CITY
    country = country or settings.DEFAULT_WEATHER_COUNTRY

    params = {
        'q': f"{city},{country}",
        'appid': settings.OPENWEATHER_API_KEY,
        'units': 'metric'  # Use metric units for temperature in Celsius
    }

    try:
        response = requests.get(settings.OPENWEATHER_API_URL, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching weather data: {e}")
        return None

def clean_text(text):
    """
    Clean text from markdown formatting and remove excessive whitespace
    """
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Remove markdown formatting (basic markdown elements)
    # - Remove bold (**text**)
    text = text.replace('**', '')
    # - Remove italic (*text*)
    text = text.replace('*', '')
    # - Replace headers (# text) with plain text
    lines = []
    for line in text.split('\n'):
        line = line.strip()  # Strip whitespace from each line
        if line.startswith('# '):
            lines.append(line[2:])
        elif line.startswith('## '):
            lines.append(line[3:])
        elif line.startswith('### '):
            lines.append(line[4:])
        else:
            lines.append(line)
    
    # Rejoin with consistent line breaks
    text = '\n'.join(lines)
    
    # Replace multiple spaces with a single space
    import re
    text = re.sub(' +', ' ', text)
    
    # Fix the specific issue with excessive leading spaces at the beginning of lines
    text = re.sub(r'\n\s+', '\n', text)
    
    # Clean the first line if it has leading spaces too
    text = text.lstrip()
    
    # Process each line to ensure no leading spaces
    lines = text.split('\n')
    cleaned_lines = [line.lstrip() for line in lines]
    text = '\n'.join(cleaned_lines)
    
    # Remove any markdown backtick code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    return text

def generate_weather_letter(weather_data, character=None):
    """
    Generate a weather letter using LLM API (Deepseek via OpenAI library)
    """
    # Use default character if none is provided
    character_name = getattr(character, 'name', "Eludecia the Succubus Paladin") if character else "Eludecia the Succubus Paladin"
    
    # Get character description
    character_description = getattr(character, 'description', '') if character else ''
    
    if not character_description:
        character_description = "A reformed succubus who has pledged herself to a holy order, constantly balancing between her demonic nature and righteous path. She speaks with both seductive charm and noble virtue when discussing the weather."
    
    # Format weather data for the prompt
    city = weather_data.get('name', 'Unknown City')
    country_code = weather_data.get('sys', {}).get('country', 'Unknown Country')
    temp = weather_data.get('main', {}).get('temp', 0)
    feels_like = weather_data.get('main', {}).get('feels_like', 0)
    humidity = weather_data.get('main', {}).get('humidity', 0)
    pressure = weather_data.get('main', {}).get('pressure', 0)
    wind_speed = weather_data.get('wind', {}).get('speed', 0)
    wind_direction = weather_data.get('wind', {}).get('deg', 0)
    description = weather_data.get('weather', [{}])[0].get('description', 'unknown weather')
    clouds = weather_data.get('clouds', {}).get('all', 0)
    
    # Create the prompt for the API
    system_prompt = f"You are {character_name}. {character_description}"
    
    user_prompt = f"""
    Write a short, entertaining letter (150-200 words) reporting the current weather conditions. Stay in character the entire time.
    
    IMPORTANT OUTPUT FORMATTING REQUIREMENTS:
    1. Use PLAIN TEXT ONLY - absolutely NO markdown formatting
    2. DO NOT use asterisks, hashtags, backticks or any other formatting characters
    3. DO NOT include extra spaces or indentation at the beginning of paragraphs
    4. Start directly with your greeting without ANY leading spaces
    5. Do not format text in bold or italic, just use regular text
    
    Current weather conditions:
    - Location: {city}, {country_code}
    - Temperature: {temp}°C (feels like {feels_like}°C)
    - Weather: {description}
    - Humidity: {humidity}%
    - Pressure: {pressure} hPa
    - Wind: {wind_speed} m/s, direction {wind_direction}°
    - Cloud coverage: {clouds}%
    
    Write your letter now, addressing the reader directly. Include a greeting and sign-off in your character's voice.
    """
    
    try:
        if OPENAI_AVAILABLE:
            # Configure OpenAI client to use Deepseek
            client = OpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_API_URL
            )
            
            # Call the API using the OpenAI library with Deepseek's endpoint
            response = client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            # Process the response and clean it
            letter = response.choices[0].message.content
            letter = clean_text(letter)
            return letter
            
        else:
            # Fallback to using requests library
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"
            }
            
            data = {
                "model": settings.DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            # Use DEEPSEEK_API_URL instead of DEEPSEEK_API_BASE_URL
            response = requests.post(
                f"{settings.DEEPSEEK_API_URL}/v1/chat/completions",
                headers=headers,
                data=json.dumps(data)
            )
            
            # Check for successful response
            if response.status_code == 200:
                result = response.json()
                letter = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                letter = clean_text(letter)
                return letter
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return f"Weather letter unavailable. Error: {response.status_code}"
            
    except Exception as e:
        logger.error(f"Error generating weather letter: {e}")
        return f"Weather letter unavailable. Error: {str(e)}"

def update_city_weather(city_obj):
    """
    Update weather data for a specific city
    """
    logger.info(f"Updating weather data for {city_obj.name}, {city_obj.country}")
    
    # Fetch weather data from API
    weather_data = fetch_weather_data(city_obj.name, city_obj.country)
    
    if not weather_data:
        logger.error(f"Failed to fetch weather data for {city_obj.name}")
        return
    
    try:
        with transaction.atomic():
            # Create or update the weather data in the database
            weather_obj, created = Weather_current.objects.update_or_create(
                city=city_obj.name,
                country=city_obj.country,
                defaults={
                    'temperature': weather_data.get('main', {}).get('temp'),
                    'feels_like': weather_data.get('main', {}).get('feels_like'),
                    'humidity': weather_data.get('main', {}).get('humidity'),
                    'pressure': weather_data.get('main', {}).get('pressure'),
                    'wind_speed': weather_data.get('wind', {}).get('speed'),
                    'wind_direction': weather_data.get('wind', {}).get('deg'),
                    'description': weather_data.get('weather', [{}])[0].get('description'),
                    'icon': weather_data.get('weather', [{}])[0].get('icon'),
                    'clouds': weather_data.get('clouds', {}).get('all'),
                }
            )
            
            # Update weather letters for each active character for this city
            city_characters = CityCharacter.objects.filter(city=city_obj, is_active=True)
            
            for city_char in city_characters:
                # Generate letter for this character
                weather_letter = generate_weather_letter(weather_data, city_char.character)
                
                # Update the city-character relationship with the new letter
                city_char.weather_letter = weather_letter
                city_char.save(update_fields=['weather_letter', 'last_updated'])
            
            action = "Created" if created else "Updated"
            logger.info(f"{action} weather data for {weather_obj.city}, {weather_obj.country}")
            
    except Exception as e:
        logger.error(f"Error updating weather data for {city_obj.name}: {e}")

def update_weather_data():
    """
    Update weather data in the database for all active city-character pairs
    """
    logger.info("Running scheduled weather data update")
    
    # Ensure we have the default data
    ensure_default_data()
    
    # Get all cities that have at least one active character
    cities = City.objects.filter(citycharacter__is_active=True).distinct()
    
    if not cities:
        # If no active city-character pairs, use default city
        default_city, _ = City.objects.get_or_create(
            name=settings.DEFAULT_WEATHER_CITY, 
            country=settings.DEFAULT_WEATHER_COUNTRY
        )
        cities = [default_city]
    
    # Update weather for each city
    for city in cities:
        update_city_weather(city)

def delete_old_job_executions(max_age=604_800):
    """
    Delete old job executions to prevent the database from filling up
    :param max_age: The maximum age of job executions in seconds (default: 7 days)
    """
    if django_apscheduler_available:
        DjangoJobExecution.objects.delete_old_job_executions(max_age)

def start():
    """
    Start the scheduler for weather updates
    """
    scheduler = BackgroundScheduler()
    
    # Only use DjangoJobStore if django_apscheduler tables exist
    if django_apscheduler_available:
        try:
            scheduler.add_jobstore(DjangoJobStore(), "default")
            logger.info("Using DjangoJobStore for persistent jobs")
        except (OperationalError, ProgrammingError) as e:
            logger.warning(f"Could not use DjangoJobStore: {e}")
            logger.warning("Using default memory jobstore instead")
    else:
        logger.warning("DjangoJobStore not available, using memory jobstore")
    
    # Update weather data every 2 hours
    interval_hours = getattr(settings, 'WEATHER_UPDATE_INTERVAL_HOURS', 2)
    job_id = "update_weather_data"
    
    scheduler.add_job(
        update_weather_data,
        'interval',
        hours=interval_hours,
        name=job_id,
        id=job_id,
        replace_existing=True,
    )
    logger.info(f"Added job: update weather data every {interval_hours} hours")
    
    # Add job to delete old job executions only if django_apscheduler is available
    if django_apscheduler_available:
        scheduler.add_job(
            delete_old_job_executions,
            'interval',
            days=7,
            name="delete_old_job_executions",
            id="delete_old_job_executions",
            replace_existing=True,
        )
        logger.info("Added weekly job: delete old job executions")
    
    try:
        logger.info("Starting scheduler...")
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Stopping scheduler...")
        scheduler.shutdown()
        logger.info("Scheduler stopped successfully!")