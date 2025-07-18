from PIL import Image, ImageDraw, ImageFont
import os

from byteskript_agent.img_gen.card_builder.editor.text_drawer import (
    BGType,
    Color,
    TextLine,
    Position2D,
    Spacing,
    TextDrawer,
)


class ImageGenerator:
    def __init__(
        self,
        canvas_size=(1080, 1350),
        output_dir="generated_templates",
    ):
        self.canvas_size = canvas_size
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def add_bottom_black_fade(self, img, height=300):
        """
        Adds a black gradient overlay that fades out from bottom up.

        Args:
            img: PIL.Image (RGBA)
            height: how tall the fade effect should be

        Returns:
            new image with black fade applied
        """
        w, h = img.size
        fade = Image.new("L", (w, height), color=0)

        print(f"Adding black fade of height {height}")

        for y in range(height):
            opacity = int(255 * (y / height))  # more opaque at bottom
            ImageDraw.Draw(fade).line(
                [(0, height - y - 1), (w, height - y - 1)], fill=255 - opacity
            )

        black_layer = Image.new("RGBA", (w, height), color=(0, 0, 0, 0))
        black_layer.putalpha(fade)

        img.paste(black_layer, (0, h - height), black_layer)
        return img

    def generate_image(self, preset) -> Image.Image:
        """
        Generate an image based on the preset configuration.

        Args:
            preset (dict): Preset configuration
            filename (str): Output filename (without extension)

        Returns:
            str: Path to the generated image
        """

        fonts = preset.get("fonts", {})

        bg_color = preset.get("bg_color", "white")
        img = Image.new("RGB", self.canvas_size, color=bg_color)
        draw = ImageDraw.Draw(img)
        y_cursor = 0

        for layer in preset.get("layers", []):
            layer_type = layer.get("type")

            if layer_type == "image":
                im = layer["image"]
                pos = layer["position"]

                # Resize image while preserving aspect ratio
                if layer.get("resize_to_height", False):
                    # Calculate aspect ratio
                    img_ratio = im.width / im.height
                    canvas_ratio = img.width / img.height
                    
                    if img_ratio > canvas_ratio:
                        # Image is wider than canvas - fit to width
                        new_width = img.width
                        new_height = int(img.width / img_ratio)
                    else:
                        # Image is taller than canvas - fit to height
                        new_height = img.height
                        new_width = int(img.height * img_ratio)
                    
                    im = im.resize((new_width, new_height), Image.Resampling.LANCZOS)

                if pos[1] == "auto":
                    pos = (pos[0], y_cursor + 10)

                if layer.get("from_bottom", False):
                    # Place the image end point at the bottom of the canvas
                    pos = (pos[0], img.height - im.height)

                if layer.get("crop_center_scale", False):
                    # Crop the image to the center and scale it to the canvas size
                    im = im.crop((0, 0, im.width, im.height))
                    im = im.resize((img.width, img.height), Image.Resampling.LANCZOS)

                img.paste(im, pos, im if im.mode == "RGBA" else None)
                pos = (pos[0], pos[1] + (im.height - img.height))

            elif layer_type == "black_fade":
                img = self.add_bottom_black_fade(img, layer["height"])

            elif layer_type == "textbox":
                pos = layer["position"]
                x = pos[0]
                y = pos[1]

                if y == "auto":
                    y = y_cursor + layer.get("auto_y_padding", 0)

                bg_fill = layer.get("bg_fill", (0, 0, 0))
                bg_type = BGType(layer.get("bg_type", "none"))
                padding = layer.get("padding", 0)

                h = (
                    TextDrawer(
                        TextLine(
                            text=layer["text"],
                            position=Position2D(x, y),
                            font=fonts[layer["font"]],
                            max_width=layer["max_width"],
                            line_spacing=layer.get("line_spacing", 5),
                            bg_fill=Color.from_tuple(bg_fill),
                            text_fill=Color.from_tuple(layer["text_fill"]),
                            bg_type=bg_type,
                            padding=Spacing(
                                top=10,
                                bottom=10,
                                left=10,
                                right=10,
                            ),
                        )
                    )
                    .draw(draw)
                    .height
                )

                y_cursor = y + h + padding

        return img



# Example usage
if __name__ == "__main__":
    def get_logo():
        im = Image.open("assets/bs_logo_dark.png")
        im.thumbnail((100, 100))
        return im



    # Example preset configuration
    preset = {
        "bg_color": (244, 244, 244),
        "fonts": {
            "title": ImageFont.truetype("assets/font.ttf", 48),
            "small": ImageFont.truetype("assets/font.ttf", 24),
        },
        "layers": [
            {
                "type": "textbox",
                "font": "title",
                "text": "Bangladeshi Founders Raise $26M to Launch World's First Self-Driving AI CRM",  # This will be replaced with title_text
                "position": (80, 100),
                "max_width": 920,
                "bg_fill": (0, 45, 98),
                "text_fill": (255, 255, 255),
                "padding": 10,
                "bg_type": "solid",
            },
            {
                "type": "textbox",
                "font": "small",
                "text": "Source: The Daily Star | 15th April 2025 | Photo: Generated",  # This will be replaced with source_text
                "position": (70, "auto"),
                "max_width": 960,
                "text_fill": (100, 100, 100),
                "auto_y_padding": 10,
                "bg_type": "none",
            },
            {
                "type": "image",
                "id": "thumbnail",
                "image": Image.new("RGBA", (1080, 1080), (0, 100, 10, 100)),
                "position": (0, "auto"),
                "resize_to_height": True,
            },
            {
                "type": "black_fade",
                "height": 700,
            },
            {
                "type": "image",
                "position": (70, 1200),
                "image": get_logo(),
            },  # Logo position
        ],
    }

    # Create an instance of the generator with font and logo paths
    generator = ImageGenerator()
    generator.generate_image(preset, "template_01")
