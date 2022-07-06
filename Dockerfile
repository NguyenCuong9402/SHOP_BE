# syntax = docker/dockerfile:experimental
FROM python:3.7
WORKDIR /app
ADD . /app
RUN pip install -r requirements.txt
EXPOSE 5000
CMD gunicorn --workers=3 --threads=1 -b 0.0.0.0:5000 --log-level=debug server:app