import numpy as np
from PIL import Image
import logging
from sklearn.cluster import KMeans
import colorsys
from skimage import color

class PaletteHandler:
    def adjust_hsv_in_image(self, img, target_color, tolerance=30, hue_shift=0.0, sat_shift=0.0, bri_shift=0.0, sharpness=1.0, contrast=0.0):
        """Shift hue/saturation/brightness/contrast/sharpness of all pixels within tolerance of target_color, vectorized for performance.
        Transparency color (if set) is always preserved and not altered.
        Sharpness and contrast only affect the selected color region (tolerance mask)."""
        import numpy as np
        from PIL import Image
        arr = np.array(img.convert('RGBA'))
        r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
        # Convert image and target color to HSV
        rgb_img = np.stack([r, g, b], axis=-1).astype(np.float32) / 255.0
        hsv_img = color.rgb2hsv(rgb_img)
        tr, tg, tb = target_color
        target_rgb = np.array([[tr / 255.0, tg / 255.0, tb / 255.0]])
        target_hsv = color.rgb2hsv(target_rgb)[0]
        # Compute hue distance (circular)
        hue_img = hsv_img[..., 0] * 360.0
        target_hue = target_hsv[0] * 360.0
        hue_dist = np.abs(hue_img - target_hue)
        hue_dist = np.minimum(hue_dist, 360.0 - hue_dist)  # wraparound
        # Optionally, also check S/V distance (less important, but helps with edge cases)
        sat_img = hsv_img[..., 1]
        val_img = hsv_img[..., 2]
        sat_dist = np.abs(sat_img - target_hsv[1])
        val_dist = np.abs(val_img - target_hsv[2])
        # Main mask: within hue tolerance (tolerance is in degrees, 0-1000 maps to 0-180)
        hue_tol = np.clip(tolerance, 0, 1000) * 0.18  # 0-180 degrees
        mask = (hue_dist <= hue_tol) & (sat_dist < 0.4) & (val_dist < 0.4)
        # If a transparency color is set, exclude those pixels from the mask
        transparency_color = getattr(self, 'transparency_color', None)
        if transparency_color is not None:
            tcr, tcg, tcb = transparency_color
            ttol = int(getattr(self, 'transparency_tolerance', 0))
            if ttol <= 0:
                transparency_mask = (r == tcr) & (g == tcg) & (b == tcb)
            else:
                # Per-channel tolerance (L-inf distance)
                transparency_mask = (np.abs(r - tcr) <= ttol) & (np.abs(g - tcg) <= ttol) & (np.abs(b - tcb) <= ttol)
            mask = mask & (~transparency_mask)
        # Flatten mask and indices for masked pixels
        idxs = np.where(mask)
        if idxs[0].size == 0:
            return Image.fromarray(arr)
        # Extract masked RGB pixels and normalize
        rgb_masked = np.stack([r[idxs], g[idxs], b[idxs]], axis=1) / 255.0
        # Convert RGB to HSV (vectorized)
        import colorsys
        def rgb_to_hsv_vec(rgb):
            return np.array([colorsys.rgb_to_hsv(*pix) for pix in rgb])
        def hsv_to_rgb_vec(hsv):
            return np.array([colorsys.hsv_to_rgb(*pix) for pix in hsv])
        hsv_masked = rgb_to_hsv_vec(rgb_masked)
        # Apply shifts
        hsv_masked[:, 0] = (hsv_masked[:, 0] + hue_shift / 360.0) % 1.0
        hsv_masked[:, 1] = np.clip(hsv_masked[:, 1] + sat_shift, 0.0, 1.0)
        hsv_masked[:, 2] = np.clip(hsv_masked[:, 2] + bri_shift, 0.0, 1.0)
        # Apply contrast to value channel ([-1,1], 0=no change)
        if contrast != 0.0:
            hsv_masked[:, 2] = np.clip((hsv_masked[:, 2] - 0.5) * (1 + contrast) + 0.5, 0.0, 1.0)
        # Convert back to RGB
        rgb_new = (hsv_to_rgb_vec(hsv_masked) * 255).astype(np.uint8)
        # --- Apply sharpness to only the masked region ---
        # Always apply sharpness, even if 1.0 (so it can be reset)
        from PIL import ImageEnhance
        mask_img = np.zeros(arr.shape, dtype=np.uint8)
        mask_img[..., 0] = 0
        mask_img[..., 1] = 0
        mask_img[..., 2] = 0
        mask_img[..., 3] = 0
        mask_img[idxs[0], idxs[1], 0] = rgb_new[:, 0]
        mask_img[idxs[0], idxs[1], 1] = rgb_new[:, 1]
        mask_img[idxs[0], idxs[1], 2] = rgb_new[:, 2]
        mask_img[idxs[0], idxs[1], 3] = a[idxs]
        region_img = Image.fromarray(mask_img, mode='RGBA')
        region_rgb = region_img.convert('RGB')
        region_enhanced = ImageEnhance.Sharpness(region_rgb).enhance(sharpness)
        region_enhanced = region_enhanced.convert('RGBA')
        # Only update the masked region
        region_arr = np.array(region_enhanced)
        rgb_new = np.stack([
            region_arr[idxs[0], idxs[1], 0],
            region_arr[idxs[0], idxs[1], 1],
            region_arr[idxs[0], idxs[1], 2]
        ], axis=1)
        # Update only masked pixels
        arr[idxs[0], idxs[1], 0] = rgb_new[:, 0]
        arr[idxs[0], idxs[1], 1] = rgb_new[:, 1]
        arr[idxs[0], idxs[1], 2] = rgb_new[:, 2]
        return Image.fromarray(arr)
    def replace_color_in_image(self, img, target_color, replacement_color, tolerance=30):
        """Replace all pixels in img close to target_color with replacement_color, within tolerance."""
        try:
            arr = np.array(img.convert('RGBA'))
            r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
            tr, tg, tb = target_color
            mask = (np.abs(r - tr) <= tolerance) & (np.abs(g - tg) <= tolerance) & (np.abs(b - tb) <= tolerance)
            arr[..., 0][mask] = replacement_color[0]
            arr[..., 1][mask] = replacement_color[1]
            arr[..., 2][mask] = replacement_color[2]
            return Image.fromarray(arr)
        except Exception as e:
            print(f"Error in replace_color_in_image: {e}")
            return img
    def __init__(self):
        self.current_palette = None
        self.palette_colors = None  # numpy array of RGB colors
        self.palette_colors_lab = None  # LAB version of palette colors
        self.transparency_color = None
        # Transparency tolerance in 0..255 (per-channel absolute tolerance)
        self.transparency_tolerance = 0
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
                ttol = int(getattr(self, 'transparency_tolerance', 0))
                if ttol <= 0:
                    is_transparent = np.all(rgb_data == self.transparency_color, axis=2)
                else:
                    # Per-channel tolerance
                    diffs = np.abs(rgb_data.astype(int) - np.array(self.transparency_color, dtype=int))
                    is_transparent = np.all(diffs <= ttol, axis=2)
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