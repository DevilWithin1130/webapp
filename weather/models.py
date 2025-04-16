from django.db import models

class Character(models.Model):
    """Weather reporter character model"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    avatar_color = models.CharField(max_length=20, default="#ff6b6b")  # For character avatar background color
    
    def __str__(self):
        return self.name

class City(models.Model):
    """City model for weather data"""
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    characters = models.ManyToManyField(Character, through='CityCharacter')
    
    def __str__(self):
        return f"{self.name}, {self.country}"
    
    class Meta:
        verbose_name_plural = "Cities"

class Weather_current(models.Model):
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    temperature = models.FloatField(null=True, blank=True)
    feels_like = models.FloatField(null=True, blank=True)
    humidity = models.IntegerField(null=True, blank=True)
    pressure = models.IntegerField(null=True, blank=True)
    wind_speed = models.FloatField(null=True, blank=True)
    wind_direction = models.IntegerField(null=True, blank=True)
    description = models.CharField(max_length=200, null=True, blank=True)
    icon = models.CharField(max_length=20, null=True, blank=True)
    clouds = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    character_name = models.CharField(max_length=100, null=True, blank=True)
    character_letter = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.city}, {self.country} ({self.last_updated.strftime('%Y-%m-%d %H:%M')})"

class CityCharacter(models.Model):
    """Through model for City-Character relationship with weather letters"""
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    character = models.ForeignKey(Character, on_delete=models.CASCADE)
    weather_letter = models.TextField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('city', 'character')
    
    def __str__(self):
        return f"{self.character.name} reporting from {self.city.name}"

class Comment(models.Model):
    """User comments on city weather"""
    city_character = models.ForeignKey(CityCharacter, on_delete=models.CASCADE, related_name='comments')
    name = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Comment by {self.name} on {self.city_character}"
