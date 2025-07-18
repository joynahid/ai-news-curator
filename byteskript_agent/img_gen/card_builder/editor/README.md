# Image Composer Module

This module provides a clean, modular approach to creating layered image compositions with text and images.

## Overview

The `ImgComposer` class encapsulates the image composition logic from the original `gen_img.py` script into a reusable, object-oriented design. It supports:

- Multiple layer types (images and text)
- Automatic positioning with "auto" y-coordinates
- Text wrapping and styling
- Image resizing and positioning
- Background colors and padding
- Modular configuration

## Classes

### ImgComposer

The main class for creating image compositions.

```python
from card_builder.editor.img_composer import ImgComposer
from card_builder.editor.preset import Preset, ImageLayer, TextboxLayer
```

#### Methods

- `__init__(preset: Preset, canvas_size: tuple[int, int] = (1080, 1350), output_dir: str = "generated_templates")`: Initialize with preset configuration
- `compose() -> Image.Image`: Create the composed image
- `save(filename: str, format: str = "JPEG", **kwargs) -> str`: Compose and save image
- `from_preset_dict(preset_dict: Dict[str, Any], canvas_size: tuple[int, int] = (1080, 1350), output_dir: str = "generated_templates") -> ImgComposer`: Create from preset dictionary

### Preset Classes

The composer uses dataclasses from `preset.py` for configuration:

#### Preset

Main preset configuration dataclass.

```python
@dataclass
class Preset:
    bg_color: ColorTuple = field(default=(255, 255, 255))
    layers: list[LayerT] = field(default_factory=list)
```

#### ImageLayer

For placing images in the composition.

```python
@dataclass
class ImageLayer:
    type: Literal["image"] = "image"
    image: Image.Image = field()
    position: PositionT = field()
    resize_to_height: bool = field(default=False)
```

#### TextboxLayer

For placing text boxes in the composition.

```python
@dataclass
class TextboxLayer:
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
```

## Usage Examples

### Basic Usage

```python
from PIL import Image, ImageFont
from card_builder.editor.img_composer import ImgComposer, CompositionConfig, ImageLayer, TextLayer

# Load resources
logo = Image.open("assets/logo.png")
font = ImageFont.truetype("assets/font.ttf", 48)

# Create preset
preset = Preset(bg_color=(244, 244, 244))

# Add layers
preset.layers = [
    ImageLayer(
        image=logo,
        position=(70, 60)
    ),
    TextboxLayer(
        text="Your title here",
        position=(80, 220),
        font=font,
        max_width=920,
        bg_fill=(0, 45, 98),
        text_fill=(255, 255, 255),
        bg_type="solid"
    )
]

# Create and save
composer = ImgComposer(preset, canvas_size=(1080, 1350))
output_path = composer.save("output.jpg")
```

### Using Preset Dictionary

```python
preset = {
    "bg_color": (244, 244, 244),
    "layers": [
        {
            "type": "image",
            "image": logo,
            "position": (70, 60)
        },
        {
            "type": "textbox",
            "text": "Your title here",
            "position": (80, 220),
            "font": font,
            "max_width": 920,
            "bg_fill": (0, 45, 98),
            "text_fill": (255, 255, 255),
            "bg_type": "solid"
        }
    ]
}

composer = ImgComposer.from_preset_dict(preset)
output_path = composer.save("output.jpg")
```

## Features

### Automatic Positioning

Use `"auto"` for y-coordinates to automatically position layers:

```python
TextboxLayer(
    text="This will be positioned automatically",
    position=(70, "auto"),  # x=70, y=auto
    font=my_font,
    max_width=920,
    text_fill=(0, 0, 0),
    auto_y_padding=10
)
```

### Image Resizing

Multiple options for image resizing:

```python
ImageLayer(
    type="image",
    image=my_image,
    position=(0, 0),
    resize_to_height=True,  # Resize to full canvas height
    # OR
    resize_to_width=True,   # Resize to full canvas width
    # OR
    max_width=800,          # Resize to max width
    max_height=600          # Resize to max height
)
```

### Text Styling

Rich text styling options:

```python
TextboxLayer(
    text="Styled text",
    font=my_font,
    max_width=920,
    bg_fill=(0, 45, 98),      # Background color
    text_fill=(255, 255, 255), # Text color
    padding=10,                # Background padding
    bg_type="solid",           # Background type: "solid" or "none"
    line_spacing=5             # Space between lines
)
```

## Migration from gen_img.py

The new `ImgComposer` class maintains the same functionality as the original `gen_img.py` script but with improved modularity:

1. **Separation of Concerns**: Configuration, layer processing, and image creation are separated
2. **Reusability**: The same composer can be used for multiple images
3. **Type Safety**: Strong typing with dataclasses
4. **Extensibility**: Easy to add new layer types
5. **Clean API**: Clear, documented methods and classes

See `example_composer_usage.py` for a complete migration example. 