from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages

from .models import Weather_current, City, Character, CityCharacter, Comment
from .schedulers.weather_updater import ensure_default_data

def index(request):
    # Initialize default data if needed
    ensure_default_data()
    
    # Get page number from query parameters
    page_number = request.GET.get('page', 1)
    
    # Get all active city-character pairs with proper ordering
    city_characters = CityCharacter.objects.filter(is_active=True).select_related('city', 'character').order_by('city__name', 'character__name')
    
    # Apply filters if provided
    character_filter = request.GET.get('character')
    city_filter = request.GET.get('city')
    
    if character_filter:
        city_characters = city_characters.filter(character__name=character_filter)
    
    if city_filter:
        city_characters = city_characters.filter(city__name=city_filter)
    
    # Paginate the city-character pairs
    paginator = Paginator(city_characters, settings.WEATHER_PAGINATION_PER_PAGE)
    page_obj = paginator.get_page(page_number)
    
    # Get weather data for each city-character pair
    weather_data = {}
    comments_data = {}
    
    for city_char in page_obj:
        try:
            # Get the latest weather data for this city
            weather = Weather_current.objects.filter(
                city=city_char.city.name,
                country=city_char.city.country
            ).latest('last_updated')
            
            weather_data[city_char.id] = weather
        except Weather_current.DoesNotExist:
            weather_data[city_char.id] = None
        
        # Get comments for this city-character pair
        comments = Comment.objects.filter(city_character=city_char).order_by('-created_at')
        comments_data[city_char.id] = comments[:settings.WEATHER_COMMENTS_PER_PAGE]
    
    # Get all available characters and cities for filtering
    all_characters = Character.objects.all()
    all_cities = City.objects.filter(citycharacter__is_active=True).distinct()
    
    # Prepare context
    context = {
        'page_obj': page_obj,
        'weather_data': weather_data,
        'comments_data': comments_data,
        'all_characters': all_characters,
        'all_cities': all_cities,
        'selected_character': character_filter,
        'selected_city': city_filter,
    }
    
    return render(request, 'weather/index.html', context)
