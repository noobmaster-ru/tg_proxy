FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md alembic.ini ./
COPY axiomai_proxy ./axiomai_proxy
RUN pip install --no-cache-dir .

CMD ["python", "-m", "axiomai_proxy.tgbot"]
