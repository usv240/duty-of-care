FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY duty_of_care duty_of_care
COPY duty_of_care_agent duty_of_care_agent
COPY scripts scripts
COPY app/web app/web
COPY guidance guidance
COPY presets presets
COPY benchmark benchmark
COPY evaluation evaluation
COPY docs/EVAL-LIVE.json docs/EVAL-LIVE.json
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser
CMD ["sh", "-c", "uvicorn duty_of_care.main:app --host 0.0.0.0 --port ${PORT}"]
