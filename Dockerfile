FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -e .

# Copy default configuration files
RUN cp config.default.yaml config.yaml && \
    touch .env

# Expose web dashboard port
EXPOSE 5000

# Create startup script
RUN echo '#!/bin/bash\n\
cd /app\n\
\n\
# Use data from mounted volume if it exists, otherwise use local\n\
if [ -d "/app/data" ]; then\n\
    DATA_DIR="/app/data"\n\
else\n\
    DATA_DIR="/app/local-data"\n\
    mkdir -p "$DATA_DIR"\n\
fi\n\
\n\
# Initialize database if it does not exist\n\
if [ ! -f "$DATA_DIR/uptime.db" ]; then\n\
    . venv/bin/activate\n\
    python3 -m uptime_monitor.database --init "$DATA_DIR/uptime.db"\n\
fi\n\
\n\
# Update config to use the correct database path\n\
sed -i "s|database:.*|database: \"$DATA_DIR/uptime.db\"|" config.yaml\n\
\n\
# Start the application\n\
. venv/bin/activate\n\
exec python -m uptime_monitor.main\n\
' > /app/start.sh && chmod +x /app/start.sh

# Run the application
CMD ["/app/start.sh"]
