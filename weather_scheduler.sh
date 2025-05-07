#!/bin/bash

# weather_scheduler.sh
# Script to run the weather notification service daily and log results
# For use on Linux servers

# Set variables
SERVICE_DIR="/path/to/weather-notification-service" 
LOG_DIR="$SERVICE_DIR/logs"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="$LOG_DIR/weather_service_$TIMESTAMP.log"
ERROR_LOG="$LOG_DIR/weather_service_errors_$TIMESTAMP.log"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Log script start
echo "====================================================" >> "$LOG_FILE"
echo "Weather Notification Service Run - $(date)" >> "$LOG_FILE"
echo "====================================================" >> "$LOG_FILE"

# Activate virtual environment if using one
# Uncomment and modify the following line if you're using a virtual environment
# source /path/to/venv/bin/activate

# Change to the service directory
cd "$SERVICE_DIR" || {
    echo "Error: Could not change to directory $SERVICE_DIR" | tee -a "$ERROR_LOG"
    exit 1
}

# Run the weather service with automatic input for option 1 (Get Weather Update)
# Capture both standard output and error
{
    echo "1" | python3 main.py 
    echo "8" | python3 main.py  # Exit after running
} >> "$LOG_FILE" 2>> "$ERROR_LOG"

# Check if there were any errors
if [ -s "$ERROR_LOG" ]; then
    echo "Completed with errors. See $ERROR_LOG for details." >> "$LOG_FILE"
    # Optional: Send email notification about errors
    # mail -s "Weather Service Error" your@email.com < "$ERROR_LOG"
else
    echo "Completed successfully with no errors." >> "$LOG_FILE"
fi

echo "Weather service run completed at $(date)" >> "$LOG_FILE"

# Remove empty error log if no errors occurred
if [ ! -s "$ERROR_LOG" ]; then
    rm "$ERROR_LOG"
fi

# Deactivate virtual environment if using one
# Uncomment if you activated a virtual environment above
# deactivate

exit 0