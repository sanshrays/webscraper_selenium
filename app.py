from flask import Flask, render_template, request, jsonify
import logging
import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By as BY
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from urllib.parse import urlparse

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

color_schemes = []

def initialize_driver(path, website_link):
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--window-size=1920,1080')
    service = Service(executable_path=path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()
    driver.get(website_link)
    return driver

def get_domain(website_link):
    parsed_url = urlparse(website_link)
    domain = parsed_url.netloc
    return domain

def get_logoURL_from_website(domain):
    clearbit_url = f"https://logo.clearbit.com/{domain}"
    response = requests.get(clearbit_url)
    if response.status_code == 200:
        return clearbit_url
    else:
        return None

def get_favicon_url(driver):
    try:
        favicon = WebDriverWait(driver, 5).until(EC.presence_of_element_located((BY.XPATH, './/link[(@rel="icon") or (@rel="shortcut icon")]')))
        favicon_url = favicon.get_attribute('href')
        return favicon_url
    except Exception as e:
        logging.error(f"Error locating the favicon: {e}")
    return None

def extract_text_color(driver):
    texts = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((BY.XPATH, './/p |.//span |.//div |.//body')))
    text_colors = {}
        
    for text in texts:
        color = driver.execute_script("return window.getComputedStyle(arguments[0]).color;", text)
        text_colors[color] = text_colors.get(color, 0) + 1
    
    if text_colors:
        dominant_text_color = max(text_colors, key=text_colors.get)
        logging.info(f"Dominant text color: {dominant_text_color}")
        return dominant_text_color
    else:
        logging.info("No text colors found")
        return None

def extract_color_schemes(driver):
    button_xpaths = [
        './/button',
        './/a[contains(@class,"button") or contains(@class,"btn") or contains(@class,"submit")]',
        './/a[contains(@class,"Button") or contains(@class,"Submit")]',
        './/span[contains(@class,"button") or contains(@class,"btn") or contains(@class,"submit")]',
        './/span[contains(@class,"Button") or contains(@class,"Submit")]',
        './/div[contains(@class,"button") or contains(@class,"btn") or contains(@class,"submit")]',
        './/div[contains(@class,"Button") or contains(@class,"Submit")]',
        './/p[contains(@class,"button") or contains(@class,"btn") or contains(@class,"submit")]',
        './/p[contains(@class,"Button") or contains(@class,"Submit")]',
        './/input[@type="submit" or @type="button" or @type="reset"]',
    ]

    processed_elements = set()
    button_background_colors = set()

    for xpath in button_xpaths:
        try:
            buttons = WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((BY.XPATH, xpath)))
            for button in buttons:
                outermost_button = button
                while True:
                    parent = button.find_element(by="xpath", value='..')
                    if any(parent.get_attribute('class').find(cls) != -1 for cls in ['button', 'btn', 'Button', 'submit', 'Submit']):
                        button = parent
                    else:
                        break
                outermost_button = button

                if outermost_button in processed_elements:
                    continue

                processed_elements.add(outermost_button)
                background_color = driver.execute_script("return window.getComputedStyle(arguments[0]).backgroundColor;", outermost_button)
                border_color = driver.execute_script("return window.getComputedStyle(arguments[0]).borderColor;", outermost_button)
                button_background_colors.add(border_color)
                button_background_colors.add(background_color)

        except Exception as e:
            logging.error(f"XPath '{xpath}' not found or an error occurred: {e}")

    return list(button_background_colors)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    website_link = request.form.get('website_link')
    path = '/Users/SanshrayNandala/Downloads/chromedriver-win64/chromedriver-win64/chromedriver.exe'
    driver = initialize_driver(path, website_link)

    domain = get_domain(website_link)
    logo_url = get_logoURL_from_website(domain)
    favicon_url = get_favicon_url(driver)
    
    # if logo_url or favicon_url:
    #     df = pd.DataFrame({'logo_url': [logo_url], 'favicon_url': [favicon_url]})
    #     df.to_csv(f'{domain}_logo_urls.csv', index=False)
    #     logging.info(f"Logo and favicon URLs saved to {domain}_logo_urls.csv")
        
        
    background_colors = extract_color_schemes(driver)
    try:
        dominant_text_color = extract_text_color(driver)
    except StaleElementReferenceException as e:
        try:
            driver.switch_to.frame(1)
            dominant_text_color = extract_text_color(driver)
        except Exception as e:
            dominant_text_color = None    
            logging.error(f"Error while locating text colors: {e}")
    
    # if background_colors or dominant_text_color:
    #     df = pd.DataFrame({'background_colors': [background_colors], 'dominant_text_color': [dominant_text_color]})
    #     df.to_csv(f'{domain}_color_schemes.csv', index=False)
    #     logging.info(f"Color schemes saved to {domain}_color_schemes.csv")
    
    

    driver.quit()

    return jsonify({
        'logo_url': logo_url,
        'favicon_url': favicon_url,
        'background_colors': background_colors,
        'dominant_text_color': dominant_text_color
    })

if __name__ == '__main__':
    app.run(debug=True)
