# Weather Notification Service

A Python-based weather notification service that emails personalized weather updates with a charming twist.

## Features

- Fetches real-time weather data from OpenWeatherMap API
- Sends customized email notifications with current weather and forecast data
- Uses Tencent Cloud Email Service for reliable email delivery
- Includes personalized weather suggestions and activity recommendations
- Supports multiple recipients with individual location preferences
- Character-based weather narratives via DeepSeek API
- Responsive HTML email design with time-specific forecasts
- Easy-to-use command-line interface for configuration
- Multi-language support (English, Chinese, and more)

## Requirements

- Python 3.6 or higher
- Internet connection
- Tencent Cloud account with Email Service enabled
- OpenWeatherMap API key
- DeepSeek API key (for character-based narratives)

## Dependencies

- `requests`: For API calls
- `pycountry`: For country code validation
- `pytz`: For timezone handling
- `tencentcloud-sdk-python`: For Tencent Cloud Email Service
- `openai`: For DeepSeek API integration
- Standard Python libraries: json, os, pathlib, random, datetime, email

## Setup

1. Clone this repository
2. Install required packages:
   ```
   pip install -r requirements.txt
   ```
3. Run the program:
   ```
   python main.py
   ```
4. On first run, you'll be prompted to enter:
   - OpenWeatherMap API key (get one at https://openweathermap.org/)
   - Tencent Cloud Email Service credentials
   - Sender email address (must be verified in Tencent Cloud)
   - Assistant name
   - Default location (city and country)
   - Preferred language and timezone
   - Recipient email address(es)

## Usage

The program offers a command-line interface with the following options:

1. Get Weather Update - Fetch current weather data and send an email
2. Update Default Location - Change your default city and country
3. Update Email Sender Settings - Modify sender email settings
4. Update Weather API Key - Change your OpenWeatherMap API key
5. Update Tencent Cloud API Credentials - Modify your Tencent Cloud credentials
6. Update Default Language and Timezone - Change language and timezone preferences
7. Manage Recipients - Add, edit, or remove recipients with personalized settings
8. Exit - Close the program

## Configuration

All settings are stored in `configuration.json` and include:

- API keys and endpoints for weather data and DeepSeek
- Tencent Cloud Email Service credentials
- Default location preferences
- Service preferences (language, timezone)
- Recipient-specific settings (email, location, character preferences)

## Weather Suggestions

The program includes weather-specific personalized messages delivered by a character (default is Eludecia, a succubus paladin). These messages are generated using the DeepSeek API and complemented with activity suggestions based on current weather conditions.

## Email Templates

The service uses HTML email templates (stored in `template.html`) to create visually appealing weather updates that include:

- Current weather conditions
- Hourly forecasts for morning, afternoon, and evening
- Daily temperature ranges and precipitation probabilities
- Character-generated weather narratives
- Activity suggestions based on weather conditions

## Security Note

Your API keys and passwords are stored locally in the configuration file. Never share this file or upload it to public repositories.

## License

This project is available for personal use.

## Automating Weather Updates

Use the included `weather_scheduler.sh` script with cron jobs to send automatic weather updates. Run `install_cron.sh` to set up daily notifications.
