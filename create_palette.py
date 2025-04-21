import os

def create_default_palette(filename):
    """Create a default C&C-style palette file."""
    colors = [
        (0, 0, 0),    # Transparent
        (63, 0, 0),   # Red
        (0, 63, 0),   # Green
        (0, 0, 63),   # Blue
        (63, 63, 0),  # Yellow
        (63, 0, 63),  # Magenta
        (0, 63, 63),  # Cyan
        (63, 63, 63), # White
    ]
    
    # Add grayscale ramp
    for i in range(8, 64, 8):
        colors.append((i, i, i))
        
    # Add color gradients
    for i in range(32, 64, 8):
        colors.extend([
            (i, 0, 0),
            (0, i, 0),
            (0, 0, i)
        ])
    
    # Fill rest with interpolated colors to reach 256
    while len(colors) < 256:
        colors.append((32, 32, 32))
    
    # Write binary palette file
    with open(filename, 'wb') as f:
        for r, g, b in colors:
            f.write(bytes([r, g, b]))

if __name__ == '__main__':
    os.makedirs('pal', exist_ok=True)
    create_default_palette('pal/unittem.pal') 