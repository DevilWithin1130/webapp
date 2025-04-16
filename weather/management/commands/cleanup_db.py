from django.core.management.base import BaseCommand
from weather.models import Character, CityCharacter, Comment, Weather_current
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean up the database by removing unwanted characters and their related data'

    def handle(self, *args, **options):
        self.stdout.write("Starting database cleanup...")
        
        try:
            # Remove any characters with "Captain" in the name
            captain_characters = Character.objects.filter(
                Q(name__icontains="Captain") | 
                Q(description__icontains="Captain")
            )
            
            if captain_characters.exists():
                # Get count of characters to be deleted
                character_count = captain_characters.count()
                
                # Get names of characters to log what's being deleted
                character_names = list(captain_characters.values_list('name', flat=True))
                
                # Find all CityCharacter relationships that include these characters
                city_characters = CityCharacter.objects.filter(character__in=captain_characters)
                city_character_count = city_characters.count()
                
                # Find all comments related to these city-character pairs
                comments = Comment.objects.filter(city_character__in=city_characters)
                comment_count = comments.count()
                
                # Delete in the correct order to respect foreign key constraints
                self.stdout.write(f"Deleting {comment_count} comments related to Captain characters...")
                comments.delete()
                
                self.stdout.write(f"Deleting {city_character_count} city-character relationships related to Captain characters...")
                city_characters.delete()
                
                self.stdout.write(f"Deleting {character_count} Captain characters: {', '.join(character_names)}...")
                captain_characters.delete()
                
                self.stdout.write(self.style.SUCCESS(f"Successfully removed all Captain characters and related data from the database"))
            else:
                self.stdout.write("No Captain characters found in the database")
                
            # Also clean up any references in the legacy Weather_current table
            weather_updates = Weather_current.objects.filter(
                Q(character_name__icontains="Captain") | 
                Q(character_letter__icontains="Captain")
            )
            
            weather_count = weather_updates.count()
            if weather_count > 0:
                self.stdout.write(f"Cleaning {weather_count} weather records with Captain references...")
                # Clear the character_name and character_letter fields
                weather_updates.update(character_name=None, character_letter=None)
                self.stdout.write(self.style.SUCCESS(f"Successfully cleaned {weather_count} weather records"))
            else:
                self.stdout.write("No weather records with Captain references found")
                
            # Additional search for any weather letters that mention Captain
            weather_with_captain_letters = Weather_current.objects.filter(
                character_letter__icontains="Captain"
            ).exclude(character_letter__isnull=True)
            
            if weather_with_captain_letters.exists():
                self.stdout.write(f"Found {weather_with_captain_letters.count()} weather letters mentioning 'Captain'")
                weather_with_captain_letters.update(character_letter=None)
                self.stdout.write(self.style.SUCCESS("Successfully cleared those weather letters"))
                
            self.stdout.write(self.style.SUCCESS("Database cleanup completed successfully"))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during cleanup: {str(e)}"))
            logger.error(f"Error during database cleanup: {str(e)}")
            raise