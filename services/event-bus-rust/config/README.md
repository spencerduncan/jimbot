# Event Bus Configuration

This directory contains configuration files for the Event Bus service.

## File Structure

- `default.yaml` - Base configuration with default values
- `dev.yaml` - Development environment overrides
- `staging.yaml` - Staging environment overrides
- `prod.yaml` - Production environment overrides
- `local.yaml` - Local overrides (gitignored)

## Environment Variable Support

Configuration values can be overridden using environment variables with the prefix `EVENT_BUS` and double underscore (`__`) as separator.

### Examples:

```bash
# Override REST API port
export EVENT_BUS__SERVER__REST__PORT=8080

# Override gRPC port
export EVENT_BUS__SERVER__GRPC__PORT=50051

# Override log level
export EVENT_BUS__LOGGING__LEVEL=debug
```

## Production Environment Variables

The following environment variables should be set in production:

### CORS Configuration
- `CORS_ALLOWED_ORIGIN_1` - First allowed CORS origin (required)
- `CORS_ALLOWED_ORIGIN_2` - Second allowed CORS origin (optional)
- `CORS_ALLOWED_ORIGIN_3` - Third allowed CORS origin (optional)

### TLS Configuration
- `TLS_CERT_PATH` - Path to TLS certificate (default: /etc/ssl/certs/server.crt)
- `TLS_KEY_PATH` - Path to TLS private key (default: /etc/ssl/private/server.key)
- `TLS_CA_PATH` - Path to CA certificate bundle (default: /etc/ssl/certs/ca-bundle.crt)
- `TLS_MUTUAL_ENABLED` - Enable mutual TLS (default: true)

### Logging
- `LOG_FILE_PATH` - Path to log file (default: /var/log/event-bus/prod.log)

## Staging Environment Variables

### CORS Configuration
- `STAGING_CORS_ORIGIN_1` - First allowed CORS origin (default: https://localhost:3001)
- `STAGING_CORS_ORIGIN_2` - Second allowed CORS origin (optional)

### TLS Configuration
- `STAGING_TLS_CERT_PATH` - Path to TLS certificate (default: /etc/ssl/certs/staging.crt)
- `STAGING_TLS_KEY_PATH` - Path to TLS private key (default: /etc/ssl/private/staging.key)
- `STAGING_TLS_CA_PATH` - Path to CA certificate bundle (optional)
- `STAGING_TLS_MUTUAL_ENABLED` - Enable mutual TLS (default: false)

### Logging
- `STAGING_LOG_PATH` - Path to log file (default: /var/log/event-bus/staging.log)

## Configuration Loading Order

1. `config/default.yaml` - Base configuration
2. `config/{environment}.yaml` - Environment-specific overrides (based on ENVIRONMENT env var)
3. `config/local.yaml` - Local overrides (if exists)
4. Environment variables with `EVENT_BUS__` prefix
5. Specific environment variables (e.g., CORS_ALLOWED_ORIGIN_1)

## Validation

All configuration values are validated on startup. The service will fail to start if:
- Required fields are missing
- Values are outside acceptable ranges
- TLS certificates don't exist (when TLS is enabled)

## Hot Reload

Configuration files are watched for changes in non-production environments. Changes will be automatically reloaded without service restart. Invalid configurations will be rejected and logged.