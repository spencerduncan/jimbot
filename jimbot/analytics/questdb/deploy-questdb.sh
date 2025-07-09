#!/bin/bash
# Deploy QuestDB for JimBot Analytics
# This script sets up QuestDB with optimal configuration for game metrics

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
COMPOSE_FILE="${SCRIPT_DIR}/../docker-compose.questdb.yml"
DATA_DIR="${QUESTDB_DATA_PATH:-${SCRIPT_DIR}/../data/questdb}"
NETWORK_NAME="jimbot-network"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
}

create_network() {
    if ! docker network inspect "${NETWORK_NAME}" &> /dev/null; then
        log_info "Creating Docker network: ${NETWORK_NAME}"
        docker network create "${NETWORK_NAME}"
    else
        log_info "Docker network ${NETWORK_NAME} already exists"
    fi
}

create_directories() {
    log_info "Creating data directories..."
    mkdir -p "${DATA_DIR}"
    
    # Ensure proper permissions
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # QuestDB runs as user 10001
        if command -v sudo &> /dev/null; then
            sudo chown -R 10001:10001 "${DATA_DIR}" 2>/dev/null || true
        else
            # Try without sudo in containerized environments
            chown -R 10001:10001 "${DATA_DIR}" 2>/dev/null || true
        fi
    fi
}

deploy_questdb() {
    log_info "Deploying QuestDB..."
    
    # Export environment variables
    export QUESTDB_DATA_PATH="${DATA_DIR}"
    export LOG_LEVEL="${LOG_LEVEL:-INFO}"
    
    # Deploy using docker-compose
    docker-compose -f "${COMPOSE_FILE}" up -d
    
    # Wait for QuestDB to be healthy
    log_info "Waiting for QuestDB to be healthy..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose -f "${COMPOSE_FILE}" exec -T questdb curl -f http://localhost:9000/exec?query=SELECT%201 &> /dev/null; then
            log_info "QuestDB is healthy!"
            break
        fi
        
        attempt=$((attempt + 1))
        if [ $attempt -eq $max_attempts ]; then
            log_error "QuestDB failed to start properly"
            docker-compose -f "${COMPOSE_FILE}" logs questdb
            exit 1
        fi
        
        sleep 2
    done
}

create_initial_tables() {
    log_info "Creating initial tables..."
    
    # Create game_metrics table
    docker-compose -f "${COMPOSE_FILE}" exec -T questdb curl -X POST \
        -H "Content-Type: text/plain" \
        --data-binary @- \
        "http://localhost:9000/exec" << 'EOF'
CREATE TABLE IF NOT EXISTS game_metrics (
    timestamp TIMESTAMP,
    session_id SYMBOL INDEX,
    ante INT,
    blind_type SYMBOL,
    chips_scored LONG,
    chips_required LONG,
    money INT,
    hands_played INT,
    discards_used INT,
    joker_count INT,
    outcome SYMBOL,
    score_ratio DOUBLE,
    event_count INT
) TIMESTAMP(timestamp) PARTITION BY DAY;
EOF

    # Create joker_synergies table
    docker-compose -f "${COMPOSE_FILE}" exec -T questdb curl -X POST \
        -H "Content-Type: text/plain" \
        --data-binary @- \
        "http://localhost:9000/exec" << 'EOF'
CREATE TABLE IF NOT EXISTS joker_synergies (
    timestamp TIMESTAMP,
    session_id SYMBOL INDEX,
    joker_combination STRING,
    synergy_score DOUBLE,
    chips_generated LONG,
    mult_generated DOUBLE,
    effectiveness DOUBLE
) TIMESTAMP(timestamp) PARTITION BY DAY;
EOF

    # Create decision_points table
    docker-compose -f "${COMPOSE_FILE}" exec -T questdb curl -X POST \
        -H "Content-Type: text/plain" \
        --data-binary @- \
        "http://localhost:9000/exec" << 'EOF'
CREATE TABLE IF NOT EXISTS decision_points (
    timestamp TIMESTAMP,
    session_id SYMBOL INDEX,
    decision_type SYMBOL INDEX,
    phase SYMBOL,
    context STRING,
    action_taken STRING,
    confidence DOUBLE,
    used_llm BOOLEAN,
    outcome_delta DOUBLE
) TIMESTAMP(timestamp) PARTITION BY DAY;
EOF

    # Create economic_flow table
    docker-compose -f "${COMPOSE_FILE}" exec -T questdb curl -X POST \
        -H "Content-Type: text/plain" \
        --data-binary @- \
        "http://localhost:9000/exec" << 'EOF'
CREATE TABLE IF NOT EXISTS economic_flow (
    timestamp TIMESTAMP,
    session_id SYMBOL INDEX,
    transaction_type SYMBOL INDEX,
    amount INT,
    balance_before INT,
    balance_after INT,
    item_purchased STRING,
    roi DOUBLE
) TIMESTAMP(timestamp) PARTITION BY DAY;
EOF

    log_info "Initial tables created successfully"
}

test_ingestion() {
    log_info "Testing data ingestion..."
    
    # Send a test metric using InfluxDB line protocol
    echo "game_metrics,session_id=test_001,blind_type=Small chips_scored=1500i,chips_required=300i,money=45i,ante=1i $(date +%s%N)" | \
        docker-compose -f "${COMPOSE_FILE}" exec -T questdb nc localhost 8812
    
    # Verify the data was inserted
    sleep 1
    local result=$(docker-compose -f "${COMPOSE_FILE}" exec -T questdb curl -s \
        "http://localhost:9000/exec?query=SELECT%20COUNT(*)%20FROM%20game_metrics")
    
    if [[ $result == *"1"* ]]; then
        log_info "Data ingestion test passed!"
    else
        log_warn "Data ingestion test failed - please check the configuration"
    fi
}

print_status() {
    log_info "QuestDB deployment completed!"
    echo
    echo "Access points:"
    echo "  - Web Console: http://localhost:9000"
    echo "  - InfluxDB Line Protocol: localhost:8812"
    echo "  - PostgreSQL Wire Protocol: localhost:9120"
    echo
    echo "Default credentials: No authentication (configure for production)"
    echo
    echo "Useful commands:"
    echo "  - View logs: docker-compose -f ${COMPOSE_FILE} logs -f questdb"
    echo "  - Stop QuestDB: docker-compose -f ${COMPOSE_FILE} down"
    echo "  - Remove data: docker-compose -f ${COMPOSE_FILE} down -v"
}

# Main execution
main() {
    log_info "Starting QuestDB deployment for JimBot"
    
    check_docker
    create_network
    create_directories
    deploy_questdb
    create_initial_tables
    test_ingestion
    print_status
}

# Run main function
main "$@"