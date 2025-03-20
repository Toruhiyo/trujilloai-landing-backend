FROM python:3.13-slim

# Set environment variables
ARG PROJECT_KEY
ENV PROJECT_KEY=${PROJECT_KEY}

ARG ENV
ENV ENV=${ENV}

# Create .env file with environment variables
RUN echo "PROJECT_KEY=${PROJECT_KEY}" > .env && \
    echo "ENV=${ENV}" >> .env

# Set non-interactive and disable pip cache for smaller images
ENV PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_VERSION=2.1.1 \
    PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Update pip and install Poetry
RUN pip install --upgrade pip \
    && pip install "poetry==$POETRY_VERSION"

# Copy only poetry.lock & pyproject.toml to cache them in docker layer
COPY poetry.lock pyproject.toml ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi --no-root \
    && poetry run pip install uvicorn

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Start the web server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
