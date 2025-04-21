import numpy as np
from PIL import Image
import logging
from sklearn.cluster import KMeans
import colorsys
from skimage import color

class PaletteHandler:
    def __init__(self):
        self.current_palette = None
        self.palette_colors = None  # numpy array of RGB colors
        self.palette_colors_lab = None  # LAB version of palette colors
        self.transparency_color = None
        self.original_images = {}  # Store original images before palette application
        self.next_image_id = 0  # Counter for generating unique image IDs
        
    def get_image_id(self, img):
        """Generate or retrieve a unique ID for an image."""
        # Try to find existing ID in image metadata
        if hasattr(img, 'palette_handler_id'):
            return img.palette_handler_id
        
        # Create new ID and store it in image metadata
        new_id = f"img_{self.next_image_id}"
        self.next_image_id += 1
        img.palette_handler_id = new_id
        return new_id
    
    def load_palette_from_image(self, palette_image):
        """Load palette from an image.
        
        Args:
            palette_image: Either a file path (str) or a PIL Image object
        """
        try:
            # If palette_image is a string (file path), open it
            if isinstance(palette_image, str):
                print(f"Loading palette from file: {palette_image}")
                palette_image = Image.open(palette_image)
            
            # Convert to RGB mode for consistent color handling
            palette_image = palette_image.convert('RGB')
            
            # Extract unique colors from the image
            colors = np.array(list(set(palette_image.getdata())))
            print(f"Found {len(colors)} unique colors in palette image")
            
            # If more than 256 colors, use k-means to reduce
            if len(colors) > 256:
                print(f"Reducing {len(colors)} colors to 256 using k-means clustering")
                kmeans = KMeans(n_clusters=256, random_state=42)
                kmeans.fit(colors)
                colors = kmeans.cluster_centers_.astype(np.uint8)
            
            # Store RGB colors
            self.palette_colors = colors
            
            # Convert to LAB color space for better matching
            # Normalize RGB values to 0-1 range for skimage
            rgb_norm = colors.astype(float) / 255.0
            # Convert to LAB color space
            self.palette_colors_lab = color.rgb2lab(rgb_norm.reshape(1, -1, 3)).reshape(-1, 3)
            
            print(f"Palette loaded with {len(self.palette_colors)} colors")
            return True
        except Exception as e:
            print(f"Error loading palette: {str(e)}")
            self.palette_colors = None
            self.palette_colors_lab = None
            return False
    
    def set_transparency_color(self, color):
        """Set the transparency color (RGB tuple)."""
        self.transparency_color = tuple(color) if color else None
    
    def clear_palette(self):
        """Remove current palette and transparency color."""
        self.current_palette = None
        self.palette_colors = None
        self.palette_colors_lab = None
        self.transparency_color = None
    
    def apply_palette_to_image(self, img):
        """Convert image to use current palette."""
        try:
            # Get or create unique ID for this image
            img_id = self.get_image_id(img)
            
            # Store original image if not already stored
            if img_id not in self.original_images:
                self.original_images[img_id] = img.copy().convert('RGBA')
                print(f"Stored original image {img_id} in RGBA mode")
            
            # Get original image
            original = self.original_images[img_id]
            result = original.copy()
            
            # Apply transparency if set
            if self.transparency_color:
                img_data = np.array(result)
                rgb_data = img_data[:, :, :3]
                alpha = img_data[:, :, 3]
                
                # Create mask for transparency color
                is_transparent = np.all(rgb_data == self.transparency_color, axis=2)
                alpha[is_transparent] = 0
                
                # Update image with new alpha channel
                img_data[:, :, 3] = alpha
                result = Image.fromarray(img_data)
            
            # If no palette is set, return the image (with transparency applied if any)
            if self.palette_colors is None:
                print("No palette set, returning image with transparency")
                result.palette_handler_id = img_id  # Preserve the ID
                return result
            
            # Convert to LAB space and apply palette
            img_data = np.array(result)
            rgb_data = img_data[:, :, :3].astype(np.float32)  # Ensure float32 type
            alpha = img_data[:, :, 3]
            
            # Normalize RGB values to 0-1 range
            rgb_norm = rgb_data / 255.0
            
            # Reshape for color conversion while preserving alpha
            orig_shape = rgb_norm.shape
            rgb_reshaped = rgb_norm.reshape(-1, 3)
            
            # Convert to LAB space
            lab_data = color.rgb2lab(rgb_reshaped.reshape(-1, 1, 3)).reshape(-1, 3)
            
            # Calculate distances in LAB space
            distances = np.sqrt(((lab_data[:, np.newaxis] - self.palette_colors_lab) ** 2).sum(axis=2))
            closest_indices = np.argmin(distances, axis=1)
            
            # Map to closest palette colors (in RGB space)
            mapped_colors = self.palette_colors[closest_indices]
            
            # Reshape back to image dimensions
            mapped_rgb = mapped_colors.reshape(orig_shape)
            
            # Create output image with alpha channel
            output_data = np.dstack((mapped_rgb, alpha))
            output_image = Image.fromarray(output_data.astype(np.uint8))
            
            # Preserve the image ID
            output_image.palette_handler_id = img_id
            
            print(f"Applied palette to image {img_id} with {len(self.palette_colors)} colors")
            return output_image
            
        except Exception as e:
            print(f"Error applying palette: {str(e)}")
            result = img.copy()
            result.palette_handler_id = self.get_image_id(img)  # Ensure ID is preserved even on error
            return result
            
    def cleanup(self):
        """Clear stored original images to free memory."""
        self.original_images.clear()
        self.next_image_id = 0  # Reset the ID counter 