FROM python:3.11-slim

WORKDIR /app

RUN python -m pip install --upgrade pip
RUN python -m pip install --no-cache-dir fastapi uvicorn pymongo python-dotenv
RUN python -m pip list

COPY . .

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]