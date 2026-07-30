"""Take a screenshot of the current screen using Pillow."""
try:
    from PIL import ImageGrab
    img = ImageGrab.grab()
    img.save("screenshot.png")
    print("Screenshot saved to screenshot.png")
except ImportError:
    print("Pillow not installed. Run: pip install Pillow")
except Exception as e:
    print(f"Error: {e}")
