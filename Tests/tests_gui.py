import tkinter as tk
from tkinter import scrolledtext
import subprocess
import threading
import sys
import os

class TestRunnerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Test Runner & Output Viewer")
        self.root.geometry("800x600")
        
        # Setup UI Elements
        self.btn_run = tk.Button(
            root, 
            text="Run Organized Tests", 
            command=self.run_tests, 
            font=("Helvetica", 14, "bold"), 
            bg="#4CAF50", 
            fg="white",
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.btn_run.pack(pady=10, padx=10, fill=tk.X)
        
        # Output text area with dark theme
        self.text_area = scrolledtext.ScrolledText(
            root, 
            wrap=tk.WORD, 
            font=("Consolas", 10), 
            bg="#1e1e1e", 
            fg="#d4d4d4"
        )
        self.text_area.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        tags = {
            "success": {"foreground": "#4CAF50"},
            "error": {"foreground": "#F44336"},
            "header": {"foreground": "#2196F3", "font": ("Consolas", 10, "bold")},
            "info": {"foreground": "#64B5F6"}
        }
        for tag, kwargs in tags.items():
            self.text_area.tag_config(tag, **kwargs)

    def run_tests(self):
        self.btn_run.config(state=tk.DISABLED, text="Running Tests... Please wait")
        self.text_area.delete(1.0, tk.END)
        self._append_text("Starting Test Suite...\n" + "="*60 + "\n\n", "header")
        
        # Run subprocess in a separate thread so it doesn't freeze the GUI
        thread = threading.Thread(target=self._execute_subprocess, daemon=True)
        thread.start()
        
    def _execute_subprocess(self):
        try:
            # Find python executable dynamically from common virtualenv names (.venv or venv)
            # as sys.executable may point to a global python if launched outside the activated shell.
            python_exe = sys.executable
            for venv_dir in [".venv", "venv"]:
                venv_path = os.path.join(os.getcwd(), venv_dir, "Scripts", "python.exe")
                if os.path.exists(venv_path):
                    python_exe = venv_path
                    self.root.after(0, self._append_text, f"Using virtual environment python: {python_exe}\n\n", "info")
                    break

            # Build an environment dictionary overriding python I/O encoding
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            # We use standard library subprocess with real-time output reading
            # We explicitly read as bytes and decode to avoid any Popen text wrappers crashing on weird terminals
            script_dir = os.path.dirname(os.path.abspath(__file__))
            process = subprocess.Popen(
                [python_exe, "-m", "pytest", "tests.py", "-s", "-v"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                cwd=script_dir,
                env=env
            )
            
            for raw_line in iter(process.stdout.readline, b''):
                # Decode each line byte-by-byte using utf-8, replacing bad skips
                line = raw_line.decode('utf-8', errors='replace')
                
                # Process lines to add basic color tagging dynamically
                tag = "info"
                if "PASSED" in line:
                    tag = "success"
                elif "FAILED" in line or "ERROR" in line:
                    tag = "error"
                elif "===" in line:
                    tag = "header"
                    
                self.root.after(0, self._append_text, line, tag)
                
            process.stdout.close()
            process.wait()
            
            self.root.after(0, self._test_finished, process.returncode)
        except Exception as e:
            self.root.after(0, self._append_text, f"\nError executing tests: {str(e)}\n\n", "error")
            self.root.after(0, self._test_finished, -1)
            
    def _append_text(self, text, tag="info"):
        self.text_area.insert(tk.END, text, tag)
        self.text_area.see(tk.END)
        
    def _test_finished(self, returncode):
        self.btn_run.config(state=tk.NORMAL, text="Run Organized Tests", bg="#4CAF50")
        
        status = "SUCCESS" if returncode == 0 else "FAILED / ERRORS"
        status_tag = "success" if returncode == 0 else "error"
        
        finish_text = f"\n" + "="*60 + str(f"\nTests execution finished with status: {status} (Exit Code: {returncode})\n")
        self.text_area.insert(tk.END, finish_text, status_tag)
        self.text_area.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = TestRunnerGUI(root)
    root.mainloop()