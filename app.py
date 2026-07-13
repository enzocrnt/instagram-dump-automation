import eel
import os
import shutil
import glob
import random

# Import your native Selenium engine from your source directory files
from src.uploader import upload_photo_carousel as execute_browser_upload

# Base path configurations shifted entirely to your internal hard drive (D:)
ARCHIVE_BASE_DIR = r"D:\2024_Backup"
STAGING_DIR = os.path.join(os.path.dirname(__file__), 'web', 'staging')
VAULT_DIR = r"D:\IG_Dump_Staging" 

MONTH_FOLDER_MAP = {
    "January": "01-00-2024 (Jan. 2024)", "February": "02-00-2024 (Feb. 2024)",
    "March": "03-00-2024 (Mar. 2024)", "April": "04-00-2024 (Apr. 2024)",
    "May": "05-00-2024 (May 2024)", "June": "06-00-2024 (Jun. 2024)",
    "July": "07-00-2024 (Jul. 2024)", "August": "08-00-2024 (Aug. 2024)",
    "September": "09-00-2024 (Sept. 2024)", "October": "10-00-2024 (Oct. 2024)",
    "November": "11-00-2024 (Nov. 2024)", "December": "12-00-2024 (Dec. 2024)"
}

MONTH_NUM_MAP = {
    "January": "01", "February": "02", "March": "03", "April": "04",
    "May": "05", "June": "06", "July": "07", "August": "08",
    "September": "09", "October": "10", "November": "11", "December": "12"
}

# Reverse mapping to turn folder digits back into human-readable text for the UI
REV_MONTH_MAP = {v: k for k, v in MONTH_NUM_MAP.items()}

eel.init('web')

def clear_staging_directory():
    """Removes any stale images inside the web staging area to save space."""
    if os.path.exists(STAGING_DIR):
        shutil.rmtree(STAGING_DIR)
    os.makedirs(STAGING_DIR, exist_ok=True)

@eel.expose
def python_reroll_day_pool(month, day):
    """Isolates files matching the exact selected date string and stages them."""
    clear_staging_directory()
    
    folder_name = MONTH_FOLDER_MAP.get(month)
    month_digits = MONTH_NUM_MAP.get(month)
    day_digits = f"{int(day):02d}"
    
    target_pics_path = os.path.join(ARCHIVE_BASE_DIR, folder_name, "Pics")
    
    if not os.path.exists(target_pics_path):
        print(f"[Error] Directory not found: {target_pics_path}")
        return []
        
    search_pattern = f"IMG_2024{month_digits}{day_digits}_*.jpg"
    full_search_string = os.path.join(target_pics_path, search_pattern)
    matched_file_paths = glob.glob(full_search_string)
    
    if not matched_file_paths:
        return []

    random.shuffle(matched_file_paths)
    final_selection_pool = matched_file_paths[:10]
    
    staged_filenames = []
    for file_path in final_selection_pool:
        filename = os.path.basename(file_path)
        destination = os.path.join(STAGING_DIR, filename)
        try:
            shutil.copy2(file_path, destination)
            staged_filenames.append(filename)
        except Exception as e:
            print(f"[Error] Failed to stage file {filename}: {str(e)}")
            
    return staged_filenames

@eel.expose
def python_save_to_standby(month, day, filenames):
    """Moves chosen files into an isolated folder named by its date prefix."""
    month_digits = MONTH_NUM_MAP.get(month)
    day_digits = f"{int(day):02d}"
    
    date_str = f"{month_digits}-{day_digits}-2024"
    folder_name = f"STAGED_{date_str}"
    batch_vault_path = os.path.join(VAULT_DIR, folder_name)
    
    counter = 1
    while os.path.exists(batch_vault_path):
        folder_name = f"STAGED_{date_str}_{counter}"
        batch_vault_path = os.path.join(VAULT_DIR, folder_name)
        counter += 1
        
    os.makedirs(batch_vault_path, exist_ok=True)
    
    vaulted_paths = []
    for fname in filenames:
        source_file = os.path.join(STAGING_DIR, fname)
        destination_file = os.path.join(batch_vault_path, fname)
        
        if os.path.exists(source_file):
            shutil.copy2(source_file, destination_file)
            vaulted_paths.append(destination_file)
            
    print(f"[Vault Log] Locked down {len(vaulted_paths)} files into: {batch_vault_path}")
    return folder_name

@eel.expose
def python_load_existing_staged_batches():
    """Scans the hard drive directory for folders left un-uploaded and reconstructs the UI queue rows."""
    if not os.path.exists(VAULT_DIR):
        return []
        
    recovered_batches = []
    # Search for any directories starting with STAGED_
    search_path = os.path.join(VAULT_DIR, "STAGED_*")
    
    for folder_path in glob.glob(search_path):
        if os.path.isdir(folder_path):
            folder_name = os.path.basename(folder_path)
            
            # Count the files inside this directory
            file_count = len(glob.glob(os.path.join(folder_path, "*.jpg")))
            
            # Deconstruct the date from the folder name (e.g., STAGED_01-05-2024 -> 01, 05)
            try:
                date_part = folder_name.split("STAGED_")[1].split("_")[0]
                month_digits, day_digits, _ = date_part.split("-")
                
                month_name = REV_MONTH_MAP.get(month_digits, "January")
                day_display = str(int(day_digits)) # Drop leading zero for text display
                date_display = f"{month_name} {day_display}"
            except Exception:
                date_display = "Unknown Date"
                
            recovered_batches.append({
                "folderKey": folder_name,
                "dateDisplay": date_display,
                "count": file_count
            })
            
    # Sort them so they line up in chronological order based on the folder string
    return sorted(recovered_batches, key=lambda x: x['folderKey'])

@eel.expose
def python_upload_batch(folder_name, caption):
    """Launches the uploader routine targeting the folder name, renaming it to POSTED_ on success."""
    batch_vault_path = os.path.join(VAULT_DIR, folder_name)
    absolute_image_paths = sorted(glob.glob(os.path.join(batch_vault_path, "*.jpg")))
    
    if not absolute_image_paths:
        print(f"[Error] No files found in vault for {folder_name} to upload.")
        return False

    print(f"\n--- LAUNCHING AUTOMATION ENGINE FOR {folder_name} ---")
    print(f"Absolute Image Payload: {absolute_image_paths}")
    print(f"Caption Content to Inject: '{caption}'")
    
    try:
        upload_success = execute_browser_upload(absolute_image_paths, caption)
        
        if upload_success:
            new_folder_name = folder_name.replace("STAGED_", "POSTED_")
            posted_vault_path = os.path.join(VAULT_DIR, new_folder_name)
            
            if os.path.exists(posted_vault_path):
                shutil.rmtree(posted_vault_path)
                
            os.rename(batch_vault_path, posted_vault_path)
            print(f"[Vault Log] Status updated successfully! Moved to: {posted_vault_path}")
            return True
        else:
            print(f"[Error] Selenium runner reported a failure during posting.")
            return False
            
    except Exception as e:
        print(f"[Error] System crash encountered during automated browser routine: {str(e)}")
        return False

if __name__ == "__main__":
    os.makedirs(STAGING_DIR, exist_ok=True)
    os.makedirs(VAULT_DIR, exist_ok=True)
    eel.start('index.html', size=(1200, 750))