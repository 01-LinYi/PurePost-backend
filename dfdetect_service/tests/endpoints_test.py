import requests
# Define the API endpoint and file path
url = "http://localhost:5555/predict"  # Replace with your API address
# Replace with your own file path
# Make sure the working directory is correct
# or provide the absolute path to the file
file_path = "./tests/img/DGM4-bbc-Real2.jpg"
# file_path = "./tests/img/DGM4-wapo-Real3.jpg"

# File upload with multipart/form-data
with open(file_path, "rb") as file:
    # Prepare the file for upload using multipart/form-data
    files = {"file": file}
    # Optional, requests sets this automatically
    # headers = {"Content-Type": "multipart/form-data"}

    try:
        # Send POST request to the API
        response = requests.post(url, files=files)

        # Raise an exception for HTTP errors (status codes 4xx/5xx)
        response.raise_for_status()

        # Print the response status and content
        print("Status Code:", response.status_code)
        print("Response Content:", response.text)

    except requests.exceptions.RequestException as e:
        # Handle exceptions (e.g., connection errors, HTTP errors)
        print(f"Request failed: {e}")
