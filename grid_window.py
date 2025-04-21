import tkinter as tk
from tkinter import Frame, Label, Button, Scale, Scrollbar, Canvas, filedialog, messagebox
import logging
import os
from PIL import Image, ImageTk
import image_grid_utils as utils

class GridWindow(Frame):
    def __init__(self, parent, config, app):
        try:
            logging.info("Initializing GridWindow")
            super().__init__(parent)
            self.app = app
            self.images = {}  # filename -> PIL Image
            self.images_data = {}  # filename -> data dict
            self.thumbnails = {}  # filename -> PhotoImage
            self.image_positions = {}  # index -> (x, y)
            self.selection_boxes = {}  # index -> canvas item id
            self.selected_items = set()  # indices of selected items
            self.thumbnail_size = tk.IntVar(value=64)
            self.grid_size = self.thumbnail_size.get()
            self._setup_ui()
            self.load_images_from_config(config)
        except Exception as e:
            logging.error(f"Error initializing GridWindow: {e}", exc_info=True)

    def _setup_ui(self):
        """Creates the UI elements for the file panel."""
        logging.debug("Setting up GridWindow UI")

        # --- Top Control Bar ---
        control_frame = Frame(self)
        control_frame.pack(side="top", fill="x", pady=5, padx=5)
        thumb_size_label = Label(control_frame, text="Thumbnail Size:")
        thumb_size_label.pack(side="left", padx=(0, 2))
        thumb_size_slider = Scale(control_frame, from_=32, to=256, orient=tk.HORIZONTAL, length=150,
                                  variable=self.thumbnail_size, command=self.apply_thumbnail_size)
        thumb_size_slider.pack(side="left", padx=(0, 10))
        load_image_button = Button(control_frame, text="Load Files", command=self.load_images_dialog)
        load_image_button.pack(side="left", padx=5)
        delete_button = Button(control_frame, text="Delete Selected", command=self.delete_selected_files)
        delete_button.pack(side="left", padx=5)

        # --- Scrollable Area ---
        scroll_frame = Frame(self, bd=1, relief="sunken")
        scroll_frame.pack(side="top", fill="both", expand=True, padx=5, pady=(0,5))
        v_scrollbar = Scrollbar(scroll_frame, orient="vertical")
        v_scrollbar.pack(side="right", fill="y")
        self.canvas = Canvas(scroll_frame, bd=0, highlightthickness=0, yscrollcommand=v_scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        v_scrollbar.config(command=self.canvas.yview)
        self.inner_frame = Frame(self.canvas) # Holds the items
        self.inner_frame_id = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw", tags="inner_frame")

        # --- Bindings for Scrolling and Resize ---
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.inner_frame.bind('<Configure>', self._on_inner_frame_configure)

    def _on_canvas_configure(self, event):
        """Handle canvas resize."""
        try:
            if event.width != self.canvas.winfo_width():
                self.canvas.itemconfig(self.inner_frame_id, width=event.width)
                self.redraw_grid()
        except Exception as e:
            logging.error(f"Error in canvas configure: {e}", exc_info=True)

    def _on_inner_frame_configure(self, event):
        """Update scroll region when inner frame changes."""
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception as e:
            logging.error(f"Error in inner frame configure: {e}", exc_info=True)

    def load_images_dialog(self):
        """Open file dialog and load selected files."""
        try:
            files = filedialog.askopenfilenames(
                title="Select Files",
                filetypes=[
                    ("All Supported", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"),
                    ("Images", "*.png;*.jpg;*.jpeg;*.bmp"),
                    ("GIF Files", "*.gif"),
                    ("All Files", "*.*")
                ]
            )
            if files:
                self.load_images(files)
        except Exception as e:
            logging.error(f"Error in load images dialog: {e}", exc_info=True)

    def load_images(self, file_paths):
        """Load files from the given paths."""
        try:
            for path in file_paths:
                if path not in self.images_data:
                    try:
                        # Use app's load_file method which handles GIF
                        img = self.app.load_file(path)
                        if img:
                            self.images_data[path] = {
                                'pil_image': img,
                                'thumbnail': None
                            }
                    except Exception as e:
                        logging.error(f"Error loading file {path}: {e}", exc_info=True)
            self.redraw_grid()
        except Exception as e:
            logging.error(f"Error in load files: {e}", exc_info=True)

    def load_images_from_config(self, config):
        """Load images from paths stored in config."""
        try:
            if config and "images" in config:
                existing_paths = [p for p in config["images"] if os.path.exists(p)]
                if existing_paths:
                    self.load_images(existing_paths)
                    logging.info(f"Loaded {len(existing_paths)} images from config.")
                if len(existing_paths) != len(config["images"]):
                    logging.warning(f"Some config images missing ({len(existing_paths)}/{len(config['images'])})")
        except Exception as e:
            logging.error(f"Error loading config images: {e}", exc_info=True)

    def get_image_paths(self):
        """Get list of currently loaded file paths."""
        return list(self.images_data.keys())

    def apply_thumbnail_size(self, *args):
        """Update thumbnail size and redraw grid."""
        try:
            self.grid_size = self.thumbnail_size.get()
            self.redraw_grid()
        except Exception as e:
            logging.error(f"Error applying thumbnail size: {e}", exc_info=True)

    def redraw_grid(self):
        """Redraw the image grid with current settings."""
        try:
            utils.clear_grid(self)
            if self.images_data:
                utils.create_thumbnails(self)
                utils.layout_grid(self)
                utils.update_selection(self)
        except Exception as e:
            logging.error(f"Error redrawing grid: {e}", exc_info=True)

    def delete_selected_files(self):
        """Remove selected files from the grid."""
        try:
            if not self.selected_items:
                messagebox.showinfo("Delete", "No items selected")
                return
            
            indices_to_remove = sorted(self.selected_items, reverse=True)
            paths_to_remove = []
            
            for idx in indices_to_remove:
                for path, data in self.images_data.items():
                    if data.get('index') == idx:
                        paths_to_remove.append(path)
                        break
            
            for path in paths_to_remove:
                if path in self.images_data:
                    del self.images_data[path]
            
            self.selected_items.clear()
            self.redraw_grid()
            logging.info(f"Deleted {len(paths_to_remove)} items")
            
        except Exception as e:
            logging.error(f"Error deleting files: {e}", exc_info=True)
            messagebox.showerror("Error", f"Delete failed: {e}")

    def on_item_click(self, event, index):
        """Handle click on grid item."""
        try:
            ctrl_click = (event.state & 0x0004) != 0
            if ctrl_click:
                if index in self.selected_items:
                    self.selected_items.remove(index)
                else:
                    self.selected_items.add(index)
            else:
                self.selected_items.clear()
                self.selected_items.add(index)
                
                # Find the file path for this index
                for path, data in self.images_data.items():
                    if data.get('index') == index:
                        # Reload the file to get all frames
                        self.app.load_file(path)
                        break
                        
            utils.update_selection(self)
        except Exception as e:
            logging.error(f"Error in item click: {e}", exc_info=True) 