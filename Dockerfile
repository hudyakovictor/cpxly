# Candidate: uv.lock must be refreshed and validated before acceptance.
FROM ghcr.io/astral-sh/uv:0.9.17@sha256:5cb6b54d2bc3fe2eb9a8483db958a0b9eebf9edff68adedb369df8e7b98711a2 AS uv
FROM docker.io/library/node:24.0.0-bookworm-slim@sha256:7b0f9cbb3f88da0e67873be5efcf38ce79ea25cfbb4986fad55a446af484e7c9 AS frontend
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci
COPY assets ./assets
COPY static ./static
COPY vite.config.ts tsconfig.json ./
RUN npm run build

FROM docker.io/library/python:3.14.0-slim-bookworm@sha256:d13fa0424035d290decef3d575cea23d1b7d5952cdf429df8f5542c71e961576 AS tooling
COPY --from=uv /uv /uvx /usr/local/bin/
WORKDIR /app
ENV UV_CACHE_DIR=/tmp/uv-cache

FROM tooling AS dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --group prod --no-install-project

FROM tooling AS development
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app && chown -R app:app /app
COPY --chown=10001:10001 . .
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10001:10001
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM tooling AS static-builder
COPY --from=dependencies /app/.venv /app/.venv
COPY . .
COPY --from=frontend /src/static /app/static
ENV PATH="/app/.venv/bin:$PATH" DJANGO_SETTINGS_MODULE=project.settings_build
RUN python manage.py collectstatic --noinput

FROM docker.io/library/python:3.14.0-slim-bookworm@sha256:d13fa0424035d290decef3d575cea23d1b7d5952cdf429df8f5542c71e961576 AS production
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app
WORKDIR /app
COPY --from=static-builder --chown=10001:10001 /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=project.settings_production
USER 10001:10001
EXPOSE 8000
CMD ["gunicorn", "project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "--access-logformat", "%(m)s %(s)s %(L)s", "--error-logfile", "-"]
