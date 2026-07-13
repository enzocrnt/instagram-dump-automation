import os
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def upload_photo_carousel(image_paths, caption):
    if not image_paths:
        print("❌ Upload Error: No image paths provided.")
        return False

    print("🌐 Spinning up native Selenium Chrome Driver with dedicated pipeline profile...")
    
    local_profile_path = Path("database/selenium_chrome_profile").resolve()
    
    chrome_options = Options()
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--start-maximized")
    
    chrome_options.add_argument(f"user-data-dir={local_profile_path}")
    chrome_options.add_argument("--profile-directory=AutomationProfile")
    
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    try:
        print("⏳ Step A: Attempting to initialize the Chrome binary...")
        driver = webdriver.Chrome(options=chrome_options)
        
        print("⏳ Step B: Chrome binary successfully hooked! Setting up wait timers...")
        wait = WebDriverWait(driver, 15)
        manual_login_wait = WebDriverWait(driver, 300) 

        # 1. Go to Instagram
        print("🌐 Step C: Directing Chrome to load Instagram...")
        driver.get("https://www.instagram.com/")
        time.sleep(5)

        # 2. Authentication Check
        print("⏳ Checking authentication status...")
        create_btn = manual_login_wait.until(EC.presence_of_element_located((By.XPATH, "//*[@aria-label='New post' or @aria-label='Create']")))
        print("🔓 Authenticated session detected!")
                
        # 3. Navigate to the Upload Interface (Handling sub-menu)
        print("📤 Opening the Create Post menu...")
        create_btn.click()
        time.sleep(2)
        
        print("📑 Selecting 'Post' option from sub-menu...")
        # Locates the specific "Post" text button in the popup overlay
        post_sub_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Post')]")))
        post_sub_btn.click()
        
       # 4. Inject the File Paths
        print("📁 Injecting local files into the DOM...")
        time.sleep(3)  # Give the upload modal a moment to fully settle its DOM components
        
        string_paths = "\n".join([str(Path(p).resolve()) for p in image_paths])
        
        # A more relaxed XPATH that targets any file input inside the modal wrapper
        file_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
        
        # Forcefully push the paths
        file_input.send_keys(string_paths)
        time.sleep(3)  # Give the browser a moment to process the file stream
        
        # 5. Click through the 'Next' buttons
        print("⏩ Advancing through crop and filter screens...")
        next_btn_1 = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Next')]")))
        next_btn_1.click()
        time.sleep(1)
        
        next_btn_2 = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Next')]")))
        next_btn_2.click()
        
      # 6. Write the Caption
        print("📝 Interacting with the caption window...")
        # Target the main focus container
        caption_box = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Write a caption...' and @contenteditable='true']")))
        caption_box.click()
        time.sleep(1)
        
        print("⌨️ Executing native keyboard stream injection...")
        # We clear any ghost text and focus the container via execution script first
        driver.execute_script("arguments[0].focus();", caption_box)
        time.sleep(1)

        # Send the caption using action chains to mimic human typing rhythm 
        # which forces the Lexical framework to initialize the inner elements
        from selenium.webdriver.common.action_chains import ActionChains
        actions = ActionChains(driver)
        actions.move_to_element(caption_box)
        actions.click()
        
        # We use a fallback injection if send_keys panics over the emoji
        try:
            actions.send_keys(caption)
            actions.perform()
        except Exception:
            print("⚠️ Standard keyboard stream blocked by emoji encoding. Using character array parsing...")
            # If it panics due to the BMP emoji issue, we inject via clipboard script execution targeting focus
            js_paste = """
            var el = arguments[0];
            el.focus();
            document.execCommand('insertText', false, arguments[1]);
            """
            driver.execute_script(js_paste, caption_box, caption)

        # Dispatch standard input verification events to seal the deal
        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", caption_box)
        time.sleep(2)
        
       # 7. Share the Post
        print("🚀 Clicking Share...")
        share_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Share')]")))
        share_btn.click()
        
        # Wait for the upload network stream to complete (up to 30 seconds for heavy dumps)
        print("⏳ Waiting for Instagram to process the upload payload...")
        
        success = False
        for _ in range(30):
            # Win Condition A: We got redirected straight to the new post page
            if "/p/" in driver.current_url:
                success = True
                break
            # Win Condition B: The success modal popped up
            try:
                if driver.find_elements(By.XPATH, "//img[@alt='Animated checkmark']"):
                    success = True
                    break
            except:
                pass
            time.sleep(1)
            
        if success:
            print("✅ Post successfully deployed to timeline!")
            time.sleep(3)
            driver.quit()
            return True
        else:
            raise Exception("Upload timed out without confirming redirection or checkmark graphic.")

    except Exception as e:
        print(f"❌ Critical error during Web Upload process: {e}")
        try:
            driver.quit()
        except:
            pass
        return False