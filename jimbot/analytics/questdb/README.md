# QuestDB Deployment for JimBot Analytics

QuestDB is deployed as the primary time-series database for storing real-time game metrics and performance data in the JimBot system.

## Overview

QuestDB provides:
- High-performance time-series data ingestion
- SQL query interface for analytics
- InfluxDB line protocol compatibility
- Web console for data exploration
- Efficient storage with automatic partitioning

## Deployment

### Quick Start

```bash
# Deploy QuestDB
cd jimbot/analytics/questdb
./deploy-questdb.sh

# Verify deployment
docker ps | grep questdb
```

### Manual Deployment

```bash
# Create network if it doesn't exist
docker network create jimbot-network

# Create data directory
mkdir -p ./data/questdb

# Deploy using docker-compose
docker-compose -f ../docker-compose.questdb.yml up -d

# Check health
curl -f http://localhost:9000/exec?query=SELECT%201
```

## Configuration

### Memory Allocation

QuestDB is configured with 3GB memory limit:
- Writer memory: 2GB
- System memory: 1GB
- Query cache and buffers use available memory

### Performance Tuning

Key optimizations in `conf/server.conf`:
- WAL enabled for durability
- 100k uncommitted rows for batch efficiency
- 4MB message buffer for line protocol
- Daily partitioning for data management

### Ports

- `9000`: Web console and HTTP API
- `8812`: InfluxDB line protocol
- `9009`: HTTP REST API
- `9120`: PostgreSQL wire protocol

## Data Schema

### Core Tables

1. **game_metrics**
   - Session-level game performance data
   - Partitioned by day
   - Indexed on session_id

2. **joker_synergies**
   - Joker combination effectiveness
   - Tracks synergy scores and chip generation
   - Used for strategy optimization

3. **decision_points**
   - Individual decision tracking
   - Records confidence levels and LLM usage
   - Enables decision quality analysis

4. **economic_flow**
   - Money transactions and ROI
   - Shop purchase effectiveness
   - Economic strategy optimization

## Data Ingestion

### Using InfluxDB Line Protocol

```bash
# Send metric via line protocol
echo "game_metrics,session_id=abc123,blind_type=Boss chips_scored=50000i,money=75i $(date +%s%N)" | \
  nc localhost 8812
```

### Using HTTP API

```bash
# Insert data via HTTP
curl -X POST http://localhost:9000/exec \
  -H "Content-Type: text/plain" \
  --data-binary "INSERT INTO game_metrics VALUES(now(), 'session123', 5, 'Boss', 50000, 30000, 75, 3, 1, 5, 'win', 1.67, 42)"
```

### Using Python Client

```python
import requests
from datetime import datetime

# Insert using SQL
query = """
INSERT INTO game_metrics VALUES(
    now(), 'session123', 5, 'Boss', 50000, 30000, 
    75, 3, 1, 5, 'win', 1.67, 42
)
"""
response = requests.post('http://localhost:9000/exec', params={'query': query})
```

## Querying Data

### Web Console

Access the web console at http://localhost:9000 for:
- Interactive SQL queries
- Data visualization
- Schema exploration
- Performance monitoring

### Common Queries

```sql
-- Session performance summary
SELECT 
    session_id,
    max(ante) as max_ante,
    sum(chips_scored) as total_chips,
    count(*) as rounds_played,
    avg(score_ratio) as avg_performance
FROM game_metrics
WHERE timestamp > dateadd('h', -24, now())
GROUP BY session_id;

-- Joker synergy analysis
SELECT 
    joker_combination,
    avg(synergy_score) as avg_synergy,
    count(*) as usage_count,
    avg(effectiveness) as avg_effectiveness
FROM joker_synergies
WHERE timestamp > dateadd('d', -7, now())
GROUP BY joker_combination
ORDER BY avg_effectiveness DESC
LIMIT 20;

-- Decision quality by type
SELECT 
    decision_type,
    avg(confidence) as avg_confidence,
    count(*) as decision_count,
    sum(CASE WHEN used_llm THEN 1 ELSE 0 END) as llm_usage,
    avg(outcome_delta) as avg_impact
FROM decision_points
WHERE timestamp > dateadd('h', -1, now())
GROUP BY decision_type;
```

## Monitoring

### Health Check

```bash
# Basic health check
curl -f http://localhost:9000/health

# Detailed status
curl http://localhost:9000/status
```

### Metrics

Monitor these key metrics:
- Ingestion rate (rows/second)
- Query latency (p50, p95, p99)
- Disk usage and growth rate
- Memory utilization
- Active connections

### Logs

```bash
# View logs
docker-compose -f ../docker-compose.questdb.yml logs -f questdb

# Check for errors
docker-compose -f ../docker-compose.questdb.yml logs questdb | grep ERROR
```

## Maintenance

### Backup

```bash
# Backup data directory
tar -czf questdb-backup-$(date +%Y%m%d).tar.gz ./data/questdb

# Backup specific tables
curl "http://localhost:9000/exp?query=SELECT * FROM game_metrics" > game_metrics_backup.csv
```

### Data Retention

QuestDB automatically manages partitions:
- Daily partitions for all tables
- 90-day retention policy
- Automatic vacuum for space reclamation

### Scaling

To scale QuestDB:
1. Increase memory allocation in docker-compose
2. Adjust worker counts in server.conf
3. Consider splitting read/write workloads
4. Use multiple QuestDB instances with sharding

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   - Check uncommitted row count
   - Review partition sizes
   - Adjust writer memory limit

2. **Slow Queries**
   - Add indexes for common filters
   - Use SAMPLE BY for large datasets
   - Optimize time range filters

3. **Connection Refused**
   - Verify container is running
   - Check port bindings
   - Review firewall rules

### Debug Commands

```bash
# Container status
docker ps -a | grep questdb

# Resource usage
docker stats jimbot-questdb

# Network connectivity
docker exec jimbot-questdb ping jimbot-network

# Disk usage
docker exec jimbot-questdb df -h /var/lib/questdb
```

## Integration

### With Event Bus

QuestDB receives metrics from the Event Bus consumer:
```python
# Example consumer code
async def process_game_metric(event):
    metric = f"game_metrics,session_id={event.session_id},blind_type={event.blind_type} "
    metric += f"chips_scored={event.chips_scored}i,money={event.money}i {event.timestamp}"
    
    # Send to QuestDB
    await send_to_questdb(metric)
```

### With Analytics Dashboard

QuestDB serves as the backend for Grafana dashboards:
- Configure QuestDB as PostgreSQL datasource
- Use port 9120 for PostgreSQL wire protocol
- Enable time-series visualizations

## Security

### Production Recommendations

1. Enable authentication in server.conf
2. Use TLS for external connections
3. Restrict network access
4. Regular security updates
5. Audit log monitoring

### Access Control

```bash
# Example: Create read-only user (when auth is enabled)
CREATE USER readonly WITH PASSWORD 'secure_password';
GRANT SELECT ON ALL TABLES TO readonly;
```

## Performance Benchmarks

Expected performance with 3GB allocation:
- Ingestion: >1M rows/second
- Query latency: <10ms (p50), <30ms (p95)
- Concurrent queries: 100+
- Storage efficiency: ~10x compression

## References

- [QuestDB Documentation](https://questdb.io/docs/)
- [SQL Reference](https://questdb.io/docs/reference/sql/overview/)
- [Performance Tuning Guide](https://questdb.io/docs/operations/performance/)
- [JimBot Analytics Architecture](../README.md)