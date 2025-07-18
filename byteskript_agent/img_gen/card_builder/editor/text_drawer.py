from dataclasses import dataclass, field
from enum import Enum
from PIL import ImageFont, ImageDraw, Image
import textwrap


@dataclass
class Spacing:
    top: float = 0.0
    bottom: float = 0.0
    left: float = 0.0
    right: float = 0.0

    def __post_init__(self):
        if self.top < 0 or self.bottom < 0 or self.left < 0 or self.right < 0:
            raise ValueError("Spacing values must be non-negative")


@dataclass
class Color:
    r: int
    g: int
    b: int

    @classmethod
    def from_tuple(cls, color_tuple: tuple[int, int, int]) -> "Color":
        return cls(r=color_tuple[0], g=color_tuple[1], b=color_tuple[2])

    def __post_init__(self):
        if (
            self.r < 0
            or self.r > 255
            or self.g < 0
            or self.g > 255
            or self.b < 0
            or self.b > 255
        ):
            raise ValueError("Color values must be between 0 and 255")

    @property
    def hex(self) -> str:
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"


@dataclass
class Position2D:
    x: int = field(default=0)
    y: int = field(default=0)


@dataclass
class Size2D:
    width: float = field(default=0.0)
    height: float = field(default=0.0)


class BGType(Enum):
    NONE = "none"
    SOLID = "solid"


@dataclass
class TextLine:
    text: str
    position: Position2D = field(default_factory=lambda: Position2D())
    margin: Spacing = field(default_factory=lambda: Spacing())
    padding: Spacing = field(default_factory=lambda: Spacing())
    bg_type: BGType = field(default=BGType.NONE)
    bg_fill: Color = field(default_factory=lambda: Color(0, 0, 0))
    text_fill: Color = field(default_factory=lambda: Color(0, 0, 0))
    font: ImageFont.FreeTypeFont = field(
        default_factory=lambda: ImageFont.load_default()
    )
    line_spacing: int = field(default=5)
    max_width: int = field(default=1000)
    uppercase: bool = field(default=False)
    line_height: float = field(default=1.0)

    def __post_init__(self):
        if self.uppercase:
            self.text = self.text.upper()
        if self.line_height < 0:
            raise ValueError("Line height must be non-negative")

class TextDrawer:
    def __init__(
        self,
        line: TextLine,
    ):
        self.line = line

    def _get_text_size(self, text: str, font: ImageFont.FreeTypeFont) -> Size2D:
        """Get the width and height of text."""
        bbox = font.getbbox(text)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        return Size2D(width=width, height=height)

    def _get_line_height(self, font: ImageFont.FreeTypeFont) -> float:
        """Get the recommended line height for the font."""
        # Use font size as a base, or get ascent + descent if available
        try:
            return font.size + 4  # Add some padding
        except Exception:
            return font.getbbox("Ay")[3] - font.getbbox("Ay")[1] + 4

    def _wrap_text(
        self, text: str, font: ImageFont.FreeTypeFont, max_width: int
    ) -> list[str]:
        """Wrap text to fit within max_width."""
        words = text.split()
        lines = []
        line = ""

        for word in words:
            test_line = f"{line} {word}".strip()
            line_size = self._get_text_size(test_line, font)
            if line_size.width <= max_width:
                line = test_line
            else:
                if line:
                    lines.append(line)
                line = word

        if line:
            lines.append(line)

        return lines

    def _draw_line_bg(
        self,
        draw: ImageDraw,
        line: TextLine,
        start_x: int,
        start_y: int,
        line_width: float,
        line_height: float,
    ) -> Size2D:
        bg_x0 = start_x - line.padding.left
        bg_y0 = start_y - line.padding.top
        bg_x1 = start_x + line_width + line.padding.right
        bg_y1 = start_y + line_height + line.padding.bottom
        draw.rectangle((bg_x0, bg_y0, bg_x1, bg_y1), fill=line.bg_fill.hex)
        return Size2D(width=bg_x1 - bg_x0, height=bg_y1 - bg_y0)

    def _draw_text(
        self, draw: ImageDraw, line: TextLine, start_x: int, start_y: int, wrapped_line: str
    ):
        draw.text(
            (start_x, start_y), wrapped_line, font=line.font, fill=line.text_fill.hex
        )

    def _draw_wrapped_text(
        self,
        draw: ImageDraw,
        line: TextLine,
    ) -> int:
        """Draw wrapped text and return the total height used."""
        wrapped_lines = self._wrap_text(line.text, line.font, line.max_width)
        line_height = self._get_line_height(line.font)
        total_height = 0
        current_y = line.position.y

        for i, wrapped_line in enumerate(wrapped_lines):
            line_size = self._get_text_size(wrapped_line, line.font)
            current_text_y = current_y + total_height

            if line.bg_type != BGType.NONE:
                bg_size = self._draw_line_bg(
                    draw,
                    line,
                    line.position.x,
                    current_text_y,
                    line_size.width,
                    line_height,
                )

            self._draw_text(draw, line, line.position.x, current_text_y, wrapped_line)

            # Add the actual background height for this line
            total_height += (
                bg_size.height
                if line.bg_type != BGType.NONE
                else line_size.height
            )

            # Add spacing between lines (but not after the last line)
            if i < len(wrapped_lines) - 1:
                total_height += line.line_spacing

        return Size2D(width=line.max_width, height=total_height)

    def draw(self, draw: ImageDraw) -> Size2D:
        return self._draw_wrapped_text(draw, self.line)
