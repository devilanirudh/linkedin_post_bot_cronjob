import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Replace with your Vyro API key
API_KEY = os.getenv("API_KEY")

# Base URL for the Vyro Text-to-Image API
API_URL = "https://api.vyro.ai/v2/image/generations"

def generate_image(prompt: str, style: str = "anime", aspect_ratio: str = "1:1") -> str:
    """
    Generates an image using the Vyro Text-to-Image API.
    
    Args:
        prompt (str): The text prompt to generate an image from.
        style (str): The style of the image (e.g., "realistic", "abstract").
        aspect_ratio (str): The aspect ratio of the image (e.g., "1:1", "16:9").
    
    Returns:
        str: The filename of the generated image.
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }

    # Prepare the multipart form data
    form_data = {
        "prompt": (None, prompt),
        "style": (None, style),
        "aspect_ratio": (None, aspect_ratio)
    }

    # Send the request
    response = requests.post(API_URL, headers=headers, files=form_data)

    if response.status_code == 200:
        # Save the binary image response
        filename = "generated_image.png"
        with open(filename, "wb") as f:
            f.write(response.content)
        print(f"Image successfully generated and saved as '{filename}'")
        return filename
    else:
        # Handle errors
        raise Exception(f"Request failed with status code {response.status_code}: {response.text}")

# Example Usage
if __name__ == "__main__":
    try:
        # Example prompt
        prompt = "A futuristic, clean, and bright medical laboratory setting, showcasing a large holographic display showing a detailed 3D model of a breast with highlighted cancerous areas (pink/red), overlaid with intricate AI-generated neural network visualizations (glowing blue lines and nodes).  A partially visible, diverse team of radiologists (men and women of varying ages and ethnicities) collaborate around the display, with one pointing at a specific area on the holographic model.  In the foreground, a subtle, hopeful graphic showing an upward-trending graph representing improved cancer detection rates (+17.6%). The overall style should be photorealistic with a touch of futuristic sci-fi elements to convey technological advancement.  The mood should be optimistic and hopeful"
        filename = generate_image(prompt, style="anime", aspect_ratio="16:9")
        print(f"Image saved as '{filename}'")
    except Exception as e:
        print(f"Error: {e}")
