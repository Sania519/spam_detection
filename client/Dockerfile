FROM python:3.9-slim

WORKDIR /app

# Copy requirements file
COPY client_requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r client_requirements.txt

# Copy application code
COPY client_ui.py .
COPY templates/ ./templates/

# Create uploads directory
RUN mkdir -p uploads

# Run the client UI application
CMD ["python", "client_ui.py"]