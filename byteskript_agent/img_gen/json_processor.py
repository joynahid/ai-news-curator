import json
import os
from datetime import datetime
import traceback
from PIL import Image
import requests
from io import BytesIO
from PIL import ImageFont
import replicate

from byteskript_agent.img_gen.openai_img import get_openai_image


def get_logo():
    im = Image.open("assets/bs_logo_dark.png")
    im.thumbnail((100, 100))
    return im


# Example preset configuration
def generate_preset(title_text, source_text, image):
    return {
        "bg_color": (244, 244, 244),
        "fonts": {
            "title": ImageFont.truetype("assets/OpenSauceTwo-Bold.ttf", 48),
            "small": ImageFont.truetype("assets/OpenSauceTwo-Regular.ttf", 24),
        },
        "layers": [
            {
                "type": "textbox",
                "font": "title",
                "text": title_text,  # This will be replaced with title_text
                "position": (80, 100),
                "max_width": 920,
                "bg_fill": (0, 71, 171),
                "text_fill": (255, 255, 255),
                "padding": 10,
                "bg_type": "solid",
            },
            {
                "type": "textbox",
                "font": "small",
                "text": source_text,  # This will be replaced with source_text
                "position": (70, "auto"),
                "max_width": 960,
                "text_fill": (200, 200, 200),
                "auto_y_padding": 10,
                "bg_type": "none",
            },
            {
                "type": "image",
                "id": "thumbnail",
                "image": image,
                "position": (0, "auto"),
                "resize_to_height": True,
                "from_bottom": False,
            },
            {
                "type": "black_fade",
                "height": 500,
            },
            {
                "type": "image",
                "id": "logo",
                "image": get_logo(),
                "position": (70, 1200),
            },  # Logo position
        ],
    }


class NewsDataProcessor:
    def __init__(self, image_generator, on_one_generated):
        """
        Initialize the NewsDataProcessor with an image generator instance.

        Args:
            image_generator: Instance of ImageGenerator class
        """
        self.image_generator = image_generator
        self.on_one_generated = on_one_generated

    def download_image_from_url(self, url, max_size=(800, 800)):
        """
        Download an image from a URL and return it as a PIL Image.

        Args:
            url (str): URL of the image to download
            max_size (tuple): Maximum width and height for the image

        Returns:
            PIL.Image: Downloaded image or a placeholder if download fails
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Open image from bytes
            image = Image.open(BytesIO(response.content))

            # Convert to RGBA if necessary
            if image.mode != "RGBA":
                image = image.convert("RGBA")

            # Resize if larger than max_size while maintaining aspect ratio
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)

            return image

        except Exception as e:
            print(f"Failed to download image from {url}: {e}")
            # Return a placeholder image
            placeholder = Image.new("RGBA", max_size, (200, 200, 200))
            draw = Image.Draw(placeholder)
            draw.text((50, 50), "Image\nNot\nAvailable", fill="black")
            return placeholder

    def generate_image_with_openai(self, title, source_text):
        img_bytes = get_openai_image(title, source_text)
        im = Image.open(BytesIO(img_bytes))
        im.save(f"output_openai_{title}.png")
        return im

    def generate_image_with_replicate(self, title, source_text, image: Image.Image):
        # Convert PIL Image to bytes and create BytesIO object
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format="PNG")
        img_byte_arr.seek(0)

        output = replicate.run(
            "bria/expand-image",
            input={
                "image": img_byte_arr,
                "sync": True,
                "aspect_ratio": "1:1",
                "preserve_alpha": True,
                "content_moderation": False,
            },
        )

        # Handle the output properly - it might be a URL, file path, or FileOutput object
        if isinstance(output, str):
            # If it's a URL, download it
            if output.startswith("http"):
                response = requests.get(output)
                im = Image.open(BytesIO(response.content))
            else:
                # If it's a file path, open it directly
                im = Image.open(output)
        elif hasattr(output, "read"):
            # If it's a FileOutput object or file-like object
            im = Image.open(output)
        else:
            # If it's already bytes or BytesIO
            im = Image.open(BytesIO(output))
        im.save("output.png")
        print(im.size)
        return im

    async def process_data(self, data: list) -> list[Image.Image]:
        """
        Process JSON data containing news items and generate images for each.

        Args:
            json_file_path (str): Path to the JSON file containing news data
            output_prefix (str): Prefix for output filenames

        Returns:
            list: List of generated image paths
        """
        generated_images = []
        for i, news_item in enumerate(data):
            try:
                # Extract data from news item
                title = news_item.get("title", "No Title")
                source = news_item.get("source", "Unknown Source")
                summary = news_item.get("summary", "No Summary Found")
                custom_img = news_item.get("custom_img", None)

                # Create source text with current date
                source_text = f"Source: {source} | {news_item.get('publish_date', datetime.now().strftime('%d %B %Y'))} | Photo: Generated"

                if custom_img:
                    image = custom_img
                else:
                    image = self.generate_image_with_openai(title, summary)

                # Generate the image
                print(f"Generating image {i + 1}/{len(data)}: {title[:50]}...")
                img: Image.Image = self.image_generator.generate_image(
                    preset=generate_preset(title, source_text, image),
                )

                generated_images.append(img)
                await self.on_one_generated(img, news_item)
            except Exception as e:
                traceback.print_exc()
                print(f"Failed to process news item {i + 1}: {e}")
                continue

        print(
            f"Successfully generated {len(generated_images)} images from {len(data)} news items"
        )
        return generated_images


# Example usage
if __name__ == "__main__":
    from gen_img import ImageGenerator

    # Create an instance of the image generator
    generator = ImageGenerator()

    # Create the JSON processor
    processor = NewsDataProcessor(generator, lambda x, y: None)

    title = "On 18 July 2024, Palak Pulls the Plug—Bangladesh Buffers Into Airplane Mode"
    source = "18 July 2025 | Photo: Sora"
    image = Image.open("image.png")

    im = processor.image_generator.generate_image(
        preset=generate_preset(title, source, image)
    )
    im.save("output.png")

    # # Process the JSON file
    # json_file_path = "data.json"
    # if os.path.exists(json_file_path):
    #     print(f"Processing JSON file: {json_file_path}")
    #     generated_paths = processor.process_json_data(
    #         json_file_path, output_prefix="news"
    #     )
    #     print(f"Generated {len(generated_paths)} images successfully!")
    # else:
    #     print(f"JSON file not found: {json_file_path}")


