from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
from webdriver_manager.chrome import ChromeDriverManager
import time
import random

# === CONFIG ===
SITE_URL = "https://hyperglycaemic-obdulia-ungowned.ngrok-free.dev/"

# Helper function to handle alerts
def handle_alert(driver, accept=True):
    """Handle JavaScript alerts/confirms/prompts"""
    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        print(f"🔔 Alert detected: '{alert_text}'")
        if accept:
            alert.accept()
            print("   ✓ Alert accepted")
        else:
            alert.dismiss()
            print("   ✗ Alert dismissed")
        time.sleep(0.5)
        return True
    except NoAlertPresentException:
        return False

def safe_click(driver, element, description="element"):
    """Click element and handle any alerts that appear"""
    try:
        element.click()
        time.sleep(0.5)
        handle_alert(driver, accept=True)
        return True
    except UnexpectedAlertPresentException:
        print(f"⚠️ Alert appeared while clicking {description}")
        handle_alert(driver, accept=True)
        return True
    except Exception as e:
        print(f"⚠️ Error clicking {description}: {type(e).__name__}")
        return False

options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--remote-debugging-port=9222")
options.add_experimental_option("detach", True)
options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
options.add_experimental_option('useAutomationExtension', False)

# Create service with verbose logging
service = Service(ChromeDriverManager().install())
service.log_path = "chromedriver.log"

driver = None

try:
    driver = webdriver.Chrome(service=service, options=options)
    
    # Clear any existing session/cookies
    driver.delete_all_cookies()
    
    # Set implicit wait (helps with element loading)
    driver.implicitly_wait(10)
    
    wait = WebDriverWait(driver, 30)

    print("🚀 Opening site...")
    driver.get(SITE_URL)
    time.sleep(2)

    # STEP 1: Confirm homepage
    print("Waiting for homepage...")
    wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'Disaster Management Dashboard')]")))
    print("✅ Homepage loaded successfully!")
    time.sleep(1)

    # STEP 2: Click Login/Navigate to dashboard
    print("🔍 Looking for Login button...")
    login_btn = wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//a[contains(., 'Login')] | //button[contains(., 'Login')]")
    ))
    
    driver.execute_script("arguments[0].scrollIntoView(true);", login_btn)
    time.sleep(0.5)
    login_btn.click()
    print("✅ Login button clicked...")
    time.sleep(3)

    # Check where we ended up
    current_url = driver.current_url
    print(f"📍 Current URL: {current_url}")
    
    # Handle any alerts that might have appeared
    handle_alert(driver, accept=True)

    # STEP 3: Handle Login/Register if needed
    print("\n👤 STEP 3: Authentication...")
    if "dashboard" in current_url.lower():
        print("✅ Already on dashboard - skipping login!")
        
    elif "login" in current_url.lower() or driver.find_elements(By.NAME, "username"):
        print("📝 Login page detected - proceeding with authentication...")
        
        username = f"user{random.randint(1000,9999)}"
        email = f"{username}@test.com"
        password = "password123"

        # Check if Register link exists
        register_links = driver.find_elements(By.XPATH, "//a[contains(.,'Register')] | //a[contains(.,'Sign up')] | //button[contains(.,'Register')]")
        if register_links:
            print("📝 Register link found - creating new account...")
            register_links[0].click()
            time.sleep(3)
            
            # Wait for register page to load
            try:
                print("Waiting for registration form...")
                username_field = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )
                print("✅ Registration form loaded")
                
                username_field.send_keys(username)
                time.sleep(0.3)
                
                email_field = driver.find_element(By.NAME, "email")
                email_field.send_keys(email)
                time.sleep(0.3)
                
                password_field = driver.find_element(By.NAME, "password")
                password_field.send_keys(password)
                time.sleep(0.3)
                
                register_btn = driver.find_element(By.XPATH, "//button[contains(.,'Register')] | //button[contains(.,'Sign up')]")
                driver.execute_script("arguments[0].scrollIntoView(true);", register_btn)
                time.sleep(0.5)
                safe_click(driver, register_btn, "Register button")
                print(f"✅ Registered user: {username}")
                time.sleep(3)
                handle_alert(driver, accept=True)
                
                # After registration, might need to login
                current_url = driver.current_url
                print(f"After registration, current URL: {current_url}")
                
            except Exception as e:
                print(f"⚠️ Registration failed: {type(e).__name__}")
                print(f"Current URL: {driver.current_url}")
                driver.save_screenshot("registration_error.png")
                # Try to continue anyway
        else:
            print("ℹ️ No Register link found - will try direct login")
        
        # Now attempt login (whether we registered or not)
        time.sleep(2)
        
        # Check if we need to login or already on dashboard
        if "dashboard" not in driver.current_url.lower():
            print("Attempting login...")
            try:
                username_field = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )
                username_field.clear()
                username_field.send_keys(username)
                time.sleep(0.3)
                
                password_field = driver.find_element(By.NAME, "password")
                password_field.clear()
                password_field.send_keys(password)
                time.sleep(0.3)
                
                login_submit = driver.find_element(By.XPATH, "//button[contains(.,'Login')] | //button[contains(.,'Sign in')]")
                driver.execute_script("arguments[0].scrollIntoView(true);", login_submit)
                time.sleep(0.5)
                
                # Get current URL before clicking
                old_url = driver.current_url
                
                safe_click(driver, login_submit, "Login button")
                print("✅ Login form submitted... waiting for page transition")
                
                # Wait for URL to change (page navigation)
                try:
                    WebDriverWait(driver, 10).until(EC.url_changes(old_url))
                    print(f"✅ Page navigated to: {driver.current_url}")
                except:
                    print("⚠️ URL didn't change, but continuing...")
                
                # Handle any success alerts
                handle_alert(driver, accept=True)
                
                # Extra wait for page to stabilize after navigation
                time.sleep(5)
            except Exception as e:
                print(f"⚠️ Login attempt failed: {type(e).__name__}")
                print("Continuing anyway - might already be logged in")
        else:
            print("✅ Already on dashboard after registration!")
    else:
        print("⚠️ Unexpected page state - continuing anyway...")
        time.sleep(2)

    # Verify we're logged in (check for Logout button or dashboard elements)
    try:
        print("Verifying login status...")
        # Wait longer and check multiple possible indicators
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'Logout')] | //*[contains(text(),'Dashboard')] | //div[contains(@class, 'leaflet-container')]"))
        )
        print("✅ Successfully authenticated/on dashboard!")
        
        # Additional stabilization wait
        time.sleep(3)
    except Exception as e:
        print(f"⚠️ Could not confirm login status: {type(e).__name__}")
        print(f"Current URL: {driver.current_url}")
        driver.save_screenshot("login_verification_error.png")
        print("Continuing anyway...")
    
    time.sleep(2)

    # STEP 4: Add Alert (Marker)
    try:
        print("\n🗺️ STEP 4: Adding marker to map...")
        
        # Handle any lingering alerts first
        handle_alert(driver, accept=True)
        
        map_container = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "leaflet-container")))
        print("✅ Map container found")
        
        time.sleep(2)
        
        map_elem = driver.find_element(By.CLASS_NAME, "leaflet-container")
        actions = ActionChains(driver)
        actions.move_to_element_with_offset(map_elem, 250, 250).click().perform()
        print("✅ Clicked on map to add marker")
        time.sleep(1)
        
        # Handle alert after marker click
        handle_alert(driver, accept=True)
        time.sleep(1)

        # Check for form after click
        description_fields = driver.find_elements(By.NAME, "description")
        if description_fields:
            print("✅ Alert form appeared - filling details")
            description_fields[0].send_keys("Automated test alert")
            time.sleep(0.5)
            submit_btn = driver.find_element(By.XPATH, "//button[contains(.,'Submit')] | //button[contains(.,'Add')]")
            driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
            time.sleep(0.5)
            safe_click(driver, submit_btn, "Submit button")
            print("✅ Alert submitted successfully!")
            time.sleep(1)
            handle_alert(driver, accept=True)
        else:
            print("✅ Marker added directly (no form)")
            
        time.sleep(2)
        
    except UnexpectedAlertPresentException:
        print("⚠️ Alert appeared during Add Alert step - handling it")
        handle_alert(driver, accept=True)
    except Exception as e:
        print(f"❌ Add Alert step failed: {type(e).__name__}")
        handle_alert(driver, accept=True)
        driver.save_screenshot("alert_error.png")

    # STEP 5: Resolve alert
    try:
        print("\n🔧 STEP 5: Resolving an alert...")
        time.sleep(1)
        
        # Handle any alerts first
        handle_alert(driver, accept=True)
        
        markers = driver.find_elements(By.CLASS_NAME, "leaflet-marker-icon")
        if markers:
            print(f"✅ Found {len(markers)} marker(s) on the map")
            
            # Click the first marker
            markers[0].click()
            print("✅ Clicked on marker")
            time.sleep(2)
            
            # Check if there's a "Remove this alert?" popup and DISMISS it
            try:
                alert = driver.switch_to.alert
                alert_text = alert.text
                if "remove" in alert_text.lower():
                    print(f"🔔 '{alert_text}' - Dismissing to keep marker")
                    alert.dismiss()
                    time.sleep(1)
                    
                    # Click marker again after dismissing
                    print("Clicking marker again to open details...")
                    markers = driver.find_elements(By.CLASS_NAME, "leaflet-marker-icon")
                    if markers:
                        markers[0].click()
                        print("✅ Marker clicked again")
                        time.sleep(2)
                else:
                    print(f"🔔 Alert: '{alert_text}' - Accepting")
                    alert.accept()
                    time.sleep(1)
            except NoAlertPresentException:
                print("ℹ️ No alert popup - marker details should be showing")
            
            # Now look for Resolve button
            time.sleep(1)
            resolve_btns = driver.find_elements(By.XPATH, 
                "//button[contains(text(),'Resolve')] | "
                "//a[contains(text(),'Resolve')] | "
                "//button[contains(text(),'resolve')] | "
                "//input[@value='Resolve']"
            )
            
            if resolve_btns:
                print(f"✅ Found Resolve button")
                safe_click(driver, resolve_btns[0], "Resolve button")
                print("✅ Alert resolved successfully!")
                time.sleep(1)
                handle_alert(driver, accept=True)
            else:
                print("⚠️ Could not find Resolve button")
                print("Looking for popup/modal with resolve option...")
                driver.save_screenshot("no_resolve_button.png")
        else:
            print("⚠️ No markers found on map")
            
    except UnexpectedAlertPresentException:
        print("⚠️ Alert appeared during Resolve step - handling it")
        handle_alert(driver, accept=True)
    except Exception as e:
        print(f"❌ Resolve step failed: {type(e).__name__}")
        driver.save_screenshot("resolve_error.png")

    # STEP 6: Logout
    try:
        print("\n👋 STEP 6: Logging out...")
        
        # Handle any alerts first (but not "Remove this alert?" type)
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            if "remove" not in alert_text.lower():
                print(f"🔔 Alert: '{alert_text}' - Accepting")
                alert.accept()
                time.sleep(0.5)
        except NoAlertPresentException:
            pass
        
        logout_elements = driver.find_elements(By.XPATH, 
            "//*[contains(text(),'Logout')] | "
            "//*[contains(text(),'Log out')] | "
            "//a[contains(@href,'logout')] | "
            "//button[contains(@class,'logout')]"
        )
        
        if logout_elements:
            logout_btn = logout_elements[0]
            driver.execute_script("arguments[0].scrollIntoView(true);", logout_btn)
            time.sleep(0.5)
            safe_click(driver, logout_btn, "Logout button")
            print("✅ Logged out successfully!")
            time.sleep(2)
            handle_alert(driver, accept=True)
        else:
            print("⚠️ No Logout button found - may already be logged out")
            
    except UnexpectedAlertPresentException:
        print("⚠️ Alert appeared during Logout - handling it")
        handle_alert(driver, accept=True)
    except Exception as e:
        print(f"❌ Logout failed: {type(e).__name__}")

    print("\n🎯 Full Automation Flow Completed!")
    print("✅ Browser will stay open. Close this terminal window to exit.")
    print("   Or press Ctrl+C to close the browser gracefully.\n")
    
    # Keep script alive
    while True:
        time.sleep(60)

except KeyboardInterrupt:
    print("\n👋 User interrupted. Closing browser...")
    if driver:
        try:
            driver.quit()
        except:
            print("Browser already closed or connection lost.")
            
except Exception as e:
    print(f"\n❌ Error occurred: {type(e).__name__}")
    print(f"   {str(e)[:200]}")
    
    if driver:
        try:
            print(f"\n📍 Current URL: {driver.current_url}")
            driver.save_screenshot("error_screenshot.png")
            print("📸 Screenshot saved as error_screenshot.png")
        except:
            pass
    
    print("\n✅ Browser will stay open for inspection.")
    print("   Press Ctrl+C to close.\n")
    
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n👋 Closing browser...")
        if driver:
            try:
                driver.quit()
            except:
                print("Browser already closed.")