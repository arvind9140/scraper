import os
import time
from flask import Flask, request, jsonify
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from linkedin_scraper import actions
from linkedin_scraper.person import Person
from linkedin_scraper.company import Company
from bs4 import BeautifulSoup
import html2text
import re
from urllib.parse import urlparse
from selenium.webdriver.support import expected_conditions as EC


app = Flask(__name__)
token = os.getenv("TOKEN")

chrome_options = Options()
chrome_options.headless = False  





def setup_selenium():
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    return driver
def fetch_html_selenium(url):
    driver = setup_selenium()
    try:
        driver.get(url)
        time.sleep(5) 
       
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)  
        html = driver.page_source
        return html
    except Exception as e:
        return {"error": str(e)}
    finally:
        driver.quit()

def clean_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    for element in soup.find_all(["header", "footer"]):
        element.decompose()  

    return str(soup)

def html_to_markdown_with_readability(html_content):
    cleaned_html = clean_html(html_content)
    markdown_converter = html2text.HTML2Text()
    markdown_converter.ignore_links = False
    markdown_content = markdown_converter.handle(cleaned_html)

    return markdown_content

def scrape_linkedin_profile(email, password, linkedin_url):
    
    driver = setup_selenium()
    try:
        actions.login(driver, email, password)
        person = Person(linkedin_url, driver=driver)
    finally:
        driver.quit()
    return person.__dict__

def scrape_linkedin_company(email, password, linkedin_url):
    
    driver = setup_selenium()
    
    try:
        actions.login(driver, email, password)
        company = Company(linkedin_url,driver=driver)
    finally:
        driver.quit()  
    return company.__dict__

def is_linkedin_url(url):
    """
    Checks if the URL belongs to LinkedIn.
    
    Args:
    - url (str): The URL to check
    
    Returns:
    - bool: True if the URL is from LinkedIn, False otherwise
    """
    linkedin_pattern = r"https:\/\/(www\.)?linkedin\.com\/.*"
    
    if re.match(linkedin_pattern, url):
        return True
    return False


def is_valid_url(url):
    """
    Validates if the URL is a valid web address (either LinkedIn or non-LinkedIn).
    
    Args:
    - url (str): The URL to validate
    
    Returns:
    - bool: True if the URL is a valid web URL
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])  
    except ValueError:
        return False
@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.json
    url = data.get('url')
    email = os.getenv("LINKEDIN_USER")
    password = os.getenv("LINKEDIN_PASSWORD")
    if not email or not password:
        return jsonify({"error": "Email and password must be set in environment variables"}), 400
    
    if not url:
        return jsonify({"error": "LinkedIn URL is required"}), 400
    
    try:
        data= None
        
        if is_linkedin_url(url):
            if "linkedin.com/company/" in url:
                data = scrape_linkedin_company(email, password, url)
                
                
            else:    
                data = scrape_linkedin_profile(email, password, url)
                
        elif  is_valid_url(url):
            raw_html = fetch_html_selenium(url)

            data = html_to_markdown_with_readability(raw_html)
        else:
            return jsonify({"error": "Invalid URL"}), 400
        
        initializ_url = 'https://colonelz.prod.devai.initz.run/initializ/v1/ai/chat'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        data = {

            "model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an experienced Sales Development Representative (SDR) at **Initializ**. Your task is to create a personalized outreach strategy for a prospect based on their LinkedIn profile, focusing on their current role, industry, and company. The strategy should demonstrate a deep understanding of both **Initializ's offerings** and the prospect's potential needs. Begin by summarizing the prospects current position, including their company and key responsibilities, and ensure you focus on their most recent experience, which should be indicated by a date range ending with present. Do not include information from older roles unless it is explicitly relevant. Next, identify **three key challenges** the prospect’s company is likely facing, aligning these challenges with **Initializ's value propositions** that are specific to the prospect's role (e.g., Director of Information Technology). For each challenge, explain how **Initializ** can address the need, providing clear and specific solutions that benefit both the company and the prospect's role. Offer a concrete example of how **Initializ** could solve a unique challenge for the company, ensuring that the example is highly relevant to the industry or organizational structure. Lastly, identify a recent newsworthy event or development related to the company or the prospect's role, and explain how it connects to the challenges or priorities identified earlier, demonstrating how **Initializ** can help in the context of these recent developments.",
                    
                    
                },
                
                
                {
                    "role": "user",
                    "content": f"Summarize  the information from the LinkedIn profile details '{data}'",
                }
            ],
            "max_tokens": 5000,
            "temperature": 0.7,
            "stream": False,
            # "stream": True

        }
        response = requests.post(initializ_url, headers=headers, json=data)
        
        return jsonify(response.json()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8000)

