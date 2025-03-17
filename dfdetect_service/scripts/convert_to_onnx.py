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


class DeepfakeDetectionModel(nn.Module):
    """
    **IMPORTANT**: This is just an example deepfake detection model architecture.
    Replace this with your actual model architecture.
    """

    def __init__(self, num_classes=2):
        super(DeepfakeDetectionModel, self).__init__()
        # Use a pre-trained ResNet as base
        self.base_model = models.resnet18(pretrained=False)
        # Replace final fully connected layer
        num_features = self.base_model.fc.in_features
        self.base_model.fc = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(num_features, num_classes)
        )

    def forward(self, x):
        return self.base_model(x)


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

    # Initialize your model architecture
    model = DeepfakeDetectionModel(num_classes=2)

    # Load checkpoint
    checkpoint = torch.load(model_path, map_location=device)

    # Handle different checkpoint formats
    if isinstance(checkpoint, dict):
        # If checkpoint is a dict with 'state_dict' key
        if 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
        # If checkpoint is a dict with model weights directly
        else:
            state_dict = checkpoint
    else:
        # If checkpoint is the state_dict itself
        state_dict = checkpoint

    # Remove 'module.' prefix if model was trained with DataParallel
    new_state_dict = {}
    for k, v in state_dict.items():
        name = k.replace('module.', '') if 'module.' in k else k
        new_state_dict[name] = v

    # Load state dict into model
    model.load_state_dict(new_state_dict)
    model.to(device)
    model.eval()  # Set to evaluation mode

    logger.info(f"Successfully loaded model")
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
        opset_version=12,           # ONNX opset version
        do_constant_folding=True,   # Optimize constants
        input_names=['input'],      # Input tensor name
        output_names=['output'],    # Output tensor name
        dynamic_axes=dynamic_axes_params,  # Dynamic axes if specified
        verbose=False
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
                    unoptimized_path,
                    quantized_path,
                    weight_type=QuantType.QUInt8
                )
                logger.info(f"Quantized ONNX model saved to {quantized_path}")

            # Remove the unoptimized model if optimization was successful
            if os.path.exists(output_path):
                os.remove(unoptimized_path)
                logger.info(f"Removed unoptimized model {unoptimized_path}")

        except ImportError as e:
            logger.warning(f"Couldn't optimize/quantize model: {str(e)}")
            logger.warning(
                "Install onnx and onnxruntime packages for optimization")

            # Rename unoptimized model to output path
            os.rename(unoptimized_path, output_path)
            logger.info(f"Saved unoptimized model to {output_path}")


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
        ort_session = onnxruntime.InferenceSession(onnx_path)

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
    verify_onnx_model(args.output, input_shape)

    logger.info("Conversion completed successfully")


if __name__ == "__main__":
    main()
