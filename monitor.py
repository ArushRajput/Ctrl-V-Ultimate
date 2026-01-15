import pyperclip
import time
import os
import re
from datetime import datetime
from PIL import ImageGrab
import logging

# Configure logging
logging.basicConfig(filename='debug_monitor.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

class ClipboardMonitor:
    def __init__(self, mode="General"):
        self.mode = mode
        try:
            self.last_content = pyperclip.paste()
        except Exception as e:
            logging.error(f"Init Error: {e}")
            self.last_content = ""
            
        self.is_running = False
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        self.stats = {"text": 0, "links": 0, "images": 0}
        
        if not os.path.exists("captures"):
            try:
                os.makedirs("captures")
            except Exception as e:
                logging.error(f"Failed to create captures dir: {e}")

    def set_mode(self, mode):
        self.mode = mode
        logging.info(f"Mode set to: {mode}")

    def is_link(self, text):
        return bool(self.url_pattern.search(text))

    def start(self, callback=None):
        self.is_running = True
        logging.info(f"Monitor started in {self.mode} mode")
        while self.is_running:
            try:
                # Check for Image
                try:
                    img = ImageGrab.grabclipboard()
                    if img:
                        self._save_image(img, callback)
                except Exception as img_err:
                    logging.error(f"Image Grab Error: {img_err}")

                # Check for Text
                try:
                    new_content = pyperclip.paste()
                    if new_content and new_content != self.last_content:
                        self.last_content = new_content
                        logging.info(f"New text captured: {new_content[:20]}...")
                        self._process_text(new_content)
                        if callback:
                            callback("text", new_content)
                except Exception as text_err:
                    logging.error(f"Text Grab Error: {text_err}")
                
                time.sleep(1)
            except Exception as e:
                logging.error(f"Main Loop Error: {e}")
                time.sleep(2)

    def stop(self):
        self.is_running = False
        logging.info("Monitor stopped")

    def _process_text(self, content):
        try:
            is_url = self.is_link(content)
            if is_url:
                self.stats["links"] += 1
            else:
                self.stats["text"] += 1

            filename = "clipboard_history.txt"
            if self.mode == "Links Only" and is_url:
                filename = "links_only.txt"
            elif self.mode == "Smart Sorting":
                filename = "links.txt" if is_url else "text_history.txt"
            elif self.mode == "Links Only" and not is_url:
                 return # Skip saving non-links in Links Only mode

            self._save_to_file(filename, content)
        except Exception as e:
            logging.error(f"Process Text Error: {e}")

    def _save_image(self, img, callback):
        # We need to avoid saving the same image repeatedly in the loop
        # For simplicity, we'll only save if it's been more than 2 seconds since last image
        # or if we want to be more precise, we could hash it.
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"captures/img_{timestamp}.png"
        
        # Only save if filename doesn't effectively exist (timestamp should handle this)
        if not os.path.exists(filename):
            img.save(filename)
            self.stats["images"] += 1
            # Clear clipboard to avoid duplicate captures if possible, 
            # but that might be annoying for the user. 
            # Better to just use a cooldown.
            if callback:
                callback("image", filename)
            # Sleep slightly longer after image to avoid burst
            time.sleep(0.5)

    def _save_to_file(self, filename, content):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(filename, "a", encoding="utf-8") as f:
            f.write(f"\n--- Captured at {timestamp} ---\n")
            f.write(content)
            f.write("\n" + "="*40 + "\n")

if __name__ == "__main__":
    monitor = ClipboardMonitor()
    monitor.start()
