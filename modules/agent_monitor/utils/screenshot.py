"""Screenshot utilities for capturing TUI state."""

import subprocess
from datetime import datetime
from pathlib import Path


def take_screenshot(console, screenshot_dir: Path, title: str = "Albedo Agent Monitor") -> tuple[bool, Path | None, Path | None]:
    """
    Take a screenshot of the current Rich console state.

    Args:
        console: Rich Console instance
        screenshot_dir: Directory to save screenshots
        title: Title for the screenshot

    Returns:
        Tuple of (success: bool, svg_path: Optional[Path], png_path: Optional[Path])
    """
    # Ensure screenshot directory exists
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    svg_path = screenshot_dir / f"tui-{timestamp}.svg"
    png_path = screenshot_dir / f"tui-{timestamp}.png"

    try:
        # Export to SVG (always works, no dependencies)
        svg_content = console.export_svg(title=title)
        svg_path.write_text(svg_content)

        # Try to convert to PNG if ImageMagick is available
        png_converted = False
        if check_imagemagick_available():
            try:
                subprocess.run(
                    [
                        "convert",
                        "-background", "black",
                        "-density", "150",
                        str(svg_path),
                        str(png_path)
                    ],
                    check=True,
                    capture_output=True,
                    timeout=10
                )
                png_converted = True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                png_converted = False

        if png_converted:
            return True, svg_path, png_path
        else:
            return True, svg_path, None

    except Exception:
        return False, None, None


def check_imagemagick_available() -> bool:
    """
    Check if ImageMagick's convert command is available.

    Returns:
        True if ImageMagick is installed, False otherwise
    """
    try:
        result = subprocess.run(
            ["convert", "-version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_screenshot_info(screenshot_dir: Path) -> dict:
    """
    Get information about existing screenshots.

    Args:
        screenshot_dir: Directory containing screenshots

    Returns:
        Dictionary with screenshot counts and total size
    """
    if not screenshot_dir.exists():
        return {"count": 0, "total_size_mb": 0.0}

    svg_files = list(screenshot_dir.glob("*.svg"))
    png_files = list(screenshot_dir.glob("*.png"))

    total_size = sum(f.stat().st_size for f in svg_files + png_files)
    total_size_mb = total_size / (1024 * 1024)

    return {
        "count": len(svg_files) + len(png_files),
        "svg_count": len(svg_files),
        "png_count": len(png_files),
        "total_size_mb": round(total_size_mb, 2)
    }
