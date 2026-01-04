#!/bin/bash

# Restart script for mainbot.py
# Kills the current Python process running mainbot.py and starts a new one

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="mainbot.py"
PYTHON_CMD="python3.11"

# Find and kill the current Python process running mainbot.py
echo "Stopping current bot instance..."
pkill -f "python.*${SCRIPT_NAME}" || pkill -f "python3.*${SCRIPT_NAME}" || pkill -f "python3.11.*${SCRIPT_NAME}"

# Wait a moment for the process to terminate
sleep 2

# Kill more forcefully if still running
pkill -9 -f "python.*${SCRIPT_NAME}" 2>/dev/null || true

# Change to script directory
cd "$SCRIPT_DIR"

# Start the bot in the background with nohup
echo "Starting new bot instance..."
nohup ${PYTHON_CMD} ${SCRIPT_NAME} > bot.log 2>&1 &

# Get the new process ID
NEW_PID=$!

# Wait a moment to check if it started successfully
sleep 1

if ps -p $NEW_PID > /dev/null 2>&1; then
    echo "Bot restarted successfully! PID: $NEW_PID"
    echo "Logs are being written to: $SCRIPT_DIR/bot.log"
else
    echo "Warning: Bot may not have started successfully. Check bot.log for errors."
    exit 1
fi

