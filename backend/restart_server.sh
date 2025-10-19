#!/bin/bash

echo "Restarting server to apply chatbot personalization changes..."

# Stop the current server process
echo "Stopping current server process..."
pkill -f "python run.py" || echo "No server process found"

# Wait a moment to ensure the process is fully stopped
sleep 2

# Start the server again
echo "Starting server..."
cd /home/node/Mr-White-Project/backend
python run.py &

echo "Server restart complete!"
echo "The chatbot will now address users by their username and remember dog names." 