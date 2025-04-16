from django.apps import AppConfig
import sys
from django.db.models.signals import post_migrate


class WeatherConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'weather'
    
    def ready(self):
        # Only start the scheduler when running the server, not during migrations
        if 'runserver' in sys.argv:
            # Start the weather update scheduler
            from weather.schedulers import weather_updater
            weather_updater.start()
            
            # Register a callback to run after migrations are complete
            # This avoids database access during app initialization
            post_migrate.connect(self._populate_initial_data, sender=self)
    
    def _populate_initial_data(self, sender, **kwargs):
        """
        Callback to populate initial weather data after app initialization
        This avoids the warning about database access during app initialization
        """
        from weather.schedulers import weather_updater
        import threading
        
        # Run the initial data update in a separate thread with a slight delay
        # to ensure it happens after app initialization is complete
        def delayed_update():
            import time
            time.sleep(2)  # Short delay to ensure app is fully loaded
            weather_updater.update_weather_data()
        
        threading.Thread(target=delayed_update).start()
