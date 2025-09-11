FROM python:3.13-slim-trixie

ENV POETRY_VERSION=2.1.2
ENV POETRY_HOME=/opt/poetry 
ENV POETRY_VENV=/opt/poetry-venv

RUN apt-get update && apt-get install -y libpq-dev gcc

WORKDIR /app

COPY pyproject.toml poetry.lock .env ./

RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --no-cache 

COPY ./src /app

CMD ["python", "main.py"]