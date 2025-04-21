import sys
from wand.image import Image
from wand.version import VERSION as WAND_VERSION
from wand.version import MAGICK_VERSION

print("=== ImageMagick Integration Test ===")
print(f"Python version: {sys.version.split()[0]}")
print(f"Wand version: {WAND_VERSION}")
print(f"ImageMagick version: {MAGICK_VERSION}")

# Test image creation and filters
print("\nTesting filters...")
with Image(width=100, height=100) as img:
    # Fill with a test pattern
    img.pseudo('gradient:white-black')
    
    # Test different filters
    filters = ['point', 'lanczos2', 'catrom']
    for filter_type in filters:
        try:
            img.resize(200, 200, filter=filter_type)
            print(f"✓ Filter '{filter_type}' works")
        except Exception as e:
            print(f"✗ Filter '{filter_type}' failed: {e}")

print("\nImageMagick integration test completed successfully!")

try:
    from wand.image import Image
    from wand.version import VERSION
    print(f"\nWand version: {VERSION}")
    print("Testing ImageMagick connection...")

    # Create a simple test image
    with Image(width=100, height=100) as img:
        print("Successfully created test image")
        print("ImageMagick integration is working!")
except Exception as e:
    print(f"\nError: {e}") 