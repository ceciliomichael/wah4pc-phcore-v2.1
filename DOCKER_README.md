# Docker Deployment Guide

This guide explains how to containerize and deploy the FHIR Validation Server using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+ 
- Docker Compose 2.0+

## Quick Start

### Development Environment

1. **Build and run the application:**
   ```bash
   docker-compose up --build
   ```

2. **Run in detached mode:**
   ```bash
   docker-compose up -d --build
   ```

3. **Access the application:**
   - Web Interface: http://localhost:6789 (dev) / https://wah4pc-validation.echosphere.cfd (prod)
   - API Documentation: http://localhost:6789/docs (dev) / https://wah4pc-validation.echosphere.cfd/docs (prod)
   - Health Check: http://localhost:6789/docs (dev) / https://wah4pc-validation.echosphere.cfd/docs (prod)

### Production Environment

1. **Deploy with production overrides:**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
   ```

2. **Scale the application (if needed):**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --scale fhir-validator=3
   ```

## Docker Commands

### Basic Operations

```bash
# Build the image
docker-compose build

# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f fhir-validator

# Restart a service
docker-compose restart fhir-validator

# Execute commands in running container
docker-compose exec fhir-validator bash
```

### Maintenance

```bash
# Update and rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Clean up unused resources
docker system prune -a

# Remove all containers and volumes
docker-compose down -v --remove-orphans
```

## Configuration

### Environment Variables

The application supports the following environment variables:

- `PYTHONPATH`: Python module search path (default: `/app`)
- `PORT`: Server port (default: `6789`)
- `ENVIRONMENT`: Runtime environment (`development`/`production`)
- `LOG_LEVEL`: Logging level (`debug`/`info`/`warning`/`error`)
- `SERVER_URL`: Production server URL for OpenAPI docs (default: `http://localhost:6789`)

**Note**: When `ENVIRONMENT=production` and `SERVER_URL` is set, the `/docs` endpoint will show your production URL as the primary server, with localhost as a secondary option for local testing.

### Volume Mounts

Development mode mounts the following directories:
- `./resources:/app/resources:ro` - FHIR resources and schemas
- `./static:/app/static:ro` - Static web assets
- `./templates:/app/templates:ro` - HTML templates

## Networking

The application runs on port `6789` by default. The Docker Compose setup:
- Exposes port `6789` on the host
- Creates an isolated `fhir-network` bridge network
- Includes optional nginx reverse proxy configuration

## Health Monitoring

The container includes built-in health checks:
- **Endpoint**: HTTP GET to `/docs`
- **Interval**: 30 seconds (15s in production)
- **Timeout**: 10 seconds (5s in production)
- **Retries**: 3 attempts
- **Start Period**: 40 seconds (30s in production)

Check container health:
```bash
docker-compose ps
docker inspect fhir-validation-server | grep -A 10 Health
```

## Security Considerations

### Production Security

1. **Non-root user**: Container runs as `appuser` (non-root)
2. **Resource limits**: CPU and memory limits in production
3. **Read-only mounts**: Resources mounted as read-only
4. **Network isolation**: Services run in isolated Docker network

### Recommended Production Setup

1. **Use secrets management** for sensitive configuration
2. **Enable TLS/SSL** with proper certificates
3. **Configure firewall rules** to restrict access
4. **Set up log aggregation** and monitoring
5. **Regular security updates** of base images

## Troubleshooting

### Common Issues

1. **Port already in use:**
   ```bash
   # Change port in docker-compose.yml
   ports:
     - "8080:6789"  # Use different host port
   ```

2. **Permission errors:**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   ```

3. **Container won't start:**
   ```bash
   # Check logs
   docker-compose logs fhir-validator
   
   # Debug interactively
   docker-compose run --rm fhir-validator bash
   ```

4. **Resource not found errors:**
   ```bash
   # Verify volume mounts
   docker-compose exec fhir-validator ls -la /app/resources
   ```

### Performance Tuning

For high-traffic deployments:

1. **Increase resource limits** in `docker-compose.prod.yml`
2. **Use multiple replicas** with load balancing
3. **Add Redis caching** for validation results
4. **Configure nginx** for static file serving and compression

## Monitoring and Logging

### View Application Logs
```bash
# Real-time logs
docker-compose logs -f fhir-validator

# Last 100 lines
docker-compose logs --tail=100 fhir-validator

# Logs with timestamps
docker-compose logs -t fhir-validator
```

### Container Statistics
```bash
# Resource usage
docker stats fhir-validation-server

# Detailed container info
docker inspect fhir-validation-server
```
