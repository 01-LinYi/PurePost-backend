import torch

# Path to your .pth file
pth_file_path = "model/ResNet18.pth"

# Load the .pth file
checkpoint = torch.load(pth_file_path)

# Print the keys in the .pth file
print("Keys in the .pth file:")
for key in checkpoint.keys():
    print(f"  {key}")

# If it's a state_dict, print its structure
if "model_state_dict" in checkpoint:
    print("\nModel State Dict Keys:")
    for key in checkpoint["model_state_dict"].keys():
        print(f"  {key}")
elif isinstance(checkpoint, dict):
    print("\nState Dict-like Structure Detected:")
    for key in checkpoint.keys():
        print(f"  {key}")
else:
    print("\nRaw Content of .pth file:")
    print(checkpoint)