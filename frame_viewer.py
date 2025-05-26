import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import logging
import sys # Import sys for platform check

class FrameViewer(ttk.Frame):
    def set_image_paths(self, image_paths):
        """Set the original file paths for each frame (for filename preservation)."""
        self._image_paths = list(image_paths) if image_paths else []

    def get_image_paths(self):
        """Return the list of original file paths for the loaded frames, if available."""
        return getattr(self, '_image_paths', [None] * len(self.frames))
        
    def __init__(self, parent):
        super().__init__(parent)
        self.frames = []
        self.current_frame_index = 0
        self.animation_running = False
        self.resize_after_id = None  # For debouncing resize events
        self.zoom_level = 100  # Default zoom level (100%)
        
        # Background image for preview (not part of frame data)
        self.bg_image = None # This will store a PIL Image (RGBA)
        # Transparency color for filling transparent pixels if no bg_image is set (e.g., the user-picked background color)
        self.transparency_color = None # This stores an RGB tuple (None means actual transparency)

        # Create main container that will hold both canvas and controls
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill="both", expand=True)
        
        # Create canvas with scrollbars
        self.canvas_frame = ttk.Frame(self.main_container)
        self.canvas_frame.pack(fill="both", expand=True)
        
        # Add scrollbars
        self.h_scrollbar = ttk.Scrollbar(self.canvas_frame, orient="horizontal")
        self.v_scrollbar = ttk.Scrollbar(self.canvas_frame, orient="vertical")
        self.h_scrollbar.pack(side="bottom", fill="x")
        self.v_scrollbar.pack(side="right", fill="y")
        
        # Create canvas with dark gray background for better visibility
        self.canvas = tk.Canvas(self.canvas_frame, 
                              xscrollcommand=self.h_scrollbar.set,
                              yscrollcommand=self.v_scrollbar.set,
                              bg='gray20') # Default background if no bg_image or transparency_color is applied
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Configure scrollbars
        self.h_scrollbar.config(command=self.canvas.xview)
        self.v_scrollbar.config(command=self.canvas.yview)
        
        # Frame info label
        self.info_label = ttk.Label(self.main_container, text="")
        self.info_label.pack(side="bottom", pady=2)
        
        # Controls frame (contains both navigation and zoom)
        self.controls_frame = ttk.Frame(self.main_container)
        self.controls_frame.pack(side="bottom", pady=5, fill="x")
        
        # Navigation frame (left side)
        self.nav_frame = ttk.Frame(self.controls_frame)
        self.nav_frame.pack(side="left", padx=5)
        
        # Navigation buttons
        self.prev_button = ttk.Button(self.nav_frame, text="◀", command=self.prev_frame)
        self.prev_button.pack(side="left", padx=2)

        self.play_button = ttk.Button(self.nav_frame, text="▶", command=self.toggle_animation)
        self.play_button.pack(side="left", padx=2)

        self.next_button = ttk.Button(self.nav_frame, text="▶", command=self.next_frame)
        self.next_button.pack(side="left", padx=2)

        # Frame number entry
        self.frame_var = tk.StringVar(value="1")
        self.frame_entry = ttk.Entry(self.nav_frame, textvariable=self.frame_var, width=5, justify="center")
        self.frame_entry.pack(side="left", padx=(8,2))
        self.frame_entry.bind('<Return>', self.on_frame_entry)
        self.frame_entry.bind('<FocusOut>', self.on_frame_entry)
        self.frame_total_label = ttk.Label(self.nav_frame, text="/ 1")
        self.frame_total_label.pack(side="left", padx=(0,2))

        # Zoom frame (right side)
        self.zoom_frame = ttk.Frame(self.controls_frame)
        self.zoom_frame.pack(side="right", padx=5)
        
        # Zoom controls
        ttk.Label(self.zoom_frame, text="Zoom:").pack(side="left", padx=2)
        self.zoom_out = ttk.Button(self.zoom_frame, text="-", width=2, 
                                 command=lambda: self.adjust_zoom(-10))
        self.zoom_out.pack(side="left", padx=2)
        
        self.zoom_var = tk.StringVar(value="100%") # Initialize here if not done above
        self.zoom_label = ttk.Label(self.zoom_frame, textvariable=self.zoom_var, width=6)
        self.zoom_label.pack(side="left", padx=2)
        
        self.zoom_in = ttk.Button(self.zoom_frame, text="+", width=2,
                                command=lambda: self.adjust_zoom(10))
        self.zoom_in.pack(side="left", padx=2)
        
        self.zoom_reset = ttk.Button(self.zoom_frame, text="Reset",
                                   command=self.reset_zoom)
        self.zoom_reset.pack(side="left", padx=2)
        
        self.photo_image = None # Main image on canvas
        self.bg_photo_image = None # Background image on canvas (for original size drawing)
        
        # Store current image display info (might be redundant with updated display logic)
        self.display_info = {
            'x': 0,
            'y': 0,
            'width': 0,
            'height': 0
        }
        
        # Bind to resize events
        self.canvas.bind('<Configure>', self.on_canvas_resize)
        
        # Bind mouse wheel for zooming
        self.canvas.bind('<Control-MouseWheel>', self.on_mousewheel)  # Windows
        self.canvas.bind('<Control-Button-4>', lambda e: self.adjust_zoom(10))  # Linux
        self.canvas.bind('<Control-Button-5>', lambda e: self.adjust_zoom(-10))  # Linux

    def on_frame_entry(self, event=None):
        if not self.frames:
            return
        try:
            val = int(self.frame_var.get())
            if 1 <= val <= len(self.frames):
                self.current_frame_index = val - 1
                self.update_frame_display()
            else:
                self.frame_var.set(str(self.current_frame_index + 1))
        except Exception:
            self.frame_var.set(str(self.current_frame_index + 1))

    def on_canvas_resize(self, event):
        """Handle canvas resize event with debouncing."""
        # Cancel any pending resize
        if self.resize_after_id:
            self.canvas.after_cancel(self.resize_after_id)
        
        # Schedule a new resize
        self.resize_after_id = self.canvas.after(100, self.delayed_resize)
    
    def delayed_resize(self):
        """Actually perform the resize after debouncing."""
        try:
            # Only update if there are frames loaded
            if self.frames and self.current_frame_index < len(self.frames):
                self.update_frame_display()
            self.resize_after_id = None
        except Exception as e:
            logging.error(f"Error in delayed resize: {e}")

    def get_image_display_info(self):
        """Calculate the actual display size and position of the image on the canvas.
           This method is mostly for internal tracking, not directly used for drawing now.
        """
        if not self.frames:
            return self.display_info

        frame = self.frames[self.current_frame_index]
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            return self.display_info # Return current info if canvas is too small

        # Calculate base scaling to fit canvas while maintaining aspect ratio
        img_width, img_height = frame.size
        width_ratio = canvas_width / img_width
        height_ratio = canvas_height / img_height
        base_scale = min(width_ratio, height_ratio)
        
        # Apply zoom factor
        zoom_scale = self.zoom_level / 100.0
        final_scale = base_scale * zoom_scale if self.zoom_level < 100 else zoom_scale
        
        # Calculate new dimensions
        display_width = int(img_width * final_scale)
        display_height = int(img_height * final_scale)

        # Calculate offset to center the image (with current zoom)
        x_offset = max(0, (canvas_width - display_width) // 2)
        y_offset = max(0, (canvas_height - display_height) // 2)
            
        self.display_info = {
            'x': x_offset,
            'y': y_offset,
            'width': display_width,
            'height': display_height
        }
        return self.display_info

    def load_frames(self, frames):
        """Load new frames and display the first one."""
        try:
            self.frames = [f.convert('RGBA') for f in frames] # Ensure all frames are RGBA
            self.current_frame_index = 0
            # Reset zoom to 100% when loading new frames
            self.zoom_level = 100
            if hasattr(self, 'zoom_var'): # Check if initialized
                self.zoom_var.set("100%")
            else:
                self.zoom_var = tk.StringVar(value="100%") # Initialize if not
            
            # If frames have _image_paths attribute, preserve it; else clear
            if hasattr(frames, '_image_paths'):
                self._image_paths = list(frames._image_paths)
            else:
                # If loading from outside, default to None for paths if not set
                self._image_paths = [None] * len(self.frames) 

            if self.frames:
                # Initial display
                self.update_frame_display()
                self.update_navigation_state()
            else:
                # No frames, clear canvas
                self.canvas.delete("all")
                self.photo_image = None
                self.bg_photo_image = None
                self.update_navigation_state()

            # Update frame entry and total label
            if hasattr(self, 'frame_var'):
                self.frame_var.set(str(self.current_frame_index + 1))
            if hasattr(self, 'frame_total_label'):
                self.frame_total_label.config(text=f"/ {len(self.frames)}")
        except Exception as e:
            logging.error(f"Error loading frames: {e}")

    def update_frame_display(self):
        """Update the display with the current frame and preview background image if set."""
        if not self.frames or self.current_frame_index >= len(self.frames):
            self.canvas.delete("all")
            self.photo_image = None
            self.bg_photo_image = None
            self.update_info_label()
            self.update_navigation_state()
            return
        
        try:
            current_frame = self.frames[self.current_frame_index].copy() # Work on a copy

            # Get canvas dimensions
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            if canvas_width <= 1 or canvas_height <= 1:
                return  # Wait for proper canvas initialization

            # Get original image dimensions of the sprite
            img_width, img_height = current_frame.size

            # Calculate actual display dimensions of the sprite based on zoom level
            display_width = int(img_width * (self.zoom_level / 100.0))
            display_height = int(img_height * (self.zoom_level / 100.0))

            if display_width <= 0 or display_height <= 0:
                logging.warning("Calculated display size of sprite is zero or negative. Skipping render.")
                self.canvas.delete("all")
                self.photo_image = None
                self.bg_photo_image = None
                return

            # Resize the current_frame (sprite) to its display dimensions
            display_sprite_image = current_frame.resize((display_width, display_height), Image.NEAREST)
            display_sprite_image = display_sprite_image.convert("RGBA") # Ensure it's RGBA for compositing

            # --- Compositing Logic ---
            self.canvas.delete("all") # Clear previous content


            # 1. Draw the background image (if set) centered in the canvas
            if self.bg_image:
                bg_img_width, bg_img_height = self.bg_image.size
                # Center the background image in the visible canvas area
                bg_x = (canvas_width - bg_img_width) // 2
                bg_y = (canvas_height - bg_img_height) // 2
                self.bg_photo_image = ImageTk.PhotoImage(self.bg_image.convert("RGBA"))
                self.canvas.create_image(bg_x, bg_y, anchor="nw", image=self.bg_photo_image, tags="bg_image")
                # Set scrollregion to cover the background image if it's larger than canvas
                self.canvas.config(scrollregion=(0, 0, max(canvas_width, bg_img_width), max(canvas_height, bg_img_height)))
            else:
                # If no custom background image, reset scrollregion to cover the sprite or canvas.
                self.canvas.config(scrollregion=(0, 0, max(canvas_width, display_width), max(canvas_height, display_height)))


            # 2. Prepare the sprite image (display_sprite_image) for drawing
            final_sprite_image_for_drawing = display_sprite_image.copy() # Start with the resized sprite RGBA

            # If transparency_color is set (and not None, as during outlining preview),
            # fill transparent parts of the sprite with that color before rendering.
            # This is for the "View Color" checkbox effect.
            if self.transparency_color is not None:
                # Create a solid color background for the sprite based on transparency_color
                sprite_background_solid = Image.new('RGBA', final_sprite_image_for_drawing.size, self.transparency_color + (255,))
                # Composite the sprite onto this solid background
                final_sprite_image_for_drawing = Image.alpha_composite(sprite_background_solid, final_sprite_image_for_drawing)
                # Convert to RGB to flatten alpha, as it's now a solid background color
                final_sprite_image_for_drawing = final_sprite_image_for_drawing.convert('RGB')
            # Else, it remains RGBA, and its transparent parts will show the canvas bg or bg_image.


            # Calculate position to center the sprite image on the *visible canvas area*.
            # This needs to take into account the canvas's current scroll position.
            # `self.canvas.xview()` and `self.canvas.yview()` return (frac_start, frac_end)
            # x_view and y_view are fractions of the total scrollable area.
            
            # The canvas's scroll position is (canvas.xview()[0] * canvas.winfo_width(), canvas.yview()[0] * canvas.winfo_height())
            # We want to center the sprite within the current visible portion of the canvas.
            
            # Calculate where the *center* of the canvas currently is in scrollable coordinates
            center_x_scroll = self.canvas.canvasx(canvas_width / 2) 
            center_y_scroll = self.canvas.canvasy(canvas_height / 2)

            # Position the sprite image so its center aligns with the canvas center
            # sprite image's top-left corner is at (center_x_scroll - half_width, center_y_scroll - half_height)
            x_sprite_draw = center_x_scroll - (display_width / 2)
            y_sprite_draw = center_y_scroll - (display_height / 2)

            self.photo_image = ImageTk.PhotoImage(final_sprite_image_for_drawing)
            self.canvas.create_image(x_sprite_draw, y_sprite_draw, anchor="nw", image=self.photo_image, tags="sprite_image")

            # Update info label
            self.update_info_label()
            # Update frame entry and total label
            self.frame_var.set(str(self.current_frame_index + 1))
            self.frame_total_label.config(text=f"/ {len(self.frames)}")

        except Exception as e:
            logging.error(f"Error updating frame display: {e}")

    def update_info_label(self):
        """Update the information label with current frame details."""
        if self.frames and len(self.frames) > 0:
            current_frame = self.frames[self.current_frame_index]
            info_text = f"Size: {current_frame.width}x{current_frame.height} px | Zoom: {self.zoom_level}%"
            if len(self.frames) > 1:
                info_text += f" | Frame: {self.current_frame_index + 1}/{len(self.frames)}"
            self.info_label.config(text=info_text)

    def update_navigation_state(self):
        """Update the state of navigation buttons."""
        has_frames = bool(self.frames)
        has_multiple_frames = len(self.frames) > 1 if has_frames else False
        
        self.prev_button.config(state="normal" if has_multiple_frames else "disabled")
        self.next_button.config(state="normal" if has_multiple_frames else "disabled")
        self.play_button.config(state="normal" if has_multiple_frames else "disabled")

    def next_frame(self):
        """Show next frame."""
        if self.frames:
            self.current_frame_index = (self.current_frame_index + 1) % len(self.frames)
            self.update_frame_display()

    def prev_frame(self):
        """Show previous frame."""
        if self.frames:
            self.current_frame_index = (self.current_frame_index - 1) % len(self.frames)
            self.update_frame_display()

    def toggle_animation(self):
        """Toggle animation playback."""
        if not self.frames or len(self.frames) <= 1:
            return
            
        self.animation_running = not self.animation_running
        self.play_button.config(text="⏸" if self.animation_running else "▶")
        
        if self.animation_running:
            self.animate()

    def animate(self):
        """Animate through frames."""
        if self.animation_running and self.frames:
            self.next_frame()
            self.after(100, self.animate)  # 100ms delay between frames

    def get_current_frame(self):
        """Return the current frame if available."""
        if self.frames and 0 <= self.current_frame_index < len(self.frames):
            return self.frames[self.current_frame_index]
        return None

    def get_click_image_coordinates(self, canvas_x, canvas_y):
        """Convert canvas coordinates to image coordinates."""
        if not self.frames or self.current_frame_index >= len(self.frames):
            return 0, 0, False
            
        current_frame = self.frames[self.current_frame_index]
        img_width, img_height = current_frame.size
        
        # Get displayed image dimensions and position from get_image_display_info
        display_info = self.get_image_display_info()
        scaled_width = display_info['width']
        scaled_height = display_info['height']
        
        # Adjust canvas_x, canvas_y by the current scroll offsets
        # canvas.canvasx/canvas.canvasy convert a window coordinate to a canvas coordinate
        # The image is drawn at a fixed position relative to the scrollable canvas content,
        # so we need to find its "absolute" position within that content.
        
        # The sprite is centered on the canvas view, so its top-left is at
        # (center_x_scroll - half_sprite_width, center_y_scroll - half_sprite_height)
        canvas_center_x = self.canvas.canvasx(self.canvas.winfo_width() / 2)
        canvas_center_y = self.canvas.canvasy(self.canvas.winfo_height() / 2)
        
        image_x_on_canvas_scrollable = canvas_center_x - (scaled_width / 2)
        image_y_on_canvas_scrollable = canvas_center_y - (scaled_height / 2)

        # Convert click coordinates to the coordinate system of the scrollable canvas
        click_x_scrollable = self.canvas.canvasx(canvas_x)
        click_y_scrollable = self.canvas.canvasy(canvas_y)

        # Calculate click position relative to the top-left of the sprite image
        rel_x = click_x_scrollable - image_x_on_canvas_scrollable
        rel_y = click_y_scrollable - image_y_on_canvas_scrollable

        # Check if click is within scaled image bounds
        if not (0 <= rel_x < scaled_width and 0 <= rel_y < scaled_height):
            return 0, 0, False
            
        # Convert relative scaled coordinates to original image coordinates
        zoom_factor = scaled_width / img_width if img_width else 1
        img_x = int(rel_x / zoom_factor)
        img_y = int(rel_y / zoom_factor)
        
        # Ensure coordinates are within original image bounds
        img_x = max(0, min(img_x, img_width - 1))
        img_y = max(0, min(img_y, img_height - 1))
        
        return img_x, img_y, True

    def adjust_zoom(self, delta):
        """Adjust zoom level by delta percent."""
        new_zoom = max(10, min(500, self.zoom_level + delta))  # Limit zoom between 10% and 500%
        if new_zoom != self.zoom_level:
            self.zoom_level = new_zoom
            self.zoom_var.set(f"{self.zoom_level}%")
            self.update_frame_display()
    
    def reset_zoom(self):
        """Reset zoom to 100%."""
        self.zoom_level = 100
        self.zoom_var.set("100%")
        self.update_frame_display()
    
    def on_mousewheel(self, event):
        """Handle mousewheel events for zooming."""
        # Normalize event.delta across platforms
        if sys.platform == "darwin":
            # For macOS, event.delta is typically +/-1
            delta = event.delta
        else:
            # For Windows/Linux, event.delta is typically +/-120
            delta = int(event.delta / 120)

        if event.state & 0x4: # Check for Control key (Modifier key 0x4)
            if delta > 0:
                self.adjust_zoom(10)
            else:
                self.adjust_zoom(-10)
        else: # Regular scrolling
            # If mouse wheel is not with control key, scroll the canvas
            self.canvas.yview_scroll(-1 * delta, "units")