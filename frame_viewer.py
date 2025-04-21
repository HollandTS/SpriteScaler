import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import logging

class FrameViewer(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.frames = []
        self.current_frame_index = 0
        self.animation_running = False
        self.resize_after_id = None  # For debouncing resize events
        self.zoom_level = 100  # Default zoom level (100%)
        
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
                              bg='gray20')
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
        
        # Zoom frame (right side)
        self.zoom_frame = ttk.Frame(self.controls_frame)
        self.zoom_frame.pack(side="right", padx=5)
        
        # Zoom controls
        ttk.Label(self.zoom_frame, text="Zoom:").pack(side="left", padx=2)
        self.zoom_out = ttk.Button(self.zoom_frame, text="-", width=2, 
                                 command=lambda: self.adjust_zoom(-10))
        self.zoom_out.pack(side="left", padx=2)
        
        self.zoom_var = tk.StringVar(value="100%")
        self.zoom_label = ttk.Label(self.zoom_frame, textvariable=self.zoom_var, width=6)
        self.zoom_label.pack(side="left", padx=2)
        
        self.zoom_in = ttk.Button(self.zoom_frame, text="+", width=2,
                                command=lambda: self.adjust_zoom(10))
        self.zoom_in.pack(side="left", padx=2)
        
        self.zoom_reset = ttk.Button(self.zoom_frame, text="Reset",
                                   command=self.reset_zoom)
        self.zoom_reset.pack(side="left", padx=2)
        
        self.photo_image = None
        self.canvas_image = None
        
        # Store current image display info
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
            if self.frames and self.current_frame_index < len(self.frames):
                self.update_frame_display()
            self.resize_after_id = None
        except Exception as e:
            logging.error(f"Error in delayed resize: {e}")

    def get_image_display_info(self):
        """Calculate the actual display size and position of the image on the canvas."""
        if not self.frames:
            return self.display_info

        frame = self.frames[self.current_frame_index]
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Calculate aspect ratios
        img_ratio = frame.width / frame.height
        canvas_ratio = canvas_width / canvas_height if canvas_height else 1
        
        if canvas_ratio > img_ratio:
            # Canvas is wider than image
            display_height = canvas_height
            display_width = int(display_height * img_ratio)
            x_offset = (canvas_width - display_width) // 2
            y_offset = 0
        else:
            # Canvas is taller than image
            display_width = canvas_width
            display_height = int(display_width / img_ratio)
            x_offset = 0
            y_offset = (canvas_height - display_height) // 2
            
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
            self.frames = frames
            self.current_frame_index = 0
            
            # Reset zoom to 100% when loading new frames
            self.zoom_level = 100
            self.zoom_var.set("100%")
            
            if frames:
                # Initial display
                self.update_frame_display()
                self.update_navigation_state()
        except Exception as e:
            logging.error(f"Error loading frames: {e}")

    def update_frame_display(self):
        """Update the display with the current frame."""
        if not self.frames or self.current_frame_index >= len(self.frames):
            return
            
        try:
            current_frame = self.frames[self.current_frame_index]
            
            # Get canvas dimensions
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1:
                return  # Wait for proper canvas initialization
            
            # Get original image dimensions
            img_width, img_height = current_frame.size
            
            # At 100% zoom, use actual pixel size
            if self.zoom_level == 100:
                new_width = img_width
                new_height = img_height
            else:
                # Calculate base scaling to fit canvas while maintaining aspect ratio
                width_ratio = canvas_width / img_width
                height_ratio = canvas_height / img_height
                base_scale = min(width_ratio, height_ratio)
                
                # Apply zoom factor
                zoom_scale = self.zoom_level / 100.0
                final_scale = base_scale * zoom_scale if self.zoom_level < 100 else zoom_scale
                
                # Calculate new dimensions
                new_width = int(img_width * final_scale)
                new_height = int(img_height * final_scale)
            
            # Resize image if needed
            if new_width != img_width or new_height != img_height:
                resized_image = current_frame.resize((new_width, new_height), Image.NEAREST)
            else:
                resized_image = current_frame
            
            # Update PhotoImage
            self.photo_image = ImageTk.PhotoImage(resized_image)
            
            # Calculate position to center the image
            x = max(0, (canvas_width - new_width) // 2)
            y = max(0, (canvas_height - new_height) // 2)
            
            # Update scrollregion to handle zoomed image
            self.canvas.config(scrollregion=(0, 0, max(canvas_width, new_width), 
                                          max(canvas_height, new_height)))
            
            # Clear canvas and display new image
            self.canvas.delete("all")
            self.canvas.create_image(x, y, anchor="nw", image=self.photo_image)
            
            # Update info label
            self.update_info_label()
            
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
        
        # Get canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Calculate scaling based on zoom level
        if self.zoom_level == 100:
            scale_factor = 1.0
        else:
            # Calculate base scaling to fit canvas
            width_ratio = canvas_width / img_width
            height_ratio = canvas_height / img_height
            base_scale = min(width_ratio, height_ratio)
            scale_factor = base_scale * (self.zoom_level / 100.0) if self.zoom_level < 100 else (self.zoom_level / 100.0)
        
        # Calculate image position and dimensions on canvas
        scaled_width = int(img_width * scale_factor)
        scaled_height = int(img_height * scale_factor)
        image_x = (canvas_width - scaled_width) // 2
        image_y = (canvas_height - scaled_height) // 2
        
        # Check if click is within image bounds
        if (canvas_x < image_x or canvas_x >= image_x + scaled_width or
            canvas_y < image_y or canvas_y >= image_y + scaled_height):
            return 0, 0, False
            
        # Convert canvas coordinates to image coordinates
        img_x = int((canvas_x - image_x) / scale_factor)
        img_y = int((canvas_y - image_y) / scale_factor)
        
        # Ensure coordinates are within image bounds
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
        if event.delta > 0:
            self.adjust_zoom(10)
        else:
            self.adjust_zoom(-10) 