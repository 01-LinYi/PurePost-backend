import numpy as np
import onnxruntime
import os
from PIL import Image
import logging
# Configure logging
logger = logging.getLogger("dfdetect.inference")

# Global variables
MODEL_NAME = "ResNet18" # "ResNet18_unoptimized"
MODEL_PATH = os.path.join("model", f"{MODEL_NAME}.onnx")
INPUT_SIZE = (224, 224)  # Model input dimensions
LABELS = ["real", "deepfake"]  # Class labels
# Pre-compute ImageNet mean and std for faster processing
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape((1, 1, 3))
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape((1, 1, 3))

def initialize_model():
    """
    Initialize ONNX Runtime session and load the deepfake detection model.
    This function should be called at application startup.
    
    Returns:
        bool: True if model loaded successfully
        
    Raises:
        FileNotFoundError: If model file doesn't exist
        RuntimeError: If model loading fails
    """
    global SESSION
    
    try:
        # Check if model file exists
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")
        
        # Create inference session with optimizations
        logger.info(f"Loading model from {MODEL_PATH}")
        
        # Configure session options for better performance
        sess_options = onnxruntime.SessionOptions()
        # Enable all graph optimizations for best performance
        sess_options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
        # Set number of threads for CPU computation
        sess_options.intra_op_num_threads = 4  # Adjust based on your hardware
        
        # Try to use GPU if available, fallback to CPU
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if 'CUDAExecutionProvider' in onnxruntime.get_available_providers() else ['CPUExecutionProvider']
        
        # Create the inference session
        SESSION = onnxruntime.InferenceSession(MODEL_PATH, sess_options=sess_options, providers=providers)
        
        # Validate model input/output
        input_name = SESSION.get_inputs()[0].name
        input_shape = SESSION.get_inputs()[0].shape
        logger.info(f"Model input name: {input_name}, shape: {input_shape}")
        logger.info(f"Model loaded successfully using providers: {SESSION.get_providers()}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize model: {str(e)}")
        raise

def is_model_loaded():
    """
    Check if the model is loaded and ready for inference.
    
    Returns:
        bool: True if model is loaded, False otherwise
    """
    return SESSION is not None

def preprocess_image(image):
    """
    Optimized image preprocessing function for the deepfake detection model.
    
    This function:
    1. Resizes the image to the required input size (224x224)
    2. Normalizes pixel values to [0,1]
    3. Applies ImageNet mean/std normalization
    4. Converts from HWC to NCHW format
    
    Args:
        image: PIL Image object
        
    Returns:
        np.ndarray: Preprocessed image as numpy array in NCHW format
    """
    # Ensure the image is in RGB format
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Resize to exact 224x224 (fast but may distort image)
    if image.size != INPUT_SIZE:
        image = image.resize(INPUT_SIZE, Image.BILINEAR)
    
    # Convert to numpy array with float32 precision
    img_array = np.array(image, dtype=np.float32)
    
    # Normalize to [0,1]
    img_array /= 255.0
    
    # Apply ImageNet normalization using pre-computed values
    img_array = (img_array - IMAGENET_MEAN) / IMAGENET_STD
    
    # Rearrange dimensions from HWC to NCHW format (batch, channels, height, width)
    img_array = img_array.transpose(2, 0, 1)
    # Add batch dimension
    img_array = np.expand_dims(img_array, axis=0)
    logger.debug(f"Preprocessed image shape: {img_array.shape}")
    
    return img_array.astype(np.float32)  # Ensure float32 type for inference

def preprocess_image_advanced(image):
    """
    Advanced image preprocessing that preserves aspect ratio.
    This method maintains the original proportions of the image 
    and adds padding to reach the required dimensions.
    
    Args:
        image: PIL Image object
        
    Returns:
        np.ndarray: Preprocessed image as numpy array in NCHW format
    """
    # Calculate resize scale while preserving aspect ratio
    width, height = image.size
    scale = max(INPUT_SIZE[0] / width, INPUT_SIZE[1] / height)
    new_width = int(width * scale)
    new_height = int(height * scale)
    
    # Resize image while preserving aspect ratio
    image = image.resize((new_width, new_height), Image.BILINEAR)
    
    # Create a blank black canvas of 224x224
    new_image = Image.new("RGB", INPUT_SIZE, (0, 0, 0))
    
    # Calculate position to paste the resized image (centered)
    paste_x = (INPUT_SIZE[0] - new_width) // 2
    paste_y = (INPUT_SIZE[1] - new_height) // 2
    new_image.paste(image, (paste_x, paste_y))
    
    # Convert to numpy and normalize
    img_array = np.array(new_image, dtype=np.float32)
    img_array /= 255.0
    img_array = (img_array - IMAGENET_MEAN) / IMAGENET_STD
    
    # Rearrange to NCHW format
    img_array = img_array.transpose(2, 0, 1)
    img_array = np.expand_dims(img_array, axis=0)
    
    return img_array.astype(np.float32)

def predict(image):
    """
    Perform deepfake detection on the input image.
    
    The function:
    1. Preprocesses the input image
    2. Runs inference through the ONNX model
    3. Post-processes the model output (applying softmax if needed)
    4. Returns prediction results with confidence scores
    
    Args:
        image: PIL Image object
        
    Returns:
        list: List of dictionaries containing label and confidence score
              [{"label": "real", "score": 0.98}, {"label": "deepfake", "score": 0.02}]
    
    Raises:
        RuntimeError: If model is not initialized
        Exception: If prediction process fails
    """
    if SESSION is None:
        raise RuntimeError("Model not initialized. Call initialize_model() first.")
    
    try:
        # Use optimized preprocessing
        input_data = preprocess_image(image)
        
        # Get model input and output names
        input_name = SESSION.get_inputs()[0].name
        output_name = SESSION.get_outputs()[0].name
        
        # Run inference
        outputs = SESSION.run([output_name], {input_name: input_data})
        scores = outputs[0][0]  # Extract scores
        # Process output based on model type
        if len(scores) == len(LABELS):
            # Apply softmax to convert logits to probabilities
            # Subtract max for numerical stability
            exp_scores = np.exp(scores - np.max(scores))
            probs = exp_scores / exp_scores.sum()
        else:
            # Assume model already outputs probabilities
            probs = scores
            
        # Build result structure
        results = []
        for i, label in enumerate(LABELS):
            results.append({
                "label": label,
                "score": float(probs[i])  # Convert to Python float for JSON serialization
            })
        
        # Sort results by confidence score (highest first)
        results = sorted(results, key=lambda x: x["score"], reverse=True)
        
        logger.debug(f"Prediction results: {results}")
        
        return results
    
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        raise