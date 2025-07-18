from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union, Literal, Tuple

from PIL import Image, ImageFont


class LayerType(Enum):
    IMAGE = "image"
    TEXTBOX = "textbox"
    SHAPE = "shape"
    BACKGROUND = "background"


# Type aliases for better readability
PositionT = Union[Tuple[int, int], Tuple[int, Literal["auto"]]]
ColorTuple = Tuple[int, int, int]


@dataclass
class ImageLayer:
    """Represents an image layer in a preset"""

    type: Literal["image"] = "image"
    image: Image.Image = field()
    position: PositionT = field()
    resize_to_height: bool = field(default=False)


@dataclass
class TextboxLayer:
    """Represents a textbox layer in a preset"""

    type: Literal["textbox"] = "textbox"
    text: str = field()
    position: PositionT = field()
    font: ImageFont.FreeTypeFont = field()
    max_width: int = field()
    text_fill: ColorTuple = field()
    bg_fill: Optional[ColorTuple] = field(default=None)
    bg_type: str = field(default="none")
    padding: int = field(default=0)
    auto_y_padding: int = field(default=0)
    line_spacing: int = field(default=5)


LayerT = Union[ImageLayer, TextboxLayer]


@dataclass
class Preset:
    """Represents a complete preset configuration"""

    bg_color: ColorTuple = field(default=(255, 255, 255))
    layers: list[LayerT] = field(default_factory=list)


# Example preset matching the structure from gen_img.py
def create_default_preset() -> Preset:
    """Create a default preset similar to the one in gen_img.py"""
    # This would typically load actual resources
    logo = Image.new("RGBA", (150, 150), (200, 200, 200))
    font = ImageFont.load_default()
    small_font = ImageFont.load_default()

    return Preset(
        bg_color=(244, 244, 244),
        layers=[
            ImageLayer(image=logo, position=(70, 60)),
            TextboxLayer(
                text="Sample Title Text. AI Just got a lot more interesting. It's fucking scary. AND Humorous.",
                position=(80, 220),
                font=font,
                max_width=920,
                bg_fill=(0, 45, 98),
                text_fill=(255, 255, 255),
                padding=10,
                bg_type="solid",
            ),
            TextboxLayer(
                text="Source: Example Source | Date: July 10th, 2025",
                position=(70, "auto"),
                font=small_font,
                max_width=960,
                text_fill=(128, 128, 128),
                auto_y_padding=10,
                bg_type="none",
            ),
            ImageLayer(
                image=Image.new("RGBA", (800, 800), (200, 200, 200)),
                position=(0, "auto"),
                resize_to_height=True,
            ),
        ],
    )
