import json
import shutil
import os
from pathlib import Path

# Import all our custom built blocks
from src.db_mgr import initialize_database, is_already_posted, mark_as_posted
from src.core_picker import get_handpicked_media
from src.ai_agent import generate_dump_caption
from src.uploader import upload_photo_carousel

def run_production_pipeline():
    print("🚀 FIRING UP AUTOMATED INSTAGRAM DUMP PIPELINE 🚀\n")
    
    # 1. Initialize the SQLite structural engine
    initialize_database()
    
    # 2. Extract configurations
    with open("config.json", "r") as config_file:
        config = json.load(config_file)
        backup_path = config["external_drive_path"]
        staging_name = config["staging_folder_name"]
        
    # 3. Handle physical staging directories on the D: drive
    staging_dir = Path("D:/") / staging_name
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)
    
    # 4. Fetch a 20-photo batch
    selected_photos = get_handpicked_media(backup_path)
    if not selected_photos:
        print("❌ Pipeline Stopped: Could not scan or find any photo directories.")
        return

    # --- THE DATABASE CHECK GUARD ---
    # We will test the first image path of this batch against our database records
    if is_already_posted(selected_photos[0]):
        print(f"♻️ Skip: The photo batch for this day has already been posted before! Re-running pipeline...")
        # Recursively call the script again to pick a completely fresh day bucket
        return run_production_pipeline()

    print(f"🎯 Successfully isolated a fresh batch of {len(selected_photos)} photos!")
    print(f"📁 Staging files cleanly in: {staging_dir}")
    
    # 5. Physically duplicate files to our local HDD staging area
    for photo_path in selected_photos:
        destination_file = staging_dir / photo_path.name
        shutil.copy2(photo_path, destination_file)
        
    print("✅ Staging phase complete.")
    
    # 6. Fire off the AI Copywriter analysis request
    first_image = selected_photos[0]
    print(f"\n🤖 Beaming {first_image.name} context parameters to Gemini AI...")
    caption = generate_dump_caption(first_image)
    
    print("\n==================================================")
    print("✨ TARGET INSTAGRAM CAPTION CREATED ✨")
    print("==================================================")
    print(caption)
    print("==================================================")
    
    # 7. Execute the Live Instagram Deployment Stream
    # ⚠️ NOTE: If you aren't ready to post live to your account yet, 
    # you can comment out the lines below to do a dry-run test!
    print("\n🌐 Preparing upload stream payload to Instagram servers...")
    upload_success = upload_photo_carousel(selected_photos, caption)
    
    if upload_success:
        print("\n💾 Success! Writing this batch profile data to tracker.db...")
        # 8. Commit the paths to database storage so they are permanently logged
        for photo_path in selected_photos:
            mark_as_posted(photo_path)
        print("🗄️ Database records synchronized cleanly. Pipeline closed down successfully!")
    else:
        print("\n❌ Pipeline Interrupted: Post execution engine failed to broadcast.")

if __name__ == "__main__":
    run_production_pipeline()