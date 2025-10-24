# Start from a Python 3.10 base image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy ALL files from your project (the ".") into the WORKDIR ("/app")
COPY . .

# Set the PYTHONPATH so imports like "from src.utils.db" work
ENV PYTHONPATH="/app"

# 
# THIS IS THE FIX:
# The command must point to the correct path inside the container
#
CMD ["python", "src/pipeline/flow.py"]