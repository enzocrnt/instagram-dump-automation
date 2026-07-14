import eel
import os
import json
import shutil
import glob
import random
import datetime
import hashlib
import concurrent.futures
import tkinter as tk
from tkinter import filedialog

from src.uploader import upload_photo_carousel as execute_browser_upload

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')
STAGING_DIR = os.path.join(os.path.dirname(__file__), 'web', 'staging')

MONTH_NUM_MAP = {
    "January": "01", "February": "02", "March": "03", "April": "04",
    "May": "05", "June": "06", "July": "07", "August": "08",
    "September": "09", "October": "10", "November": "11", "December": "12"
}

REV_MONTH_MAP = {v: k for k, v in MONTH_NUM_MAP.items()}

executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

def load_config():
    defaults = {
        "source_dir": r"D:\2024_Backup",
        "vault_dir": r"D:\IG_Dump_Staging"
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                saved = json.load(f)
                return {**defaults, **saved}
        except Exception:
            pass
            
    return defaults

eel.init('web')

@eel.expose
def python_verify_source_connection():
    config = load_config()
    source_dir = config.get("source_dir", "")
    return os.path.exists(source_dir) and os.path.isdir(source_dir)

@eel.expose
def python_open_folder_picker(default_path):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    initial_dir = default_path if os.path.exists(default_path) else None
    chosen_directory = filedialog.askdirectory(initialdir=initial_dir, title="Select Workflow Directory")
    
    root.destroy()
    return os.path.normpath(chosen_directory) if chosen_directory else ""

@eel.expose
def python_get_paths_config():
    return load_config()

@eel.expose
def python_save_paths_config(source_dir, vault_dir):
    try:
        config_data = {
            "source_dir": source_dir.strip(),
            "vault_dir": vault_dir.strip()
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)
        
        os.makedirs(config_data["vault_dir"], exist_ok=True)
        return True
    except Exception as e:
        print(f"[Config Error] Failed to update paths: {str(e)}")
        return False

@eel.expose
def python_open_batch_in_explorer(folder_name):
    config = load_config()
    vault_base = config.get("vault_dir")
    batch_vault_path = os.path.join(vault_base, folder_name)
    if os.path.exists(batch_vault_path):
        os.startfile(batch_vault_path)

@eel.expose
def python_sync_caption_file(folder_name, caption_text):
    """Overwrites persistent string log values within target directory payload."""
    config = load_config()
    vault_base = config.get("vault_dir")
    batch_vault_path = os.path.join(vault_base, folder_name)
    if os.path.exists(batch_vault_path):
        try:
            with open(os.path.join(batch_vault_path, "caption.txt"), "w", encoding="utf-8") as f:
                f.write(caption_text)
            return True
        except Exception:
            return False
    return False

def background_recursive_file_search(archive_base, target_year_str, target_month_str, target_day_str):
    valid_extensions = ('.jpg', '.jpeg', '.png')
    matched_file_paths = []

    for root_dir, _, files in os.walk(archive_base):
        if any(ignored in root_dir for ignored in ["staging", "STAGED_", "POSTED_"]):
            continue
            
        for file in files:
            if file.lower().endswith(valid_extensions):
                full_path = os.path.join(root_dir, file)
                try:
                    mtime = os.path.getmtime(full_path)
                    file_date = datetime.datetime.fromtimestamp(mtime)
                    
                    if (str(file_date.year) == target_year_str and 
                        f"{file_date.month:02d}" == target_month_str and 
                        f"{file_date.day:02d}" == target_day_str):
                        matched_file_paths.append(full_path)
                except Exception:
                    continue
    return matched_file_paths

@eel.expose
def python_reroll_day_pool(year, month, day, locked_filenames):
    config = load_config()
    archive_base = config.get("source_dir")
    
    if not os.path.exists(archive_base):
        return []
        
    target_year_str = str(year)
    target_month_str = MONTH_NUM_MAP.get(month)
    target_day_str = f"{int(day):02d}"
    
    future = executor.submit(
        background_recursive_file_search, 
        archive_base, target_year_str, target_month_str, target_day_str
    )
    while not future.done():
        eel.sleep(0.05)
        
    matched_file_paths = future.result()

    if not matched_file_paths:
        return []

    all_available_files = []
    for p in matched_file_paths:
        base = os.path.basename(p)
        dir_hash = hashlib.md5(os.path.dirname(p).encode('utf-8')).hexdigest()[:8]
        unique_name = f"_{dir_hash}_{base}"
        
        all_available_files.append({
            "basename": unique_name, 
            "original_name": base, 
            "full_path": p
        })

    candidate_pool = [f for f in all_available_files if f["basename"] not in locked_filenames]
    random.shuffle(candidate_pool)
    
    slots_needed = max(0, 10 - len(locked_filenames))
    newly_selected = candidate_pool[:slots_needed]
    
    final_selection = []
    for fname in locked_filenames:
        orig_item = next((item for item in all_available_files if item["basename"] == fname), None)
        if orig_item:
            final_selection.append(orig_item)

    final_selection.extend(newly_selected)
    final_basenames = [item["basename"] for item in final_selection]
    
    if os.path.exists(STAGING_DIR):
        for f in os.listdir(STAGING_DIR):
            if f not in final_basenames and f != ".gitkeep":
                try:
                    os.remove(os.path.join(STAGING_DIR, f))
                except Exception:
                    pass
    else:
        os.makedirs(STAGING_DIR, exist_ok=True)

    staged_payload_response = []
    for item in final_selection:
        fname = item["basename"]
        source_img_path = item["full_path"]
        dest_img_path = os.path.join(STAGING_DIR, fname)
        
        if os.path.exists(source_img_path) and not os.path.exists(dest_img_path):
            try:
                shutil.copy2(source_img_path, dest_img_path)
            except Exception as e:
                print(f"[Error] Failed to stage file {fname}: {str(e)}")
                continue
                
        staged_payload_response.append({"filename": fname})
        
    return staged_payload_response

@eel.expose
def python_save_to_standby(year, month, day, ordered_filenames):
    config = load_config()
    vault_base = config.get("vault_dir")
    
    month_digits = MONTH_NUM_MAP.get(month)
    day_digits = f"{int(day):02d}"
    target_year = str(year)
    
    date_str = f"{month_digits}-{day_digits}-{target_year}"
    folder_name = f"STAGED_{date_str}"
    batch_vault_path = os.path.join(vault_base, folder_name)
    
    counter = 1
    while os.path.exists(batch_vault_path):
        folder_name = f"STAGED_{date_str}_{counter}"
        batch_vault_path = os.path.join(vault_base, folder_name)
        counter += 1
        
    os.makedirs(batch_vault_path, exist_ok=True)
    
    # Generate persistent default text block
    default_caption = f"{month[:3]}. {int(day)}, {year}"
    with open(os.path.join(batch_vault_path, "caption.txt"), "w", encoding="utf-8") as f:
        f.write(default_caption)
    
    for index, fname in enumerate(ordered_filenames):
        source_file = os.path.join(STAGING_DIR, fname)
        
        clean_filename = fname
        if fname.startswith("_") and len(fname.split("_")) >= 3:
            clean_filename = "_".join(fname.split("_")[2:])
            
        indexed_filename = f"{index:02d}_{clean_filename}"
        destination_file = os.path.join(batch_vault_path, indexed_filename)
        
        if os.path.exists(source_file):
            shutil.copy2(source_file, destination_file)
            
    return folder_name

@eel.expose
def python_delete_batch_folder(folder_name):
    config = load_config()
    vault_base = config.get("vault_dir")
    
    batch_vault_path = os.path.join(vault_base, folder_name)
    if os.path.exists(batch_vault_path) and folder_name.startswith("STAGED_"):
        try:
            shutil.rmtree(batch_vault_path)
            return True
        except Exception as e:
            print(f"[Vault Error] Failed to delete batch folder {folder_name}: {str(e)}")
            return False
    return False

@eel.expose
def python_load_existing_staged_batches():
    config = load_config()
    vault_base = config.get("vault_dir")
    
    if not os.path.exists(vault_base):
        return []
        
    recovered_batches = []
    for folder_path in glob.glob(os.path.join(vault_base, "STAGED_*")):
        if os.path.isdir(folder_path):
            folder_name = os.path.basename(folder_path)
            file_count = len(glob.glob(os.path.join(folder_path, "*.jpg"))) + len(glob.glob(os.path.join(folder_path, "*.png")))
            
            try:
                date_part = folder_name.split("STAGED_")[1].split("_")[0]
                month_digits, day_digits, year_digits = date_part.split("-")
                date_display = f"{REV_MONTH_MAP.get(month_digits, 'January')} {str(int(day_digits))}, {year_digits}"
            except Exception:
                date_display = "Unknown Date"
            
            # Read saved caption string if file metadata exists
            saved_caption = date_display
            caption_file_path = os.path.join(folder_path, "caption.txt")
            if os.path.exists(caption_file_path):
                try:
                    with open(caption_file_path, "r", encoding="utf-8") as f:
                        saved_caption = f.read().strip()
                except Exception:
                    pass
                
            recovered_batches.append({
                "folderKey": folder_name, 
                "dateDisplay": date_display, 
                "count": file_count,
                "caption": saved_caption
            })
    return sorted(recovered_batches, key=lambda x: x['folderKey'])

@eel.expose
def python_upload_batch(folder_name, caption):
    config = load_config()
    vault_base = config.get("vault_dir")
    
    batch_vault_path = os.path.join(vault_base, folder_name)
    absolute_image_paths = sorted(glob.glob(os.path.join(batch_vault_path, "*.jpg")) + glob.glob(os.path.join(batch_vault_path, "*.png")))
    
    if not absolute_image_paths:
        return False

    print(f"\n--- EXECUTION DEPLOYMENT TRIGGERED FOR {folder_name} ---")
    try:
        upload_success = execute_browser_upload(absolute_image_paths, caption)
        if upload_success:
            new_folder_name = folder_name.replace("STAGED_", "POSTED_")
            posted_vault_path = os.path.join(vault_base, new_folder_name)
            if os.path.exists(posted_vault_path):
                shutil.rmtree(posted_vault_path)
            os.rename(batch_vault_path, posted_vault_path)
            return True
        return False
    except Exception as e:
        print(f"[Error] System runtime crash encountered: {str(e)}")
        return False

if __name__ == "__main__":
    initial_config = load_config()
    os.makedirs(STAGING_DIR, exist_ok=True)
    os.makedirs(initial_config["vault_dir"], exist_ok=True)
    
    # Direct fullscreen window implementation on bootup execution
    eel.start(
        'index.html', 
        mode='chrome', 
        cmdline_args=['--start-maximized']
    )