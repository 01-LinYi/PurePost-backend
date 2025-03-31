from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
import time
import os
from io import BytesIO
from PIL import Image
import inference

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("dfdetect")

# Initialize FastAPI app
app = FastAPI(
    title="Deepfake Detection API",
    description="API for detecting deepfake images using ONNX models",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Start-up event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting deepfake detection service")
    # Load model on startup
    try:
        inference.initialize_model()
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        raise e

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down deepfake detection service")

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring service status
    """
    try:
        # Verify model is loaded
        model_loaded = inference.is_model_loaded()
        
        # Check model file existence
        model_path = os.path.join("model", "resnet_quantized.onnx")
        model_exists = os.path.isfile(model_path)
        
        return {
            "status": "healthy" if model_loaded and model_exists else "unhealthy",
            "timestamp": time.time(),
            "model_loaded": model_loaded,
            "model_exists": model_exists
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
        )

# Prediction endpoint
@app.post("/predict")
async def predict_image(file: UploadFile = File(...)):
    """
    Analyze uploaded image for deepfake detection
    
    Returns prediction results with confidence scores
    """
    start_time = time.time()
    
    try:
        # Validate file extension
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file format. Supported formats: {', '.join(allowed_extensions)}"
            )
        
        # Read image file
        contents = await file.read()
        
        # Process image with model
        try:
            image = Image.open(BytesIO(contents)).convert('RGB')
        except Exception as e:
            logger.error(f"Failed to process image: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid image format or corrupted file")
        
        # Run inference
        predictions = inference.predict(image)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Log prediction result
        is_deepfake = any(pred["label"] == "deepfake" and pred["score"] > 0.5 for pred in predictions)
        logger.info(f"Prediction complete: file={file.filename}, is_deepfake={is_deepfake}, time={processing_time:.2f}s")
        
        # Return results
        return {
            "success": True,
            "predictions": predictions,
            "processing_time": processing_time
        }
    
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error occurred during processing",
                "detail": str(e)
            }
        )

# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint with API information
    """
    return {
        "service": "Deepfake Detection API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "/predict": "POST - Analyze image for deepfake detection",
            "/health": "GET - Check service health status"
        }
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=5555, reload=False)