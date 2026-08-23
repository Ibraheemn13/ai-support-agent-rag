FROM python:3.12.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system supportmind \
    && useradd --system --gid supportmind --home-dir /srv/backend supportmind

WORKDIR /srv/backend

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY --chown=supportmind:supportmind . .
RUN mkdir -p /srv/storage/uploads \
    && chown -R supportmind:supportmind /srv/storage

USER supportmind

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
