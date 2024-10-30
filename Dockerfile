# Use an official Python runtime as a parent image
FROM ultralytics/ultralytics:latest-cpu

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends 

# Install any needed packages specified in requirements.txt
RUN bash setup.sh

# Make port 8001 available to the world outside this container
EXPOSE 8001

# CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]%
CMD ["python", "main.py"]
