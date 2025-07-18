FROM python:3.10-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync

# Copy the rest of the application
COPY . .

# Run the application
CMD ["bash", "-c", "PYTHONPATH=$(pwd) uv run python byteskript_agent/pipeline.py"]
