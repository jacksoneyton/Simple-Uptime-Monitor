FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create installation directory
WORKDIR /opt/Simple-Uptime-Monitor

# Copy project files
COPY . .

# Install Python dependencies
RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -e .

# Create data directory
RUN mkdir -p data

# Initialize database
RUN . venv/bin/activate && \
    python3 -m uptime_monitor.database --init /opt/Simple-Uptime-Monitor/data/uptime.db

# Copy default config (minimal working configuration)
RUN if [ ! -f config.yaml ]; then cp config.default.yaml config.yaml; fi

# Expose web dashboard port
EXPOSE 5000

# Run the application (foreground for Docker)
CMD ["venv/bin/python", "-m", "uptime_monitor.main"]
