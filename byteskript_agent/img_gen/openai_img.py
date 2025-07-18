from base64 import b64decode
import os
from openai import OpenAI


IMAGE_PROMPT = """
Without changing any core details, generate a realistic and ultra-clear image inspired by the concept of a news summary. Use the original dimensions—no cropping—and ensure the full body or object is shown, even if the reference image is partial or incomplete. Maintain generous bottom padding and margin wherever possible.

Do not reuse the original image. Instead, recreate it as a fully imagined yet realistic version. If there are texts, ensure they are completely visible, readable, and not broken. If readability can’t be guaranteed, do not include text—instead, use visually creative elements that match the style and feel of a news summary.

Use your creativity and humor. If the news theme allows for it and the tone is light or memeable, feel free to design it with a meme-like feel. Avoid turning serious or sensitive content into memes.

Follow this theme context to guide the visual tone:
<theme>{theme}</theme>
"""

def generate_openai_image_prompt(title: str, summary: str) -> str:
    prompt = """
You are a thumbnail image prompt generator for a tech meme-style news platform.

Your goal is to create a **funny**, **minimalistic**, and **realistic** image that represents the news below. It should feel like a meme thumbnail — clever or ironic — but look like a real photograph.

Guidelines:
- Use a **single object** or **one or two people** according to the news and the person mentioned in the news.
- Do not use any robots in the image if absolutely not needed.
- Feel free to use brand logos, if the news is about a company or product.
- Prefer **objects** that represent the news metaphorically.
- The composition should be **centered**, with **empty space and margin** — clean layout.
- The image must be **photo-realistic**, not surreal or cartoonish.
- Avoid AI-style coloring — no glowing lights, neon gradients, sci-fi effects, or fantasy tones.
- No text, no obvious digital artwork.
- Make it fun and engaging. If it's meme-able, make it meme-able.

Only return the exact image generation prompt, nothing else.

News Title: {title}
News Summary: {summary}
    """.strip()

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI visual designer for ByteSkript with 10+ years of experience in visual design."},
            {"role": "user", "content": prompt.format(title=title, summary=summary)}
        ]
    )

    content = response.choices[0].message.content
    print(content)
    return content

def get_openai_image(title: str, summary: str) -> bytes:
    """Process image using OpenAI API and return processed image bytes"""
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    img_response = client.images.generate(
        prompt=generate_openai_image_prompt(title, summary),
        model="gpt-image-1",
        n=1,
        size="1024x1024",
        quality="medium",
        background="auto",
    )
    return b64decode(img_response.data[0].b64_json)
