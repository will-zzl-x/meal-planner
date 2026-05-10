# Recipe for building the meal-planner app container.
# Used by Fly.io (or any Docker host) to package the app for deployment.
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies first so Docker can cache this layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app source.
COPY src/ ./src/
COPY scripts/ ./scripts/

# The SQLite DB lives on the persistent volume mounted at /data
# (configured in fly.toml). MEAL_PLANNER_DB points the app at it.
ENV MEAL_PLANNER_DB=/data/meal_planner.db
ENV PYTHONPATH=/app/src

# Streamlit listens on 8080 to match Fly's internal_port.
EXPOSE 8080

CMD ["streamlit", "run", "src/web/app.py", \
     "--server.port=8080", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
