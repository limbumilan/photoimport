import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import os
import sys
from pathlib import Path

class App(ctk.CTk):
    def __init__(self):
        super().__init__()        # Set appearance mode and default color theme
        ctk.set_appearance_mode("system")  # Options: "light", "dark", "system"
        ctk.set_default_color_theme("blue")  # Options: "blue", "green", "dark-blue"

        self.title("My CustomTkinter Application")
        self.geometry("800x600")
        
        # Set background color
        self.configure(fg_color="#e8e8e8")  # Dynamic background color

        # Configure grid layout (4x4) for better responsiveness
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.grid_rowconfigure((0, 1, 2, 3), weight=1)

        # Create assets directory if it doesn't exist
        assets_dir = Path("assets")
        assets_dir.mkdir(exist_ok=True)

        # Store references to images to prevent garbage collection
        self._image_references = []
        
        # Create all widgets and components
        self.create_widgets()
        
    def create_widgets(self):
        """Create and place all widgets"""
        self.button_1764973454776 = ctk.CTkButton(self, text="Button", width=120, height=40, corner_radius=8, fg_color="#ffffff", hover_color="#cccccc", text_color="#000000", border_width=1, border_color="#e2e8f0", font=("Arial", 12, "normal"))
        self.button_1764973454776.place(x=47, y=451)
        self.frame_1764973566297 = ctk.CTkFrame(self, width=786, height=560, corner_radius=8, fg_color="#ffffff", border_width=1, border_color="#0e0a1a")
        self.frame_1764973566297.place(x=12, y=0)
        self.button_1764973644060 = ctk.CTkButton(self, text="Button", width=120, height=40, corner_radius=8, fg_color="#ffffff", hover_color="#cccccc", text_color="#000000", border_width=1, border_color="#e2e8f0", font=("Arial", 12, "normal"))
        self.button_1764973644060.place(x=62, y=441)

    def load_image(self, path, size):
        """Load an image, resize it and return as CTkImage"""
        try:
            # Handle path as string or Path object
            path_str = str(path)
            
            # Check if image file exists
            if os.path.exists(path_str):
                img = Image.open(path_str)
                img = img.resize(size, Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
                self._image_references.append(ctk_img)  # Keep reference
                return ctk_img
            else:
                print(f"Image file not found: {path_str}")
                # Use placeholder image
                placeholder_path = "assets/placeholder.png"
                if os.path.exists(placeholder_path):
                    img = Image.open(placeholder_path)
                    img = img.resize(size, Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS)
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
                    self._image_references.append(ctk_img)
                    return ctk_img
                else:
                    # Create a fallback colored rectangle
                    img = Image.new('RGB', size, color='#3B82F6')  # Blue color as placeholder
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
                    self._image_references.append(ctk_img)
                    return ctk_img
        except Exception as e:
            print(f"Error loading image '{path}': {e}")
            # Create a colored rectangle with error indication
            try:
                img = Image.new('RGB', size, color='#FF5555')  # Red color for error
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
                self._image_references.append(ctk_img)
                return ctk_img
            except Exception as e2:
                print(f"Failed to create error placeholder: {e2}")
                # Last resort - return None and let CustomTkinter handle it
                return None


if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        print(f"Error running application: {e}")
        import traceback
        traceback.print_exc()
