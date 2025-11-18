# Satisfactory Mod Installer - Rewritten
#
# This version uses the customtkinter library for a modern, dark-themed UI.
# To run this script, you need to install customtkinter and tkinterdnd2:
# pip install customtkinter
# pip install tkinterdnd2

import os
import subprocess
import tempfile
import shutil
import configparser
import glob
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_SUPPORT = True
except ImportError:
    DND_SUPPORT = False


# --- Configuration ---
CONFIG_FILE = 'config.ini'
CONFIG_SECTION = 'Settings'
KEY_7ZIP = '7zip_path'
KEY_OUTPUT_DIR = 'output_dir'
KEY_OVERWRITE = 'overwrite'

def load_config():
    """Loads settings from config.ini."""
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    settings = {}
    if CONFIG_SECTION in config:
        settings[KEY_7ZIP] = config[CONFIG_SECTION].get(KEY_7ZIP)
        settings[KEY_OUTPUT_DIR] = config[CONFIG_SECTION].get(KEY_OUTPUT_DIR)
        settings[KEY_OVERWRITE] = config[CONFIG_SECTION].getboolean(KEY_OVERWRITE, fallback=False)
    return settings

def save_config(settings):
    """Saves settings to config.ini."""
    config = configparser.ConfigParser()
    config[CONFIG_SECTION] = {k: str(v) for k, v in settings.items() if v is not None}
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

# --- Core Logic (largely unchanged) ---

def find_7zip(manual_path=None):
    """
    Finds the 7-Zip executable by checking the manual path, system PATH,
    and common installation directories.
    """
    if manual_path and os.path.exists(manual_path):
        return manual_path
    if shutil.which('7z'):
        return shutil.which('7z')
    for path in [
        os.path.join(os.environ.get('ProgramFiles', ''), '7-Zip', '7z.exe'),
        os.path.join(os.environ.get('ProgramFiles(x86)', ''), '7-Zip', '7z.exe')
    ]:
        if os.path.exists(path):
            return path
    return None

def process_smod_file(smod_path, output_root, sevenzip_path, overwrite=False, log_callback=None):
    """
    Extracts and installs a single .smod file.
    """
    def log(message, level="INFO"):
        if log_callback:
            log_callback(message, level)

    if not os.path.exists(smod_path):
        log(f"File not found: {smod_path}", "ERROR")
        return

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            log(f"Extracting {os.path.basename(smod_path)}...", "INFO")
            subprocess.run(
                [sevenzip_path, 'x', smod_path, f'-o{temp_dir}'],
                check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
        except subprocess.CalledProcessError as e:
            log(f"Failed to extract {os.path.basename(smod_path)}. 7-Zip error: {e.stderr}", "ERROR")
            return

        uplugin_files = glob.glob(os.path.join(temp_dir, '**', '*.uplugin'), recursive=True)
        if not uplugin_files:
            log(f"No .uplugin file found in {os.path.basename(smod_path)}", "ERROR")
            return
        
        uplugin_path = uplugin_files[0]
        mod_name = os.path.splitext(os.path.basename(uplugin_path))[0]
        dest_folder = os.path.join(output_root, mod_name)

        log(f"Found mod: {mod_name}", "INFO")

        if os.path.exists(dest_folder):
            if overwrite:
                log(f"Overwrite enabled. Removing existing folder: {dest_folder}", "WARN")
                try:
                    shutil.rmtree(dest_folder)
                except OSError as e:
                    log(f"Could not remove existing folder {dest_folder}. Error: {e}", "ERROR")
                    return
            else:
                log(f"Destination folder already exists. Skipping installation.", "WARN")
                return
        
        os.makedirs(dest_folder, exist_ok=True)

        try:
            log(f"Copying files to {dest_folder}...", "INFO")
            source_content = os.listdir(temp_dir)
            if len(source_content) == 1 and os.path.isdir(os.path.join(temp_dir, source_content[0])):
                 copy_from_dir = os.path.join(temp_dir, source_content[0])
            else:
                 copy_from_dir = temp_dir

            for item in os.listdir(copy_from_dir):
                s = os.path.join(copy_from_dir, item)
                d = os.path.join(dest_folder, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
        except Exception as e:
            log(f"Failed to copy files for {mod_name}. Error: {e}", "ERROR")
            return

    log(f"Successfully installed {mod_name}", "SUCCESS")


# --- GUI ---
class ModInstallerApp(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master

        self.settings = load_config()
        self.sevenzip_path = find_7zip(self.settings.get(KEY_7ZIP))
        self.smod_files = []

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.create_sidebar()
        self.create_main_content()
        
        if not DND_SUPPORT:
            self.log("Drag and drop is not available. Please install tkinterdnd2.", "WARN")

        self.after(100, self.check_7zip)

    def create_sidebar(self):
        sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsw")
        sidebar_frame.grid_rowconfigure(4, weight=1)

        logo_label = ctk.CTkLabel(sidebar_frame, text="Installer Settings", font=ctk.CTkFont(size=20, weight="bold"))
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # SMOD Files
        smod_button = ctk.CTkButton(sidebar_frame, text="Browse SMOD Files", command=self.browse_smod_files)
        smod_button.grid(row=1, column=0, padx=20, pady=10)
        self.smod_label = ctk.CTkLabel(sidebar_frame, text="No files selected.\nDrag & drop files here.", wraplength=200, anchor="w")
        self.smod_label.grid(row=2, column=0, padx=20, pady=(0, 10))

        # Output Directory
        output_frame = ctk.CTkFrame(sidebar_frame, fg_color="transparent")
        output_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        output_frame.grid_columnconfigure(0, weight=1)

        output_button = ctk.CTkButton(output_frame, text="Select Output Folder", command=self.browse_output_dir)
        output_button.grid(row=0, column=0, sticky="ew")

        hint_button = ctk.CTkButton(output_frame, text="?", width=30, command=self.show_output_hint)
        hint_button.grid(row=0, column=1, padx=(5,0))

        self.output_dir_var = ctk.StringVar(value=self.settings.get(KEY_OUTPUT_DIR, ''))
        output_entry = ctk.CTkEntry(sidebar_frame, textvariable=self.output_dir_var)
        output_entry.grid(row=4, column=0, padx=20, pady=(0,10), sticky="n")

        # Options
        self.overwrite_var = ctk.BooleanVar(value=self.settings.get(KEY_OVERWRITE, False))
        overwrite_check = ctk.CTkCheckBox(sidebar_frame, text="Overwrite existing mods", variable=self.overwrite_var)
        overwrite_check.grid(row=5, column=0, padx=20, pady=10, sticky="s")

        # Install Button
        self.install_button_frame = ctk.CTkFrame(sidebar_frame)
        self.install_button_frame.grid(row=6, column=0, padx=20, pady=(10, 20), sticky="s")
        self.install_button_frame.grid_columnconfigure(0, weight=1)

        self.install_progressbar = ctk.CTkProgressBar(self.install_button_frame, height=30)
        self.install_progressbar.set(0)
        
        self.install_button = ctk.CTkButton(self.install_button_frame, text="Install Mods", font=ctk.CTkFont(size=16, weight="bold"), command=self.start_install_thread)
        self.install_button.grid(row=0, column=0, sticky="ew")


    def create_main_content(self):
        main_frame = ctk.CTkFrame(self, corner_radius=10)
        main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        self.log_textbox = ctk.CTkTextbox(main_frame, corner_radius=8, state="disabled", wrap="word")
        self.log_textbox.grid(row=0, column=0, sticky="nsew")

        self.log_textbox.configure(
            scrollbar_button_color="#444444",
            scrollbar_button_hover_color="#555555"
        )

    def log(self, message, level="INFO"):
        self.after(0, self._log_append, message, level)

    def _log_append(self, message, level):
        self.log_textbox.configure(state="normal")
        
        tag = f"tag_{level.lower()}"
        self.log_textbox.tag_config(tag, foreground=self.get_color_for_level(level))
        
        self.log_textbox.insert("end", f"[{level}] {message}\n", tag)
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")

    def get_color_for_level(self, level):
        if level == "ERROR": return "#FF6B6B"
        if level == "WARN": return "#FFD166"
        if level == "SUCCESS": return "#06D6A0"
        return "white"

    def handle_drop(self, event):
        files_str = event.data.strip()
        if files_str.startswith('{') and files_str.endswith('}'):
            files_str = files_str[1:-1]
        
        dropped_files = self.master.tk.splitlist(files_str)
        
        smod_files = [f for f in dropped_files if f.lower().endswith('.smod')]
        if smod_files:
            self.smod_files.extend(smod_files)
            self.smod_label.configure(text=f"{len(self.smod_files)} file(s) selected.")
            self.log(f"Dropped {len(smod_files)} SMOD file(s).", "INFO")

    def browse_smod_files(self):
        files = filedialog.askopenfilenames(
            title="Select SMOD files",
            filetypes=(("SMOD Files", "*.smod"), ("All files", "*.*"))
        )
        if files:
            self.smod_files = list(files)
            self.smod_label.configure(text=f"{len(files)} file(s) selected.")
            self.log(f"Selected {len(files)} SMOD file(s).", "INFO")

    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="Select Output Folder")
        if directory:
            self.output_dir_var.set(directory)
            self.log(f"Set output directory to: {directory}", "INFO")

    def show_output_hint(self):
        messagebox.showinfo(
            "Output Folder Hint",
            "For easy installation, you can select the 'Mods' folder directly within your Satisfactory game directory. "
            "This is typically located at <game root>/FactoryGame/Mods."
        )

    def check_7zip(self):
        if not self.sevenzip_path:
            self.master.withdraw()
            messagebox.showwarning("7-Zip Not Found", "The 7-Zip executable (7z.exe) was not found automatically. Please locate it.")
            path = filedialog.askopenfilename(
                title="Locate 7z.exe",
                filetypes=(("Executable", "*.exe"),)
            )
            if path and os.path.basename(path).lower() == '7z.exe':
                self.sevenzip_path = path
                self.settings[KEY_7ZIP] = path
                save_config(self.settings)
                self.master.deiconify()
                self.log("7-Zip path has been set.", "INFO")
            else:
                messagebox.showerror("Error", "7-Zip is required. The application will now exit.")
                self.master.quit()

    def start_install_thread(self):
        self.install_button.grid_remove()
        self.install_progressbar.grid(row=0, column=0, sticky="ew")
        self.install_progressbar.set(0)
        
        install_thread = threading.Thread(target=self.install_mods, daemon=True)
        install_thread.start()

    def install_mods(self):
        output_dir = self.output_dir_var.get()
        overwrite = self.overwrite_var.get()

        if not self.smod_files:
            self.log("Please select one or more .smod files.", "ERROR")
            self.after(0, self.finish_installation)
            return
        if not output_dir or not os.path.isdir(output_dir):
            self.log("Please select a valid output folder.", "ERROR")
            self.after(0, self.finish_installation)
            return

        self.settings[KEY_OUTPUT_DIR] = output_dir
        self.settings[KEY_OVERWRITE] = overwrite
        save_config(self.settings)

        self.log("\n--- Starting Installation ---", "INFO")
        total_files = len(self.smod_files)
        for i, smod_file in enumerate(self.smod_files):
            process_smod_file(smod_file, output_dir, self.sevenzip_path, overwrite, log_callback=self.log)
            progress = (i + 1) / total_files
            self.after(0, self.update_progress, progress)
        
        self.log("\n--- Installation Complete ---", "SUCCESS")
        self.after(0, self.finish_installation)

    def update_progress(self, value):
        self.install_progressbar.set(value)

    def finish_installation(self):
        self.install_progressbar.grid_remove()
        self.install_button.grid(row=0, column=0, sticky="ew")
        self.smod_files = []
        self.smod_label.configure(text="No files selected.\nDrag & drop files here.")


def main():
    if DND_SUPPORT:
        root = TkinterDnD.Tk()
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
    else:
        root = ctk.CTk()

    root.title("Satisfactory Mod Installer")
    root.geometry("900x600")

    app = ModInstallerApp(master=root)
    app.pack(expand=True, fill="both")

    if DND_SUPPORT:
        root.drop_target_register(DND_FILES)
        root.dnd_bind('<<Drop>>', app.handle_drop)

    root.mainloop()


if __name__ == '__main__':
    main()
