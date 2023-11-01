FROM python:3.10

RUN mkdir /fastapi_server

COPY requirements.txt /fastapi_server/requirements.txt

WORKDIR /fastapi_server

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD gunicorn main:app --access-logfile='-' --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000