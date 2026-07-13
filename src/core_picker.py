import random
from pathlib import Path
from collections import defaultdict

def get_handpicked_media(external_drive_path, target_year="2024"):
    # 1. Point to the year folder
    year_dir = Path(external_drive_path)
    if not year_dir.exists():
        return []

    # 2. Pick a random month
    month_folders = [item for item in year_dir.iterdir() if item.is_dir() and item.name.split('-')[0].isdigit()]
    if not month_folders:
        return []
    
    selected_month = random.choice(month_folders)
    
    # 3. Look in the 'Pics' folder and group files by date
    pics_dir = selected_month / "Pics"
    if not pics_dir.exists():
        return []

    # This creates a dictionary where: Key = DateString (e.g., '20240201'), Value = List of Files
    date_buckets = defaultdict(list)
    valid_extensions = {'.jpg', '.jpeg', '.png'}
    
    for file in pics_dir.iterdir():
        if file.is_file() and file.suffix.lower() in valid_extensions:
            # Filename example: IMG_20240201_xxxx.jpg
            # We split by '_' to get the date part at index 1
            date_part = file.name.split('_')[1] 
            date_buckets[date_part].append(file)

    if not date_buckets:
        return []

    # 4. Pick one random date bucket
    random_date = random.choice(list(date_buckets.keys()))
    files_for_day = date_buckets[random_date]
    
    # 5. Take up to 20 photos (or all of them if less than 20)
    num_to_pick = min(len(files_for_day), 20)
    return random.sample(files_for_day, num_to_pick)