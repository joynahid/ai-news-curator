from typing import Optional, Union, List, Dict, Any
from PIL import Image, ImageDraw, ImageFont
import os

from .text_drawer import BGType, Color, TextLine, TextDrawer
from .preset import Preset, ImageLayer, TextboxLayer, LayerT


class ImgComposer:
    """
    A modular image composer for creating layered image compositions.
    
    This class handles the creation of complex image layouts with multiple
    layers including images and text boxes, with automatic positioning
    and text wrapping capabilities.
    """
    
    def __init__(self, preset: Preset, canvas_size: tuple[int, int] = (1080, 1350), output_dir: str = "generated_templates"):
        """
        Initialize the image composer with preset configuration.
        
        Args:
            preset: Preset object containing composition settings
            canvas_size: Size of the output canvas (width, height)
            output_dir: Directory to save output files
        """
        self.preset = preset
        self.canvas_size = canvas_size
        self.output_dir = output_dir
        self._ensure_output_dir()
        self._y_cursor = 0
        
    def _ensure_output_dir(self):
        """Ensure the output directory exists."""
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _process_image_layer(self, layer: ImageLayer, img: Image.Image) -> int:
        """
        Process an image layer and return the height used.
        
        Args:
            layer: ImageLayer to process
            img: Base image to paste onto
            
        Returns:
            Height used by this layer
        """
        im = layer.image.copy()
        pos = layer.position
        
        # Handle resizing
        if layer.resize_to_height:
            im = im.resize((img.width, img.height))
        elif layer.resize_to_width:
            aspect_ratio = im.width / im.height
            new_width = img.width
            new_height = int(new_width / aspect_ratio)
            im = im.resize((new_width, new_height))
        elif layer.max_width or layer.max_height:
            if layer.max_width and layer.max_height:
                im.thumbnail((layer.max_width, layer.max_height))
            elif layer.max_width:
                aspect_ratio = im.width / im.height
                new_width = layer.max_width
                new_height = int(new_width / aspect_ratio)
                im = im.resize((new_width, new_height))
            elif layer.max_height:
                aspect_ratio = im.width / im.height
                new_height = layer.max_height
                new_width = int(new_height * aspect_ratio)
                im = im.resize((new_width, new_height))
        
        # Handle positioning
        if pos[1] == "auto":
            pos = (pos[0], self._y_cursor + layer.auto_y_padding)
        
        # Paste image
        img.paste(im, pos, im if im.mode == "RGBA" else None)
        
        return im.height
    
    def _process_text_layer(self, layer: TextboxLayer, draw: ImageDraw) -> int:
        """
        Process a text layer and return the height used.
        
        Args:
            layer: TextboxLayer to process
            draw: ImageDraw object for drawing
            
        Returns:
            Height used by this layer
        """
        pos = layer.position
        x = pos[0]
        y = pos[1]
        
        if y == "auto":
            y = self._y_cursor + layer.auto_y_padding
        
        # Create TextLine object
        text_line = TextLine(
            text=layer.text,
            position=layer.position,
            font=layer.font,
            max_width=layer.max_width,
            line_spacing=layer.line_spacing,
            bg_fill=Color.from_tuple(layer.bg_fill) if layer.bg_fill else Color(0, 0, 0),
            text_fill=Color.from_tuple(layer.text_fill),
            bg_type=BGType(layer.bg_type),
            padding=layer.padding
        )
        
        # Create TextDrawer and draw
        text_drawer = TextDrawer(text_line)
        size = text_drawer.draw(draw)
        
        return size.height
    
    def compose(self) -> Image.Image:
        """
        Compose the image according to the preset configuration.
        
        Returns:
            Composed PIL Image
        """
        # Create base image
        img = Image.new("RGB", self.canvas_size, color=self.preset.bg_color)
        draw = ImageDraw.Draw(img)
        
        # Reset cursor
        self._y_cursor = 0
        
        # Process each layer
        for layer in self.preset.layers:
            if isinstance(layer, ImageLayer):
                height = self._process_image_layer(layer, img)
                self._y_cursor += height
            elif isinstance(layer, TextboxLayer):
                height = self._process_text_layer(layer, draw)
                self._y_cursor += height + layer.padding
        
        return img
    
    def save(self, filename: str, format: str = "JPEG", **kwargs) -> str:
        """
        Compose and save the image.
        
        Args:
            filename: Name of the output file
            format: Image format (JPEG, PNG, etc.)
            **kwargs: Additional arguments for PIL save method
            
        Returns:
            Full path to the saved file
        """
        img = self.compose()
        filepath = os.path.join(self.output_dir, filename)
        img.save(filepath, format=format, **kwargs)
        return filepath
    
    @classmethod
    def from_preset_dict(cls, preset_dict: Dict[str, Any], canvas_size: tuple[int, int] = (1080, 1350), output_dir: str = "generated_templates") -> "ImgComposer":
        """
        Create an ImgComposer from a preset dictionary.
        
        Args:
            preset_dict: Dictionary containing composition configuration
            canvas_size: Size of the output canvas (width, height)
            output_dir: Directory to save output files
            
        Returns:
            Configured ImgComposer instance
        """
        # Convert layer dictionaries to Layer objects
        layers = []
        for layer_dict in preset_dict.get("layers", []):
            layer_type = layer_dict.get("type")
            
            if layer_type == "image":
                layer = ImageLayer(
                    image=layer_dict["image"],
                    position=layer_dict["position"],
                    resize_to_height=layer_dict.get("resize_to_height", False)
                )
                layers.append(layer)
                
            elif layer_type == "textbox":
                layer = TextboxLayer(
                    text=layer_dict["text"],
                    position=layer_dict["position"],
                    font=layer_dict["font"],
                    max_width=layer_dict.get("max_width", 1000),
                    bg_fill=layer_dict.get("bg_fill"),
                    text_fill=layer_dict["text_fill"],
                    padding=layer_dict.get("padding", 0),
                    bg_type=layer_dict.get("bg_type", "none"),
                    line_spacing=layer_dict.get("line_spacing", 5),
                    auto_y_padding=layer_dict.get("auto_y_padding", 0)
                )
                layers.append(layer)
        
        preset = Preset(
            bg_color=preset_dict.get("bg_color", (244, 244, 244)),
            layers=layers
        )
        
        return cls(preset, canvas_size, output_dir)
