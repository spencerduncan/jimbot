"""
Temporary Event Receiver for BalatroMCP Events
This server receives events from the BalatroMCP mod and stores them in Redis
until the full Event Bus is implemented.
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List

import redis
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="JimBot Test Event Receiver",
    description="Temporary event receiver for BalatroMCP events",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(redis_url, decode_responses=True)

# Event models
class GameEvent(BaseModel):
    event_type: str = Field(..., description="Type of game event")
    timestamp: float = Field(..., description="Unix timestamp of the event")
    game_state: Dict[str, Any] = Field(..., description="Current game state")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class EventBatch(BaseModel):
    events: List[GameEvent]
    batch_id: str = Field(..., description="Unique batch identifier")
    source: str = Field(default="BalatroMCP", description="Event source")

# Event statistics
event_stats = {
    "total_events": 0,
    "events_by_type": {},
    "last_event_time": None,
    "start_time": time.time()
}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connection
        redis_client.ping()
        return {
            "status": "healthy",
            "redis": "connected",
            "uptime": time.time() - event_stats["start_time"],
            "total_events": event_stats["total_events"]
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.post("/events")
async def receive_event(event: GameEvent):
    """Receive a single game event"""
    try:
        # Update statistics
        event_stats["total_events"] += 1
        event_stats["last_event_time"] = time.time()
        event_stats["events_by_type"][event.event_type] = \
            event_stats["events_by_type"].get(event.event_type, 0) + 1
        
        # Store event in Redis
        event_key = f"event:{event.timestamp}:{event.event_type}"
        event_data = event.model_dump_json()
        
        # Store with 24-hour expiration
        redis_client.setex(event_key, 86400, event_data)
        
        # Add to event stream
        redis_client.xadd(
            "balatro:events",
            {"data": event_data},
            maxlen=10000  # Keep last 10k events
        )
        
        # Log event
        logger.info(f"Received event: {event.event_type} at {event.timestamp}")
        
        return {
            "status": "success",
            "event_id": event_key,
            "timestamp": event.timestamp
        }
        
    except Exception as e:
        logger.error(f"Failed to process event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/events/batch")
async def receive_event_batch(batch: EventBatch):
    """Receive a batch of game events"""
    try:
        processed = 0
        failed = 0
        
        for event in batch.events:
            try:
                # Process each event
                event_stats["total_events"] += 1
                event_stats["events_by_type"][event.event_type] = \
                    event_stats["events_by_type"].get(event.event_type, 0) + 1
                
                # Store in Redis
                event_key = f"event:{event.timestamp}:{event.event_type}"
                event_data = event.model_dump_json()
                redis_client.setex(event_key, 86400, event_data)
                
                processed += 1
                
            except Exception as e:
                logger.error(f"Failed to process event in batch: {e}")
                failed += 1
        
        # Store batch metadata
        batch_key = f"batch:{batch.batch_id}"
        batch_data = {
            "processed": processed,
            "failed": failed,
            "total": len(batch.events),
            "timestamp": time.time(),
            "source": batch.source
        }
        redis_client.setex(batch_key, 3600, json.dumps(batch_data))
        
        logger.info(f"Processed batch {batch.batch_id}: {processed} success, {failed} failed")
        
        return {
            "status": "success",
            "batch_id": batch.batch_id,
            "processed": processed,
            "failed": failed
        }
        
    except Exception as e:
        logger.error(f"Failed to process batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_statistics():
    """Get event processing statistics"""
    return {
        "total_events": event_stats["total_events"],
        "events_by_type": event_stats["events_by_type"],
        "last_event_time": event_stats["last_event_time"],
        "uptime": time.time() - event_stats["start_time"],
        "server_time": datetime.utcnow().isoformat()
    }

@app.get("/events/recent")
async def get_recent_events(limit: int = 100):
    """Get recent events from Redis stream"""
    try:
        # Read from stream
        events = redis_client.xrevrange("balatro:events", count=limit)
        
        # Parse events
        parsed_events = []
        for event_id, data in events:
            try:
                event_data = json.loads(data[b"data"].decode() if isinstance(data[b"data"], bytes) else data["data"])
                parsed_events.append({
                    "id": event_id,
                    "data": event_data
                })
            except Exception as e:
                logger.error(f"Failed to parse event {event_id}: {e}")
        
        return {
            "events": parsed_events,
            "count": len(parsed_events)
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/events/clear")
async def clear_events():
    """Clear all events (development only)"""
    try:
        # Clear event keys
        keys = redis_client.keys("event:*")
        if keys:
            redis_client.delete(*keys)
        
        # Clear stream
        redis_client.delete("balatro:events")
        
        # Reset stats
        event_stats["total_events"] = 0
        event_stats["events_by_type"] = {}
        event_stats["last_event_time"] = None
        
        return {"status": "success", "cleared_keys": len(keys)}
        
    except Exception as e:
        logger.error(f"Failed to clear events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Initialize the server on startup"""
    logger.info("Starting Test Event Receiver...")
    
    # Test Redis connection
    try:
        redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    logger.info("Shutting down Test Event Receiver...")
    redis_client.close()

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8080,
        reload=True if os.getenv("DEBUG") == "true" else False
    )