# Use official Python runtime as a parent image
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8000 for the FastAPI application
EXPOSE 8000

# Run the backend application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]