# Start from a Python 3.10 base image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy ALL files from your project (the ".") into the WORKDIR ("/app")
COPY . .

# Set the PYTHONPATH so imports like "from src.api.main" work
ENV PYTHONPATH="/app"

# Expose the port the API will run on
EXPOSE 8000

# Command to run the Uvicorn server
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]