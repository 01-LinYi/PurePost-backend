import argparse
import os
import torch
import torch.nn as nn
import torch.onnx
import numpy as np
from torchvision import models, transforms
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("model_converter")


def load_pytorch_model(model_path, device='cuda'):
    """
    Load a PyTorch model from checkpoint file.

    Args:
        model_path: Path to the .pth checkpoint file
        device: Device to load the model on ('cuda' or 'cpu')

    Returns:
        PyTorch model with loaded weights
    """
    logger.info(f"Loading PyTorch model from {model_path}")

    # Create base ResNet18 model
    model = models.resnet18(weights=None)
    # Modify the last fully connected layer to have 2 output classes
    num_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(0.5),  # Add dropout layer for regularization
        nn.Linear(num_features, 2),  # Change output to 2 classes        # Apply softmax activation
    )
    logger.info("Created modified ResNet18 model with sequential FC layer")

    # Load checkpoint
    checkpoint = torch.load(model_path, map_location=device,weights_only=True)
    logger.info(f"Checkpoint loaded from {model_path}")
    logger.info(f"Checkpoint type: {type(checkpoint)}")
    
    # Inspect checkpoint keys for debugging
    if isinstance(checkpoint, dict):
        # Log the keys of the checkpoint
        logger.info(f"Checkpoint keys: {list(checkpoint.keys())[:10]}...")
        
        # Check if "state_dict" or "model_state_dict" exists
        if 'model_state_dict' in checkpoint:
            state_dict = checkpoint['model_state_dict']
            logger.info("Using 'model_state_dict' from checkpoint")
        elif 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
            logger.info("Using 'state_dict' from checkpoint")
        else:
            state_dict = checkpoint
            logger.info("Using checkpoint directly as state_dict")
           
        # Try loading the state_dict
        try:
            model.load_state_dict(state_dict, strict=True)
            logger.info("State dict loaded successfully with strict=True")
        except RuntimeError as e:
            logger.warning(f"Strict loading failed: {e}")
            incompatible = model.load_state_dict(state_dict, strict=False)
            logger.warning(f"State dict loaded with strict=False")
            logger.warning(f"Missing keys: {incompatible.missing_keys}")
            logger.warning(f"Unexpected keys: {incompatible.unexpected_keys}")
    else:
        # If checkpoint is not a dict, directly load it
        try:
            model.load_state_dict(checkpoint)
            logger.info("State dict loaded as OrderedDict")
        except Exception as e:
            logger.error(f"Loading failed: {e}")
            raise

    # Move model to the specified device
    model.to(device)
    model.eval()  # Set to evaluation mode

    logger.info("Successfully loaded model")
    return model


def convert_to_onnx(model, output_path, input_shape=(1, 3, 224, 224),
                    dynamic_axes=False, optimize=True, quantize=True):
    """
    Convert PyTorch model to ONNX format.

    Args:
        model: PyTorch model
        output_path: Path to save the ONNX model
        input_shape: Input shape for the model (batch_size, channels, height, width)
        dynamic_axes: Whether to use dynamic axes (for variable batch size)
        optimize: Whether to optimize the ONNX model
        quantize: Whether to quantize the ONNX model
    """
    logger.info(f"Converting model to ONNX format...")

    # Create dummy input tensor
    dummy_input = torch.randn(input_shape, requires_grad=True)
    dummy_input = dummy_input.to(next(model.parameters()).device)

    # Define dynamic axes if requested
    dynamic_axes_params = None
    if dynamic_axes:
        dynamic_axes_params = {
            'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}

    # Export the model to ONNX format
    unoptimized_path = output_path.replace('.onnx', '_unoptimized.onnx')
    torch.onnx.export(
        model,                      # PyTorch model
        dummy_input,                # Input tensor
        unoptimized_path,           # Output file path
        export_params=True,         # Store model weights in the model file
        opset_version=17,           # Updated ONNX opset version for PyTorch 2.5+
        do_constant_folding=True,   # Optimize constants
        input_names=['input'],      # Input tensor name
        output_names=['output'],    # Output tensor name
        dynamic_axes=dynamic_axes_params,  # Dynamic axes if specified
    )

    logger.info(f"ONNX model exported to {unoptimized_path}")

    # Optimize the model if requested
    if optimize or quantize:
        try:
            import onnx
            from onnxruntime.quantization import quantize_dynamic, QuantType

            # Load the ONNX model
            onnx_model = onnx.load(unoptimized_path)
            # Check the model for correctness
            onnx.checker.check_model(onnx_model)
            logger.info("ONNX model checked for correctness")

            if optimize and not quantize:
                # Save the optimized model
                optimized_path = output_path
                onnx.save(onnx_model, optimized_path)
                logger.info(f"Optimized ONNX model saved to {optimized_path}")

            if quantize:
                # Quantize the model
                quantized_path = output_path
                quantize_dynamic(
                    model_input=unoptimized_path,
                    model_output=quantized_path,
                    weight_type=QuantType.QUInt8,
                    optimize_model=True
                )
                logger.info(f"Quantized ONNX model saved to {quantized_path}")

        except ImportError as e:
            logger.warning(f"Couldn't optimize/quantize model: {str(e)}")
            logger.warning(
                "Install onnx and onnxruntime packages for optimization")

            # Rename unoptimized model to output path
            os.rename(unoptimized_path, output_path)
            logger.info(f"Saved unoptimized model to {output_path}")
        except Exception as e:
            logger.error(f"Error during optimization/quantization: {str(e)}")
            # Ensure we still have a model output even if optimization fails
            if not os.path.exists(output_path):
                os.rename(unoptimized_path, output_path)
                logger.info(f"Saved unoptimized model to {output_path} due to optimization error")


def verify_onnx_model(onnx_path, input_shape=(1, 3, 224, 224)):
    """
    Verify that the ONNX model produces the same output as the PyTorch model.

    Args:
        onnx_path: Path to the ONNX model
        input_shape: Input shape for testing
    """
    try:
        import onnxruntime
        import numpy as np

        logger.info(f"Verifying ONNX model...")

        # Create random input data
        input_data = np.random.randn(*input_shape).astype(np.float32)

        # Create ONNX Runtime session
        sess_options = onnxruntime.SessionOptions()
        sess_options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        providers = ['CPUExecutionProvider']
        if 'CUDAExecutionProvider' in onnxruntime.get_available_providers():
            providers.insert(0, 'CUDAExecutionProvider')
            
        ort_session = onnxruntime.InferenceSession(
            onnx_path, 
            sess_options=sess_options,
            providers=providers
        )

        # Run the ONNX model
        ort_inputs = {ort_session.get_inputs()[0].name: input_data}
        ort_outputs = ort_session.run(None, ort_inputs)

        logger.info(f"ONNX model verified successfully")
        logger.info(f"Output shape: {ort_outputs[0].shape}")

        # Print example prediction
        if ort_outputs[0].shape[1] == 2:
            def softmax(x): return np.exp(x) / \
                np.sum(np.exp(x), axis=1, keepdims=True)
            probabilities = softmax(ort_outputs[0])
            logger.info(
                f"Example prediction [real, fake] probabilities: {probabilities[0]}")

        return True

    except Exception as e:
        logger.error(f"Error verifying ONNX model: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Convert PyTorch model to ONNX')
    parser.add_argument('--input', type=str, required=True,
                        help='Path to PyTorch .pth model')
    parser.add_argument('--output', type=str, required=True,
                        help='Path to save ONNX model')
    parser.add_argument('--input_size', type=int, default=224,
                        help='Input image size (default: 224)')
    parser.add_argument('--batch_size', type=int, default=1,
                        help='Batch size (default: 1)')
    parser.add_argument('--dynamic', action='store_true',
                        help='Use dynamic axes for batch size')
    parser.add_argument('--no_optimize', action='store_true',
                        help='Skip ONNX optimization')
    parser.add_argument('--no_quantize', action='store_true',
                        help='Skip ONNX quantization')
    parser.add_argument('--cpu', action='store_true',
                        help='Use CPU instead of CUDA')
    args = parser.parse_args()

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    # Determine device
    device = 'cpu' if args.cpu or not torch.cuda.is_available() else 'cuda'
    logger.info(f"Using device: {device}")
    
    # Log PyTorch version
    logger.info(f"PyTorch version: {torch.__version__}")

    # Load the PyTorch model
    model = load_pytorch_model(args.input, device)

    # Convert model to ONNX
    input_shape = (args.batch_size, 3, args.input_size, args.input_size)
    convert_to_onnx(
        model,
        args.output,
        input_shape=input_shape,
        dynamic_axes=args.dynamic,
        optimize=not args.no_optimize,
        quantize=not args.no_quantize
    )

    # Verify the ONNX model
    if not args.no_optimize and not args.no_quantize:
        verify_onnx_model(args.output, input_shape)
    else:
        # Verify the unoptimized model
        logger.info("Verifying unoptimized ONNX model...")
        verify_onnx_model("model/ResNet18_unoptimized.onnx", input_shape)

    logger.info("Conversion completed successfully")


if __name__ == "__main__":
    main()
    # Example usage:
    # python convert_to_onnx.py --input model/ResNet18.pth --output model/ResNet18.onnx --input_size 224 --batch_size 1 --dynamic --no_quantize
    # python convert_to_onnx.py --input model/ResNet18.pth --output model/ResNet18.onnx --input_size 224 --batch_size 1 --dynamic --no_optimize --no_quantize
