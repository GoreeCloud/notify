# No third-party application or JavaScript dependencies.
FROM golang:1.23-alpine AS build
WORKDIR /src
COPY go.mod ./
COPY internal/ ./internal/
COPY cmd/ ./cmd/
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /notify ./cmd/notify
RUN mkdir -p /var/lib/goreecloud-notify && chown 65532:65532 /var/lib/goreecloud-notify

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /notify /notify
COPY --from=build --chown=65532:65532 /var/lib/goreecloud-notify /var/lib/goreecloud-notify
WORKDIR /var/lib/goreecloud-notify
USER 65532:65532
EXPOSE 8080
ENV NOTIFY_ADDR=0.0.0.0:8080 NOTIFY_DATA_DIR=/var/lib/goreecloud-notify
ENTRYPOINT ["/notify"]
