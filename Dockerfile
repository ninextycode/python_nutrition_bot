# Use an official Python image as a base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Copy the project folder into the container
COPY . /app

# Install dependencies
RUN apt-get update && \
    apt-get install -y pkg-config python3-dev default-libmysqlclient-dev build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Set the entry point for the container
CMD ["python3", "main.py"]
