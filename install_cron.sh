#!/bin/bash

# install_cron.sh
# Script to install the cron job for running the weather notification service daily at 8:00 AM

# Set variables
SERVICE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SCRIPT_PATH="$SERVICE_DIR/weather_scheduler.sh"

# Make scripts executable
chmod +x "$SCRIPT_PATH"
chmod +x "$0"

# Create temporary file for crontab
TEMP_CRON=$(mktemp)

# Export existing crontab
crontab -l > "$TEMP_CRON" 2>/dev/null || echo "# New crontab" > "$TEMP_CRON"

# Check if our cron job already exists
if grep -q "weather_scheduler.sh" "$TEMP_CRON"; then
    echo "Cron job for weather notification service already exists. Skipping."
else
    # Add our cron job to run at 8:00 AM daily
    echo "# Run weather notification service daily at 8:00 AM" >> "$TEMP_CRON"
    echo "0 8 * * * $SCRIPT_PATH" >> "$TEMP_CRON"
    
    # Install the new crontab
    crontab "$TEMP_CRON"
    echo "Successfully installed cron job to run weather notification service daily at 8:00 AM."
    echo "Cron job: 0 8 * * * $SCRIPT_PATH"
fi

# Clean up
rm "$TEMP_CRON"

echo ""
echo "Installation complete. The weather notification service will run automatically at 8:00 AM daily."
echo "Please ensure you edit $SCRIPT_PATH to set the correct paths and configuration."
echo ""

exit 0