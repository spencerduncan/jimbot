# Build stage
FROM rust:1.75-alpine AS builder

# Install build dependencies
RUN apk add --no-cache musl-dev protobuf-dev

WORKDIR /app

# Copy manifests
COPY Cargo.toml Cargo.lock ./

# Copy source code
COPY src ./src
COPY build.rs ./

# Copy proto files from jimbot
COPY ../../jimbot/proto /jimbot/proto

# Build the application
RUN cargo build --release

# Runtime stage
FROM alpine:latest

# Install runtime dependencies
RUN apk add --no-cache ca-certificates

# Create non-root user
RUN addgroup -g 1000 eventbus && \
    adduser -D -u 1000 -G eventbus eventbus

WORKDIR /app

# Copy the binary from builder
COPY --from=builder /app/target/release/event-bus-rust /app/event-bus

# Change ownership
RUN chown -R eventbus:eventbus /app

USER eventbus

# Expose ports
EXPOSE 8080 50051

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# Run the binary
CMD ["./event-bus"]