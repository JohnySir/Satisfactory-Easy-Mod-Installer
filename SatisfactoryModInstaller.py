import os
import subprocess
import tempfile
import shutil
import configparser
import glob
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading

# --- Configuration ---
CONFIG_FILE = 'config.ini'
CONFIG_SECTION = 'Settings'
KEY_7ZIP = '7zip_path'
KEY_OUTPUT_DIR = 'output_dir'
KEY_OVERWRITE = 'overwrite'

def load_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    settings = {}
    if CONFIG_SECTION in config:
        settings[KEY_7ZIP] = config[CONFIG_SECTION].get(KEY_7ZIP)
        settings[KEY_OUTPUT_DIR] = config[CONFIG_SECTION].get(KEY_OUTPUT_DIR)
        settings[KEY_OVERWRITE] = config[CONFIG_SECTION].getboolean(KEY_OVERWRITE, fallback=False)
    return settings

def save_config(settings):
    config = configparser.ConfigParser()
    config[CONFIG_SECTION] = {k: str(v) for k, v in settings.items() if v is not None}
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

# --- Core Logic ---

def find_7zip(manual_path=None):
    """
    Finds the 7-Zip executable.
    1. Tries the provided manual_path.
    2. Tries the system PATH.
    3. Checks common installation directories.
    """
    if manual_path and os.path.exists(manual_path):
        return manual_path

    # Try PATH
    if shutil.which('7z'):
        return shutil.which('7z')

    # Check common install locations
    for path in [
        os.path.join(os.environ.get('ProgramFiles', ''), '7-Zip', '7z.exe'),
        os.path.join(os.environ.get('ProgramFiles(x86)', ''), '7-Zip', '7z.exe')
    ]:
        if os.path.exists(path):
            return path

    return None

def process_smod_file(smod_path, output_root, sevenzip_path, overwrite=False, log_callback=None):
    """
    Processes a single .smod file.
    """
    def log(message):
        if log_callback:
            log_callback(message)

    if not os.path.exists(smod_path):
        log(f"ERROR: .smod file not found: {smod_path}")
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        # 1. Extract .smod to temp directory
        try:
            subprocess.run(
                [sevenzip_path, 'x', smod_path, f'-o{temp_dir}'],
                check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
        except subprocess.CalledProcessError as e:
            log(f"ERROR: Failed to extract {os.path.basename(smod_path)}. 7-Zip error: {e.stderr}")
            return

        # 2. Find .uplugin file
        uplugin_files = glob.glob(os.path.join(temp_dir, '**', '*.uplugin'), recursive=True)
        if not uplugin_files:
            log(f"ERROR: No .uplugin file found in {os.path.basename(smod_path)}")
            return
        
        uplugin_path = uplugin_files[0]
        uplugin_filename = os.path.basename(uplugin_path)
        
        # 3. Create destination folder
        mod_name = os.path.splitext(uplugin_filename)[0]
        dest_folder = os.path.join(output_root, mod_name)

        if os.path.exists(dest_folder):
            if overwrite:
                try:
                    shutil.rmtree(dest_folder)
                except OSError as e:
                    log(f"ERROR: Could not remove existing folder {dest_folder}. Error: {e}")
                    return
            else:
                log(f"SKIPPED: Destination folder already exists: {dest_folder}")
                return
        
        os.makedirs(dest_folder, exist_ok=True)

        # 4. Copy files
        try:
            # Copy all contents from the temporary directory to the destination
            for item in os.listdir(temp_dir):
                s = os.path.join(temp_dir, item)
                d = os.path.join(dest_folder, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
        except Exception as e:
            log(f"ERROR: Failed to copy files for {mod_name}. Error: {e}")
            return

    log(f"SUCCESS: Installed {mod_name} to {dest_folder}")


# --- GUI ---

class ModInstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Satisfactory Mod Installer")
        self.settings = load_config()
        self.sevenzip_path = find_7zip(self.settings.get(KEY_7ZIP))

        self.smod_files_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=self.settings.get(KEY_OUTPUT_DIR, ''))
        self.overwrite_var = tk.BooleanVar(value=self.settings.get(KEY_OVERWRITE, False))

        self.create_widgets()
        self.root.after(100, self.check_7zip)


    def create_widgets(self):
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- File Selection ---
        file_frame = tk.Frame(main_frame)
        file_frame.pack(fill=tk.X, pady=5)
        tk.Label(file_frame, text="SMOD Files:").pack(side=tk.LEFT, anchor='w', padx=(0, 5))
        tk.Entry(file_frame, textvariable=self.smod_files_var, state='readonly').pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Button(file_frame, text="Browse...", command=self.browse_smod_files).pack(side=tk.LEFT, padx=(5, 0))

        # --- Output Directory ---
        output_frame = tk.Frame(main_frame)
        output_frame.pack(fill=tk.X, pady=5)
        tk.Label(output_frame, text="Output Folder:").pack(side=tk.LEFT, anchor='w')
        tk.Button(output_frame, text="?", command=self.show_output_hint, width=2, height=1, relief=tk.GROOVE).pack(side=tk.LEFT, padx=(5, 0))
        tk.Entry(output_frame, textvariable=self.output_dir_var).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5,0))
        tk.Button(output_frame, text="Browse...", command=self.browse_output_dir).pack(side=tk.LEFT, padx=(5, 0))

        # --- Options ---
        options_frame = tk.Frame(main_frame)
        options_frame.pack(fill=tk.X, pady=5)
        tk.Checkbutton(options_frame, text="Overwrite existing folders", variable=self.overwrite_var).pack(side=tk.LEFT)

        # --- Buttons ---
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        self.install_button = tk.Button(button_frame, text="Install Mods", command=self.start_install_thread)
        self.install_button.pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Exit", command=self.root.quit).pack(side=tk.LEFT)

        # --- Log Area ---
        log_frame = tk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15, state='disabled')
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def log(self, message):
        # This method needs to be thread-safe for calls from the worker thread
        self.root.after(0, self._log_append, message)

    def _log_append(self, message):
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, message + '\n')
        self.log_area.configure(state='disabled')
        self.log_area.see(tk.END)

    def browse_smod_files(self):
        files = filedialog.askopenfilenames(title="Select SMOD files", filetypes=(("SMOD Files", "*.smod"), ("All files", "*.*")))
        if files:
            self.smod_files_var.set(";".join(files))

    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="Select Output Folder")
        if directory:
            self.output_dir_var.set(directory)

    def show_output_hint(self):
        messagebox.showinfo(
            "Output Folder Hint",
            "For easy installation, you can select the 'Mods' folder directly within your Satisfactory game directory. "
            "This is typically located at <game root>/FactoryGame/Mods."
        )

    def check_7zip(self):
        if not self.sevenzip_path:
            self.root.withdraw() # Hide main window
            path = filedialog.askopenfilename(
                title="7-Zip executable (7z.exe) not found. Please locate it.",
                filetypes=(("Executable Files", "*.exe"),)
            )
            if path and os.path.exists(path):
                self.sevenzip_path = path
                self.settings[KEY_7ZIP] = path
                save_config(self.settings)
                self.root.deiconify() # Show main window again
            else:
                messagebox.showerror("Error", "7-Zip is required to continue. Exiting.")
                self.root.quit()

    def start_install_thread(self):
        self.install_button.config(state=tk.DISABLED)
        install_thread = threading.Thread(target=self.install_mods, daemon=True)
        install_thread.start()

    def install_mods(self):
        smod_files_str = self.smod_files_var.get()
        output_dir = self.output_dir_var.get()
        overwrite = self.overwrite_var.get()

        if not smod_files_str:
            self.log("ERROR: Please select one or more .smod files.")
            self.install_button.config(state=tk.NORMAL)
            return
        if not output_dir or not os.path.isdir(output_dir):
            self.log("ERROR: Please select a valid output folder.")
            self.install_button.config(state=tk.NORMAL)
            return

        # Save settings
        self.settings[KEY_OUTPUT_DIR] = output_dir
        self.settings[KEY_OVERWRITE] = overwrite
        save_config(self.settings)

        smod_files = smod_files_str.split(';')
        for smod_file in smod_files:
            self.log(f"Processing {os.path.basename(smod_file)}...")
            process_smod_file(smod_file, output_dir, self.sevenzip_path, overwrite, log_callback=self.log)

        self.log("\nInstallation complete.")
        self.root.after(0, self.enable_install_button)

    def enable_install_button(self):
        self.install_button.config(state=tk.NORMAL)


def main():
    root = tk.Tk()
    app = ModInstallerApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()