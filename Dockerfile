FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements del servidor
COPY arey-server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del servidor
COPY arey-server/ .

RUN mkdir -p data

EXPOSE 8000

# Ejecutar el servidor con el puerto dinámico de Render ($PORT)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
