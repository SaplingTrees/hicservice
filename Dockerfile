FROM python:3.11-slim

WORKDIR /app

# Install Graphviz system dependency for pydot
RUN apt-get update && apt-get install -y --no-install-recommends \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DATA_DIR="/data"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
