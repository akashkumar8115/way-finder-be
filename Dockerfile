# # Step 1: Use the official Python image as the base
# FROM python:3.13.1-slim

# # Step 2: Install system dependencies (including libmagic)
# RUN apt-get update && apt-get install -y \
#     # libmagic1 \
#     libgl1-mesa-glx \
#     libglib2.0-0 \
#     ffmpeg \
#     libsm6 \
#     libxext6 \
#     && rm -rf /var/lib/apt/lists/*

# # Step 3: Set the working directory inside the container
# WORKDIR /app

# # Step 4: Copy the requirements file into the container
# COPY requirements.txt .

# # Step 5: Install Python dependencies
# RUN pip install --no-cache-dir -r requirements.txt

# # Step 7: Copy the rest of your application files into the container
# COPY . .

# # Step 8: Expose the port FastAPI will run on
# EXPOSE 8000

# # Step 9: Copy the .env file (if needed)
# COPY .env.local .env

# # Step 10: Run the FastAPI application using uvicorn
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]








# Step 1: Use the official Python image as the base
FROM python:3.13.1-slim

# Step 2: Install system dependencies (including libmagic)
RUN apt-get update && apt-get install -y \
    # libmagic1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Step 3: Set the working directory inside the container
WORKDIR /app

# Step 4: Copy the requirements file into the container
COPY requirements.txt .

# Step 5: Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Step 7: Copy the rest of your application files into the container
COPY . .

# Step 8: Expose the port FastAPI will run on
EXPOSE 8000

# Step 9: Copy the .env file (if needed) - MAKE THIS CONDITIONAL
COPY .env.local* ./
RUN if [ -f .env.local ]; then cp .env.local .env; else echo "No .env.local found, using environment variables directly"; fi

# Step 10: Run the FastAPI application using uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
