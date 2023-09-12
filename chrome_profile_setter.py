from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import PyInstaller
import time

chrome_profile_path = ''
with open("config.txt", "r") as config_file:
    lines = config_file.readlines()
for line in lines:
    if "CHROME_PROFILE_PATH" in line:
        chrome_profile_path = line.split("=")[1].strip().strip('"')

options = Options()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
options.add_argument("--log-level=3")
options.add_argument('--start-maximized')
options.add_argument("user-data-dir=" + chrome_profile_path)
# options.add_argument("--headless")
driver = webdriver.Chrome(options=options)

driver.get('https://www.b2b-center.ru/')

while True:
    time.sleep(300)
