FROM python:3.11-slim

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY miniapp ./miniapp

# Expose port for Mini App web server
EXPOSE 8080

# Start the bot
CMD ["python", "main.py"]
