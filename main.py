from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
from PIL import Image
from io import BytesIO
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import time
import logging
logging.basicConfig(level=logging.INFO)
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

# Load environment variables
load_dotenv()


genai_api_key = os.getenv("GENAI_API_KEY")
stability_api_key = os.getenv("STABILITY_API_KEY")
linkedin_access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
linkedin_profile_id = os.getenv("LINKEDIN_PROFILE_ID")


# Configure Gemini
genai.configure(api_key=genai_api_key)
model = genai.GenerativeModel('gemini-1.5-flash')


# Initialize FastAPI
app = FastAPI()

class PostRequest(BaseModel):
    category: str
    prompt: str

# Fetch website HTML content
def fetch_website_content(url: str) -> str:
    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch website content.")
    return response.text

def select_and_process_article(website_html: str, prompt: str) -> str:
    # Simulate Gemini identifying the article
    gemini_prompt = f"""
    You are an intelligent assistant tasked with analyzing the most relevant and recent article from a website. 
    Here's the website's HTML content:

    {website_html}

    Based on the following prompt, find the most recent and relevant article and identify its title and URL:

    {prompt}

    Provide the title and the URL of the article.
    Format your response as follows:
    Title: <title>
    URL: <url>
    """
    gemini_response = model.generate_content(gemini_prompt)
    
    # Assume the response format is: "Title: <title>\nURL: <url>"
    lines = gemini_response.text.strip().split("\n")
    article_title = None
    article_url = None
    for line in lines:
        if line.startswith("Title:"):
            article_title = line.replace("Title:", "").strip()
        elif line.startswith("URL:"):
            article_url = line.replace("URL:", "").strip()

    if not article_title or not article_url:
        raise Exception("Failed to identify the article title or URL.")

    # Fetch the full article content
    print(article_url)
    full_article_html = fetch_website_content(article_url)

    linkedin_prompt = f"""
    You now have access to the full content of the article titled "{article_title}". 
    Create an engaging, informative, and creative LinkedIn post that compels readers to dive into the topic. 
    Ensure the post is well-structured, concise, and packed with details to make it crisp and interesting.

    Avoid including any links, references to the article link, or additional instructions. The response should read like a fully developed LinkedIn post and must not contain any irrelevant content or formatting artifacts, such as asterisks (*) or bold text. Do not format headings, titles, or any part of the content in bold or special styles.

    Make the post visually engaging by including structured elements like lists, bullet points, or concise paragraphs, and ensure it flows naturally while delivering value to the reader. Focus on providing a complete and standalone informative post, keeping the content professional and compelling.
    include hashtags for the post and keep it detailed .
    Here's the full article content for reference:

    {full_article_html}
    """

    linkedin_response = model.generate_content(linkedin_prompt)

    return linkedin_response.text.strip()




# Summarize article
def generate_summary(article_content: str) -> str:
    summary_prompt = f"""
    Summarize the following article for a ai text to image genrator for image prompt:
    
    {article_content}
    """
    response = model.generate_content(summary_prompt)
    return response.text.strip()


def generate_image(summary_text: str, save_to_file: bool = False, file_name: str = "./generated_image.webp") -> str:
    """
    Generate an image based on the given summary text using Stability AI's API.

    Args:
        summary_text (str): The text prompt for the image generation.
        save_to_file (bool): Whether to save the generated image to a local file. Default is False.
        file_name (str): The name of the file to save the image if save_to_file is True. Default is "generated_image.webp".

    Returns:
        str: The file path of the generated image or raises an exception if failed.
    """
    try:
        # Define the API endpoint and headers
        url = "https://api.stability.ai/v2beta/stable-image/generate/ultra"
        headers = {
            "authorization": f"Bearer {stability_api_key}",
            "accept": "image/*"
        }

        # Define the payload
        data = {
            "prompt": summary_text,
            "output_format": "webp",
        }

        # Make the POST request
        response = requests.post(
            url,
            headers=headers,
            files={"none": ''},  # Stability AI requires this field
            data=data,
        )

        # Check response status
        if response.status_code == 200:
            file_name = file_name
            with open(file_name, 'wb') as file:
                file.write(response.content)
                return file_name

        # Handle errors
        else:
            raise Exception(f"Error: {response.status_code}, Details: {response.json()}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating image: {str(e)}")


# Get the access token
access_token = linkedin_access_token
# print(f"Access Token: {access_token}")

def register_image(access_token, image_path):
    # Step 1: Register the image upload
    register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": "urn:li:person:2biUrLTrHg",  # Replace with your LinkedIn Profile ID
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }
            ]
        }
    }
    
    # Register image
    response = requests.post(register_url, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"Failed to register image: {response.json()}")
        raise Exception("Error while registering the image")
    
    response_data = response.json()
    upload_url = response_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
    asset = response_data["value"]["asset"]
    
    # Step 2: Upload the image binary
    with open(image_path, "rb") as image_file:
        upload_response = requests.post(upload_url, headers={"Authorization": f"Bearer {access_token}"}, data=image_file)
        if upload_response.status_code not in [200, 201]:
            print(f"Failed to upload image: {upload_response.json()}")
            raise Exception("Error while uploading the image")
    
    print("Image successfully uploaded.")
    return asset


def post_to_linkedin(access_token, content, image_path=None):
    post_url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    # If an image is provided, register and upload it first
    image_asset = None
    if image_path:
        image_asset = register_image(access_token, image_path)
    
    # Create the payload for the post
    payload = {
        "author": f"urn:li:person:{linkedin_profile_id}",  # Replace with your LinkedIn Profile ID
        "lifecycleState": "PUBLISHED",
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": content
                },
                "shareMediaCategory": "NONE" if not image_asset else "IMAGE",
                "media": [
                    {
                        "status": "READY",
                        "description": {
                            "text": "Image description"
                        },
                        "media": image_asset,
                        "title": {
                            "text": "Post Title"
                        }
                    }
                ] if image_asset else []
            }
        }
    }

    # Make the request to create the post
    response = requests.post(post_url, headers=headers, json=payload)
    if response.status_code == 201:
        print("Post successfully created on LinkedIn!")
    else:
        print(f"Failed to create post: {response.json()}")
        raise Exception("Error while posting on LinkedIn")

# Main route

def scheduled_task():
    print(f"Scheduled Task Executed at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        # Example of generating a LinkedIn post every day
        url = "https://indianexpress.com/section/technology/"  # Update category if needed
        website_html = fetch_website_content(url)
        prompt = "Recent trends in technology and artificial intelligene , machine learning"
        
        # Process article and post to LinkedIn
        article_content = select_and_process_article(website_html, prompt)
        summary = generate_summary(article_content)
        image_prompt = f"An illustration related to {summary}."
        image_path = generate_image(image_prompt)
        access_token = linkedin_access_token
        post_to_linkedin(access_token, article_content, image_path)
    except Exception as e:
        print(f"Error in scheduled task: {e}")

scheduler = BackgroundScheduler()


scheduler.add_job(
    scheduled_task,
    CronTrigger(hour=15, minute=0),  # Adjust time as needed
    id="daily_linkedin_post",
    replace_existing=True,
)

scheduler.start()

# Ensure scheduler is gracefully shut down during app shutdown
@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down scheduler...")
    scheduler.shutdown()


@app.post("/generate-post/")
async def generate_post(request: PostRequest):
    try:
        url = f"https://indianexpress.com/section/{request.category}/"
        website_html = fetch_website_content(url)
        article_content = select_and_process_article(website_html, request.prompt)
        summary = generate_summary(article_content)
        image_prompt = f"An illustration related to {summary}."
        image_path = generate_image(image_prompt)
        access_token = linkedin_access_token
        linkedin_response = post_to_linkedin(access_token, article_content, image_path)
        return {
            "message": article_content,
            "linkedin_response": linkedin_response,
            "summary": summary,
            "image_url": image_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/jobs/")
async def list_jobs():
    jobs = scheduler.get_jobs()
    job_details = [
        {
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time,
            "trigger": str(job.trigger),
        }
        for job in jobs
    ]
    return {"active_jobs": job_details}