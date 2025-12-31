# sentiment_app/apps.py
from django.apps import AppConfig

class SentimentAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sentiment_app'
    
    def ready(self):
        # Import signals when the app is ready
        try:
            import sentiment_app.signals
            print("Signals imported successfully")
        except Exception as e:
            print(f"Error importing signals: {e}")