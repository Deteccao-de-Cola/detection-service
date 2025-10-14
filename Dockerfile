FROM --platform=$BUILDPLATFORM python:3.10-alpine AS builder

WORKDIR /src

COPY requirements.txt .

RUN apk update && apk add --no-cache \
    gcc \
    musl-dev \
    mariadb-connector-c-dev \
    pkgconfig \
    python3-dev \
    build-base

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

# Default to Flask development server for auto-reload
ENV FLASK_APP=app.py
ENV FLASK_ENV=development

# Use CMD instead of ENTRYPOINT for easier override
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=8000", "--reload"]

FROM builder AS dev-envs

RUN apk add --no-cache git bash

RUN addgroup -S docker && adduser -S vscode -G docker -s /bin/bash

COPY --from=gloursdocker/docker / /

FROM builder AS production

# For production, use Waitress
ENTRYPOINT ["waitress-serve"]
CMD ["--host=0.0.0.0", "--port=8000", "app:app"]