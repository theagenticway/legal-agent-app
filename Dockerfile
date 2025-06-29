# Use the official Python image
FROM python:3.11-slim

# Install ffmpeg and libsndfile-dev (libsndfile-dev is often needed for audio processing libraries)
RUN apt-get update && apt-get install -y ffmpeg libsndfile-dev && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /workspace

# Copy requirements and install dependencies
COPY ./requirements.txt /workspace/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /workspace/requirements.txt

# Copy the rest of the application code
COPY . /workspace

# Command to run the application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]