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
        data_response = None
        if is_linkedin_url(url):
            if "linkedin.com/company/" in url:
                data_response = scrape_linkedin_company(email, password, url)
                system_message = f"You are an experienced Sales Development Representative (SDR) at **Initializ**. Your task is to create a personalized outreach strategy for a prospect based on their company profile, focusing on the company's industry, key challenges, and goals. The company is '{data_response.get('name')}', and they are in the {data_response.get('industry')} industry. Begin by summarizing the company's main challenges and priorities."
                user_message = f"Summarize the information from the LinkedIn company profile of '{data_response.get('name')}' in the {data_response.get('industry')} industry. Highlight the company's challenges and any relevant news or events."

            else:    
                data_response = scrape_linkedin_profile(email, password, url)
                
                system_message = f"You are an experienced Sales Development Representative (SDR) at **Initializ**. Your task is to create a personalized outreach strategy for a prospect based on their LinkedIn profile, focusing on their current role, industry, and company. The prospect is {data_response.get('name')}, working as {data_response.get('title')} at {data_response.get('company_name')}. Begin by summarizing the prospect's current role and responsibilities at {data_response.get('company_name')}, including any recent experience."

                user_message = f"Summarize the information from the LinkedIn profile of '{data_response.get('name')}' who is working as {data_response.get('title')} at {data_response.get('company_name')}. Focus on their most recent experience and any relevant information that would be useful for creating an outreach strategy."

        
        elif is_valid_url(url):
            raw_html = fetch_html_selenium(url)
            data_response = html_to_markdown_with_readability(raw_html)

            system_message = f"You are an experienced Sales Development Representative (SDR) at **Initializ**. Your task is to create a personalized outreach strategy based on the content of a webpage. The webpage provides useful information that can help you understand the potential prospect's needs. Here is the content: {data_response}"

            user_message = f"Summarize the content of the following webpage: {data_response}. Focus on any information that can help create an outreach strategy for a prospect."

        else:
            return jsonify({"error": "Invalid URL"}), 400
        
        initializ_url = 'https://colonelz.prod.devai.initz.run/initializ/v1/ai/chat'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        payload = {
            "model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 5000,
            "temperature": 0.7,
            "stream": False
        }
        
        response = requests.post(initializ_url, headers=headers, json=payload)
        
        return jsonify(response.json()), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8000)

