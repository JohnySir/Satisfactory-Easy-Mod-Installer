# Satisfactory Mod Installer

This tool allows you to easily install Satisfactory mods (`.smod` files) into a specified folder structure.

![V2](https://i.ibb.co/tphC3hZ4/Screenshot-2025-11-18-184810.png "V2")

## Requirements

*   **Windows Operating System**
*   **Python 3.10+**: Make sure Python is installed and added to your system's PATH.
*   **7-Zip**: The tool uses 7-Zip to extract `.smod` files. It will try to find it automatically, but you may be prompted to provide the path to `7z.exe`.
*   **Tkinter**: The graphical user interface is built with Tkinter, which is part of the Python standard library and should be included with your Python installation. If you get an error about Tkinter not being found, you may need to install it separately (e.g., on Debian/Ubuntu, this can be done with `sudo apt-get install python3-tk`).

## Installation

1.  **Install Python**: If you don't have Python, download and install it from [python.org](https://www.python.org/downloads/). Make sure to check the box that says "Add Python to PATH" during installation.

2.  **Install 7-Zip**: If you don't have 7-Zip, download and install it from [7-zip.org](https://www.7-zip.org/).

## Prerequisites

**Important:** You must install the Satisfactory Mod Loader (SML) before installing mods. This tool only installs the mods themselves, not the loader.

To install SML manually:
1. Download a compatible version of SML from the [Satisfactory Mod Repository (SMR)](https://ficsit.app/mod/SML).
2. Create a `Mods` folder inside your game's installation directory (e.g., `<game root>/FactoryGame/Mods`).
3. Unzip the SML download `Satisfactory_Mod_Loader-Windows-xxx.smod` into the `Mods` folder. Ensure the final folder structure is `<game root>/FactoryGame/Mods/SML`.

For complete and up-to-date instructions, please refer to the official documentation:
[https://docs.ficsit.app/satisfactory-modding/latest/ManualInstallDirections.html](https://docs.ficsit.app/satisfactory-modding/latest/ManualInstallDirections.html)

## Usage

1.  **Run the script**: Open a command prompt or PowerShell in the same directory where you saved the script and run:
    ```
    python SatisfactoryModInstaller.py
    ```


## How it Works

For each `.smod` file, the installer performs the following steps:

1.  Extracts the `.smod` file to a temporary directory using 7-Zip.
2.  Searches the extracted files for a `.uplugin` file.
3.  Creates a new folder in your chosen output directory. The name of this new folder is based on the filename of the `.uplugin` file (e.g., `MyTestMod.uplugin` results in a folder named `MyTestMod`).
4.  Copies all the extracted files and folders into this new destination folder.
5.  Cleans up the temporary files.

Your settings (7-Zip path, last used output folder, and overwrite preference) are saved in a `config.ini` file in the same directory as the script.
