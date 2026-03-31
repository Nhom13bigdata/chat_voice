"""
Medical Intake Backend - Voice-First Patient Data Collection

Architecture:
    WebSocket Client ←→ FastAPI ←→ Gemini Live API
         (Browser)      (This app)   (Google)

Key Features:
    - Bidirectional audio streaming (16kHz input, 24kHz output)
    - Real-time transcription with text accumulation
    - Structured medical data extraction via function calling
    - Session logging and conversation persistence

Endpoints:
    GET  /              - Service information
    GET  /health        - Health check for monitoring
    GET  /api-key-status- Verifies a key is loaded without leaking it
    WS   /ws            - WebSocket for audio streaming

Usage:
    uvicorn main:app --host 0.0.0.0 --port 8000

Environment Variables:
    See .env.example for required configuration
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from gemini_live import GeminiLiveSession
from config import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Medical Intake Backend",
    description="Voice-First Medical Intake System using Gemini Live API",
    version="2.0.0",
    docs_url="/docs",  # Swagger UI at /docs
    redoc_url="/redoc",  # ReDoc at /redoc
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Shows service info"""
    return {
        "service": "Medical Intake Backend",
        "version": "2.0.0",
        "status": "running",
        "api": "Gemini Live API",
        "model": settings.MODEL_NAME,
    }


@app.get("/health")
async def health_check():
    """For monitoring"""
    return {"status": "healthy", "live_api": "connected"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, api_key: str = None):
    """
    WebSocket endpoint for real-time bidirectional audio streaming

    This is the main endpoint that handles audio streaming between the
    frontend and Gemini Live API. It creates a GeminiLiveSession that
    manages the entire conversation lifecycle.

    Connection Flow:
    ---------------
    1. Frontend connects to ws://localhost:8000/ws
    2. Server accepts connection
    3. GeminiLiveSession is created and initialized
    4. Gemini Live API connection is established
    5. Bidirectional audio streaming begins
    6. Session runs until disconnection or error

    Message Types FROM Frontend:
    ---------------------------
    1. Audio bytes:
       - Raw PCM audio chunks from microphone
       - Format: 16-bit PCM, 16kHz, mono
       - Sent as WebSocket binary frames

    2. Control messages (JSON):
       - {"type": "interrupt"}    : Interrupt AI mid-response
       - {"type": "end_session"}  : End the conversation

    Message Types TO Frontend:
    -------------------------
    1. Audio bytes:
       - AI audio response
       - Format: 16-bit PCM, 24kHz, mono
       - Sent as WebSocket binary frames

    2. Status messages (JSON):
       {
           "type": "status",
           "state": "ready",
           "message": "Connected to Gemini"
       }

    3. Transcript messages (JSON):
       {
           "type": "transcript",
           "role": "assistant",
           "text": "Hello! What brings you in today?"
       }

    4. Medical data updates (JSON):
       {
           "type": "extracted_data",
           "data": {
               "patient_info": {...},
               "present_illness": {...},
               "medications": [...],
               "allergies": [...],
               ...
           }
       }

    5. Intake completion signal (JSON):
       {
           "type": "intake_complete",
           "message": "Medical intake completed successfully"
       }

    6. Error messages (JSON):
       {
           "type": "error",
           "message": "Error description"
       }

    Error Handling:
    --------------
    - WebSocketDisconnect: Normal disconnection, cleanup happens
    - Other exceptions: Logged with full traceback, error sent to frontend if possible
    - All cases: Session cleanup is guaranteed via finally block

    Args:
        websocket (WebSocket): The WebSocket connection
        api_key (str, optional): Gemini API key from query parameter

    Example Frontend Connection (JavaScript):
        const ws = new WebSocket('ws://localhost:8000/ws?api_key=YOUR_KEY');

        // Send audio
        ws.send(audioPCMBytes);

        // Receive messages
        ws.onmessage = (event) => {
            if (event.data instanceof Blob) {
                // Audio data - play it
                playAudio(event.data);
            } else {
                // JSON message - parse it
                const msg = JSON.parse(event.data);
                if (msg.type === 'transcript') {
                    console.log(msg.role, msg.text);
                } else if (msg.type === 'extracted_data') {
                    updateForm(msg.data);
                } else if (msg.type === 'intake_complete') {
                    // Navigate to review screen
                    goToReviewScreen();
                }
            }
        };
    """
    await websocket.accept()
    logger.info("WebSocket connection accepted from client")

    # Determine which API key to use
    # Priority: 1. Query parameter, 2. Environment variable
    final_api_key = api_key if api_key else settings.GEMINI_API_KEY

    if not final_api_key:
        logger.error("No API key provided")
        await websocket.send_json(
            {
                "type": "error",
                "message": "No API key provided. Please provide an API key via query parameter or environment variable.",
            }
        )
        await websocket.close()
        return

    logger.info(
        f"Using API key: {'from query parameter' if api_key else 'from environment'}"
    )

    # Create a new Gemini Live session for this connection
    session = GeminiLiveSession(api_key=final_api_key)

    try:
        # Run the session - this blocks until disconnection or error
        # The session handles all bidirectional communication internally
        logger.info("Starting Gemini Live session")
        await session.run(websocket)

    except WebSocketDisconnect:
        # Client disconnected normally (e.g., closed browser tab)
        logger.info("WebSocket disconnected by client")

    except Exception as e:
        # Unexpected error occurred
        logger.error(f"WebSocket error: {e}", exc_info=True)

        # Try to send error message to frontend
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            # WebSocket might already be closed - ignore
            pass

    finally:
        # Always cleanup, regardless of how we exited
        # This ensures Gemini connection is properly closed
        await session.cleanup()
        logger.info("WebSocket connection closed and cleaned up")


if __name__ == "__main__":
    logger.info(f"Starting server on {settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
        loop="asyncio",
        ws_ping_interval=20,
        ws_ping_timeout=30,
    )
