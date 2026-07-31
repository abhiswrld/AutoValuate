FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and Linux dependencies
RUN playwright install --with-deps chromium

# Copy all project files into the container
COPY . .

# Run the API
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]