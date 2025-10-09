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

ENTRYPOINT ["waitress-serve"]
CMD ["--host=0.0.0.0", "--port=8000", "app:app"]

FROM builder AS dev-envs

RUN apk add --no-cache git bash

RUN addgroup -S docker && adduser -S vscode -G docker -s /bin/bash

COPY --from=gloursdocker/docker / /
