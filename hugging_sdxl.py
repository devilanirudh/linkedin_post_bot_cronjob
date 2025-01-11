import requests
from PIL import Image
from io import BytesIO
import os
from dotenv import load_dotenv
load_dotenv()

# Replace with your Hugging Face API token
API_TOKEN = os.getenv("API_TOKEN")

# The URL for the Stable Diffusion XL endpoint
API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"

def generate_image(prompt: str) -> str:
    """
    Generates an image from a given prompt using the Hugging Face API.
    
    Args:
        prompt (str): The text prompt to generate an image from.
    
    Returns:
        str: The filename of the generated image.
    """
    headers = {
        "Authorization": f"Bearer {API_TOKEN}"
    }

    payload = {
        "inputs": prompt,
        "options": {"wait_for_model": True}  # Ensures the model loads if it's not already
    }

    response = requests.post(API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        image_data = BytesIO(response.content)
        image = Image.open(image_data)
        filename = "generated_image.png"
        image.save(filename)
        return filename
    else:
        raise Exception(f"Request failed: {response.status_code}, {response.text}")

# # Example usage
# if __name__ == "__main__":
#     try:
#         prompt = "A futuristic cityscape with flying cars, neon lights, and a cyberpunk atmosphere"
#         filename = generate_image(prompt)
#         print(f"Image saved as '{filename}'")
#     except Exception as e:
#         print(e)
