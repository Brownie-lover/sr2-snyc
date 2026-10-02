import os
import sys
import time
import json
import zipfile
import subprocess
import requests
from pathlib import Path

# ==========================================
# CONFIGURATION
# ==========================================
SERVER_URL = "https://jaunt-happiness-tinsmith.ngrok-free.dev"
GAME_ID = "slimerancher2"
CONFIG_FILE = "config.json"


def get_game_exe_path() -> str:
    """Loads game exe path from config.json or prompts user to pick SlimeRancher2.exe."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                cached_path = config.get("exe_path")
                if cached_path and os.path.exists(cached_path):
                    return cached_path
        except Exception:
            pass

    print("[!] SlimeRancher2.exe path not configured.")
    print("[*] Opening File Explorer window to locate SlimeRancher2.exe...")

    selected_path = ""

    # Open Windows File Picker
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        selected_path = filedialog.askopenfilename(
            title="Select SlimeRancher2.exe",
            filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")]
        )
        root.destroy()
    except Exception:
        pass

    # Terminal input fallback
    if not selected_path or not os.path.exists(selected_path):
        print("\n--------------------------------------------------")
        selected_path = input("Please paste the full path to SlimeRancher2.exe: ").strip('"\' ')
        print("--------------------------------------------------\n")

    if not os.path.exists(selected_path):
        print(f"[-] Invalid file path provided: {selected_path}")
        sys.exit(1)

    # Save to config.json
    with open(CONFIG_FILE, "w") as f:
        json.dump({"exe_path": selected_path}, f, indent=4)

    print(f"[+] Cached executable path to {CONFIG_FILE}")
    return selected_path


def resolve_save_path() -> str:
    """Finds the Slime Rancher 2 save folder under the current user's profile."""
    base_dir = Path.home() / "AppData" / "LocalLow" / "MonomiPark" / "SlimeRancher2" / "Steam"
    if not base_dir.exists():
        raise FileNotFoundError(f"Slime Rancher 2 folder not found at: {base_dir}")
    
    steam_folders = [d for d in base_dir.iterdir() if d.is_dir()]
    if not steam_folders:
        raise FileNotFoundError(f"No Steam User directory found in {base_dir}")
        
    return str(steam_folders[0])


def zip_directory(dir_path: str, zip_path: str):
    """Compresses save folder into a ZIP archive."""
    target_path = Path(dir_path)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(target_path):
            for file in files:
                file_path = Path(root) / file
                archive_name = file_path.relative_to(target_path)
                zipf.write(file_path, archive_name)


def merge_zip_to_dir(zip_path: str, local_dir: str):
    """Extracts server saves, replacing local files only if incoming files are newer."""
    target_path = Path(local_dir)
    target_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as zipf:
        for info in zipf.infolist():
            extracted_path = target_path / info.filename

            if info.is_dir():
                extracted_path.mkdir(parents=True, exist_ok=True)
                continue

            extracted_path.parent.mkdir(parents=True, exist_ok=True)
            zip_file_time = time.mktime(info.date_time + (0, 0, -1))

            if extracted_path.exists():
                local_file_time = os.path.getmtime(extracted_path)
                if zip_file_time <= local_file_time:
                    print(f"[=] Local file current: {info.filename}")
                    continue

            print(f"[+] Updating/Merging newer file: {info.filename}")
            zipf.extract(info, target_path)


def pull_saves(server_url: str, game_id: str, local_dir: str):
    """Downloads save files from server prior to game launch."""
    print(f"[*] Connecting to {server_url}...")
    temp_zip = f"{game_id}_download.zip"
    try:
        response = requests.get(f"{server_url.rstrip('/')}/api/download/{game_id}", stream=True, timeout=10)
        if response.status_code == 200:
            with open(temp_zip, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("[*] Merging server save files...")
            merge_zip_to_dir(temp_zip, local_dir)
            print("[+] Pre-game pull complete!")
        elif response.status_code == 404:
            print("[!] No saves found on server yet. Launching with local save data.")
        else:
            print(f"[-] Download failed. Server HTTP status: {response.status_code}")
    except requests.RequestException as e:
        print(f"[-] Could not connect to server: {e}. Launching local game.")
    finally:
        if os.path.exists(temp_zip):
            os.remove(temp_zip)


def push_saves(server_url: str, game_id: str, local_dir: str):
    """Uploads local save files back to server after game exit."""
    print("[*] Packaging updated save directory...")
    temp_zip = f"{game_id}_upload.zip"
    try:
        zip_directory(local_dir, temp_zip)
        print("[*] Uploading saves to server...")
        with open(temp_zip, 'rb') as f:
            response = requests.post(
                f"{server_url.rstrip('/')}/api/upload/{game_id}",
                files={'savefile': f},
                timeout=20
            )
        if response.status_code == 200:
            print("[+] Post-game save upload complete!")
        else:
            print(f"[-] Save upload failed. Server HTTP status: {response.status_code}")
    except requests.RequestException as e:
        print(f"[-] Failed to push saves to server: {e}")
    finally:
        if os.path.exists(temp_zip):
            os.remove(temp_zip)


def launch_and_wait_direct(exe_path: str) -> bool:
    """Launches SlimeRancher2.exe directly and blocks until process terminates."""
    game_dir = os.path.dirname(exe_path)
    print(f"[*] Launching executable: {exe_path}")

    try:
        process = subprocess.Popen([exe_path], cwd=game_dir)
        print("[+] Game process started! Active session in progress.")
        print("[*] Script paused. Do not close this window — saves sync automatically upon game exit.")
        
        process.wait()  # Holds script open while game is running
        print("[+] Game process exited.")
        return True
    except Exception as e:
        print(f"[-] Failed to launch game executable: {e}")
        return False


if __name__ == "__main__":
    # 1. Resolve Game Executable Path
    game_exe_path = get_game_exe_path()

    # 2. Resolve Local Save Directory
    try:
        save_dir = resolve_save_path()
        print(f"[*] Local Save Path: {save_dir}")
    except FileNotFoundError as err:
        print(f"[-] Path Error: {err}")
        sys.exit(1)

    # 3. Download Latest Save
    print("\n--- STEP 1: PULLING SAVES FROM SERVER ---")
    pull_saves(SERVER_URL, GAME_ID, save_dir)

    # 4. Launch Game & Wait for Exit
    print("\n--- STEP 2: LAUNCHING GAME ---")
    played = launch_and_wait_direct(game_exe_path)

    # 5. Upload New Save
    if played:
        print("\n--- STEP 3: PUSHING UPDATED SAVES TO SERVER ---")
        push_saves(SERVER_URL, GAME_ID, save_dir)
    else:
        print("[-] Skipping save upload because game process failed or was closed early.")

    print("\n[+] Sync execution finished!")