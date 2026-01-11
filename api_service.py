"""
FastAPI service for AI Headline Impact Processor
Provides REST API endpoints for news analysis with Phase 1 simplified output
"""

import asyncio
import logging
import time
from typing import List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import json

from models import (
    NewsAnalysisRequest,
    NewsAnalysisResponse,
    EntityImpact,
    HealthCheckResponse,
    BatchAnalysisRequest,
    BatchAnalysisResponse
)
from poc_implementation import POCImpactAssessor
from config_loader import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global assessor instance
assessor: Optional[POCImpactAssessor] = None

# Global set of connected WebSocket clients for broadcast
active_connections: set = set()

# Global ticker feed - stores recent headlines for polling
from collections import deque
ticker_feed = deque(maxlen=50)  # Keep last 50 headlines


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app"""
    # Startup
    global assessor
    logger.info("Initializing POCImpactAssessor...")
    assessor = POCImpactAssessor()
    logger.info("API service ready")

    yield

    # Shutdown
    logger.info("Shutting down API service")


# Create FastAPI app
app = FastAPI(
    title="AI Headline Impact Processor API",
    description="Analyze financial news headlines and assess impact on currencies with confidence levels",
    version="1.0.0-phase1",
    lifespan=lifespan
)

# Add CORS middleware for Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def convert_to_confidence_category(confidence_score: float) -> str:
    """Convert numeric confidence score to category (high/medium/low)"""
    if confidence_score >= 0.7:
        return "high"
    elif confidence_score >= 0.4:
        return "medium"
    else:
        return "low"


def convert_to_simplified_output(analysis_result, min_confidence: float = 0.3) -> NewsAnalysisResponse:
    """Convert POCImpactAssessor output to Phase 1 simplified format"""

    impacted_entities = []

    for assessment in analysis_result.entity_assessments:
        # Filter by minimum confidence
        if assessment.confidence_score < min_confidence:
            continue

        # Convert to EntityImpact format
        entity_impact = EntityImpact(
            currency=assessment.entity_id,
            confidence=convert_to_confidence_category(assessment.confidence_score),
            confidence_score=round(assessment.confidence_score, 3),
            reasoning=assessment.reasoning
        )
        impacted_entities.append(entity_impact)

    # Sort by confidence score descending
    impacted_entities.sort(key=lambda x: x.confidence_score, reverse=True)

    return NewsAnalysisResponse(
        headline=analysis_result.news_headline,
        impacted_entities=impacted_entities,
        processing_time_ms=round(analysis_result.total_processing_time_ms, 2),
        analysis_timestamp=analysis_result.analysis_timestamp,
        metadata={
            "total_entities_analyzed": analysis_result.entities_processed,
            "entities_above_threshold": len(impacted_entities),
            "overall_confidence": round(analysis_result.overall_confidence, 3)
        }
    )


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "AI Headline Impact Processor API",
        "version": "1.0.0-phase1",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    config = get_config()

    return HealthCheckResponse(
        status="healthy",
        version="1.0.0-phase1",
        environment=config.environment,
        model_provider="mock_llm" if config.model_config.use_mock_llm else "gemini_flash"
    )


@app.post("/analyze", response_model=NewsAnalysisResponse, tags=["Analysis"])
async def analyze_headline(request: NewsAnalysisRequest):
    """
    Analyze a single news headline and return impacted entities with confidence levels

    **Phase 1 Simplified Output:**
    - Returns list of impacted currencies with confidence levels (high/medium/low)
    - Includes reasoning for each impact
    - Filters entities below minimum confidence threshold
    """
    if assessor is None:
        raise HTTPException(status_code=503, detail="Analysis service not initialized")

    try:
        logger.info(f"Analyzing headline: {request.headline}")

        # Run analysis using existing POCImpactAssessor
        start_time = time.time()
        result = await assessor.analyze_news_impact(
            request.headline,
            target_entities=request.target_entities
        )

        # Convert to simplified Phase 1 format
        simplified_result = convert_to_simplified_output(result, request.min_confidence)

        logger.info(
            f"Analysis completed in {simplified_result.processing_time_ms:.1f}ms. "
            f"Found {len(simplified_result.impacted_entities)} entities above threshold."
        )

        return simplified_result

    except Exception as e:
        logger.error(f"Error analyzing headline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/analyze/batch", response_model=BatchAnalysisResponse, tags=["Analysis"])
async def analyze_batch(request: BatchAnalysisRequest):
    """
    Analyze multiple headlines in batch

    Processes up to 100 headlines in parallel with controlled concurrency
    """
    if assessor is None:
        raise HTTPException(status_code=503, detail="Analysis service not initialized")

    try:
        logger.info(f"Starting batch analysis of {len(request.headlines)} headlines")

        batch_start = time.time()
        results = []

        # Process all headlines
        for headline in request.headlines:
            result = await assessor.analyze_news_impact(headline)
            simplified = convert_to_simplified_output(result, request.min_confidence)
            results.append(simplified)

        total_time = (time.time() - batch_start) * 1000

        logger.info(f"Batch analysis completed in {total_time:.1f}ms")

        return BatchAnalysisResponse(
            results=results,
            total_processed=len(results),
            total_processing_time_ms=round(total_time, 2)
        )

    except Exception as e:
        logger.error(f"Error in batch analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")


@app.get("/stats", tags=["Monitoring"])
async def get_stats():
    """Get performance statistics"""
    if assessor is None:
        raise HTTPException(status_code=503, detail="Analysis service not initialized")

    stats = assessor.get_performance_stats()
    return stats


@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time headline streaming

    Client sends: {"headline": "...", "min_confidence": 0.3, "llm_provider": "mock"}
    Server responds: NewsAnalysisResponse in JSON format
    """
    await websocket.accept()
    logger.info("WebSocket client connected")

    try:
        while True:
            # Receive headline from client
            data = await websocket.receive_text()

            try:
                # Parse request
                request_data = json.loads(data)
                headline = request_data.get("headline")
                min_confidence = request_data.get("min_confidence", 0.3)
                llm_provider = request_data.get("llm_provider", "mock")

                if not headline:
                    await websocket.send_json({
                        "error": "No headline provided"
                    })
                    continue

                logger.info(f"WebSocket received headline: {headline} (provider: {llm_provider})")

                # Send processing status
                await websocket.send_json({
                    "status": "processing",
                    "headline": headline
                })

                # Run analysis (using default assessor for now)
                result = await assessor.analyze_news_impact(headline)

                # Convert to simplified format
                simplified = convert_to_simplified_output(result, min_confidence)

                # Send result
                await websocket.send_json({
                    "status": "completed",
                    "data": {
                        "headline": simplified.headline,
                        "impacted_entities": [
                            {
                                "currency": e.currency,
                                "confidence": e.confidence,
                                "confidence_score": e.confidence_score,
                                "reasoning": e.reasoning
                            }
                            for e in simplified.impacted_entities
                        ],
                        "processing_time_ms": simplified.processing_time_ms,
                        "analysis_timestamp": simplified.analysis_timestamp.isoformat(),
                        "metadata": simplified.metadata
                    }
                })

                logger.info(f"WebSocket sent result for: {headline}")

            except json.JSONDecodeError:
                await websocket.send_json({
                    "error": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}", exc_info=True)
                await websocket.send_json({
                    "error": f"Processing error: {str(e)}"
                })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)


@app.websocket("/ws/ticker")
async def websocket_ticker(websocket: WebSocket):
    """
    Bloomberg-style ticker WebSocket endpoint

    Clients connect and receive automatic updates when news is analyzed
    No need to send messages - just listen for broadcasts
    """
    await websocket.accept()
    active_connections.add(websocket)
    logger.info(f"Ticker client connected. Total connections: {len(active_connections)}")

    try:
        # Keep connection alive and wait for disconnect
        while True:
            # Wait for any message (client can send keepalive pings)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                # Echo back to confirm connection is alive
                await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
            except asyncio.TimeoutError:
                # Send periodic heartbeat
                await websocket.send_json({"type": "heartbeat", "timestamp": datetime.now().isoformat()})

    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info(f"Ticker client disconnected. Remaining connections: {len(active_connections)}")
    except Exception as e:
        logger.error(f"Ticker WebSocket error: {e}", exc_info=True)
        if websocket in active_connections:
            active_connections.remove(websocket)


async def broadcast_to_all_clients(message: dict):
    """Broadcast a message to all connected ticker clients"""
    if not active_connections:
        return

    logger.info(f"Broadcasting to {len(active_connections)} clients")

    # Create a copy to avoid modification during iteration
    connections = active_connections.copy()

    for websocket in connections:
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error broadcasting to client: {e}")
            # Remove dead connection
            if websocket in active_connections:
                active_connections.remove(websocket)


@app.post("/broadcast", tags=["Broadcasting"])
async def broadcast_news(request: NewsAnalysisRequest):
    """
    Analyze a headline and broadcast results to all connected ticker clients

    Used by the news ticker service to push updates to all UIs
    """
    if assessor is None:
        raise HTTPException(status_code=503, detail="Analysis service not initialized")

    try:
        # Analyze the headline
        result = await assessor.analyze_news_impact(
            request.headline,
            target_entities=request.target_entities
        )

        # Convert to simplified format
        simplified = convert_to_simplified_output(result, request.min_confidence)

        # Prepare broadcast message
        broadcast_message = {
            "type": "news_update",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "headline": simplified.headline,
                "impacted_entities": [
                    {
                        "currency": e.currency,
                        "confidence": e.confidence,
                        "confidence_score": e.confidence_score,
                        "reasoning": e.reasoning
                    }
                    for e in simplified.impacted_entities
                ],
                "processing_time_ms": simplified.processing_time_ms,
                "analysis_timestamp": simplified.analysis_timestamp.isoformat()
            }
        }

        # Broadcast to all connected clients
        await broadcast_to_all_clients(broadcast_message)

        logger.info(f"Broadcast news update: {request.headline[:50]}...")

        return {
            "status": "broadcast",
            "clients_notified": len(active_connections),
            "result": simplified
        }

    except Exception as e:
        logger.error(f"Error in broadcast: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Broadcast failed: {str(e)}")


if __name__ == "__main__":
    # Run the API server
    import os

    # Get port from environment or use default
    port = int(os.getenv("API_PORT", 8000))

    logger.info(f"Starting API service on port {port}")

    uvicorn.run(
        "api_service:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Enable auto-reload for development
        log_level="info"
    )
