from django.contrib import admin
from .models import Weather_current, Character, City, CityCharacter, Comment

@admin.register(Weather_current)
class WeatherAdmin(admin.ModelAdmin):
    list_display = ('city', 'country', 'temperature', 'description', 'last_updated')
    search_fields = ('city', 'country')
    list_filter = ('country',)
    readonly_fields = ('timestamp', 'last_updated')

@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'country')
    search_fields = ('name', 'country')
    list_filter = ('country',)
    # Removing filter_horizontal because we're using a custom through model

class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0

@admin.register(CityCharacter)
class CityCharacterAdmin(admin.ModelAdmin):
    list_display = ('city', 'character', 'last_updated', 'is_active')
    list_filter = ('character', 'is_active')
    search_fields = ('city__name', 'character__name')
    inlines = [CommentInline]

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('name', 'city_character', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'content')