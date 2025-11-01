FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make startup script executable
RUN chmod +x /app/start-services.sh

# Expose the port the app runs on (App Runner expects 8080)
EXPOSE 8080

# Command to run all services
CMD ["/app/start-services.sh"] 