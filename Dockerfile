FROM --platform=$BUILDPLATFORM python:3.10-alpine AS builder

WORKDIR /src

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r requirements.txt

COPY . .

ENTRYPOINT ["waitress-serve"]
CMD ["--host=0.0.0.0", "--port=8000", "src.app:app"]

FROM builder AS dev-envs

RUN <<EOF
apk update
apk add git
EOF

RUN <<EOF
addgroup -S docker
adduser -S --shell /bin/bash --ingroup docker vscode
EOF

COPY --from=gloursdocker/docker / /
