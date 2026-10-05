FROM golang:1.27.1-alpine AS build
WORKDIR /build
COPY backend/go.mod backend/go.sum ./
RUN go mod download
COPY backend/ ./
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /little-steps .

FROM alpine:3.23
RUN apk add --no-cache ca-certificates tzdata && addgroup -S app && adduser -S -G app app
WORKDIR /app
COPY --from=build /little-steps ./little-steps
COPY web/ ./web/
USER app
ENV LISTEN_ADDR=0.0.0.0:8090 WEB_DIR=/app/web
EXPOSE 8090
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD wget -q -O /dev/null http://127.0.0.1:8090/api/health || exit 1
ENTRYPOINT ["/app/little-steps"]
