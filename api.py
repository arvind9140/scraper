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

# Setup Chrome options
chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.headless = False  # Set to True if you want headless mode



# Helper function to setup Selenium WebDriver
def setup_selenium():
    # Use ChromeDriverManager to ensure the correct ChromeDriver version is installed
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    return driver

# Helper function to fetch HTML content using Selenium
def fetch_html_selenium(url):
    driver = setup_selenium()
    try:
        driver.get(url)

        # Add random delays to mimic human behavior
        time.sleep(5)  # Adjust this to simulate time for user to read or interact

        # Add more realistic actions like scrolling
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)  # Simulate time taken to scroll and read

        html = driver.page_source
        return html
    except Exception as e:
        return {"error": str(e)}
    finally:
        driver.quit()

# Helper function to clean HTML content by removing unwanted tags (e.g., headers, footers)
def clean_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove headers and footers based on common HTML tags or classes
    for element in soup.find_all(["header", "footer"]):
        element.decompose()  # Remove these tags and their content

    return str(soup)

# Helper function to convert cleaned HTML content into Markdown format
def html_to_markdown_with_readability(html_content):
    cleaned_html = clean_html(html_content)

    # Convert to markdown
    markdown_converter = html2text.HTML2Text()
    markdown_converter.ignore_links = False
    markdown_content = markdown_converter.handle(cleaned_html)

    return markdown_content

# Helper function to login and scrape LinkedIn profile
def scrape_linkedin_profile(email, password, linkedin_url):
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # Login to LinkedIn
        actions.login(driver, email, password)
        
        # Scrape LinkedIn profile
        person = Person(linkedin_url, driver=driver)
        
        # Print available attributes of the person object for debugging
        # print(person.__dict__)  # Debug line to print all attributes of the Person object
       
    finally:
        driver.quit()
    
    return person.__dict__

def scrape_linkedin_company(email, password, linkedin_url):
    # Setup Selenium driver
    driver = setup_selenium()
    
    try:
        # Scrape company data using the LinkedIn scraper library
        actions.login(driver, email, password)
        company = Company(linkedin_url,driver=driver)
        print("company: ",company)
        print("company_dict: ",company.__dict__)  # Debug line to print all attributes of the Company object
    
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
    # Regular expression to match LinkedIn URLs (both http and https)
    linkedin_pattern = r"https:\/\/(www\.)?linkedin\.com\/.*"
    
    # Match the LinkedIn pattern
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
        return all([result.scheme, result.netloc])  # Check if it's a valid URL with a scheme (http/https) and domain
    except ValueError:
        return False
@app.route('/scrape', methods=['POST'])
def scrape():
    # Get data from POST request
    data = request.json
    url = data.get('url')

    # Fetch email and password from environment variables
    email = os.getenv("LINKEDIN_USER")
    password = os.getenv("LINKEDIN_PASSWORD")

    # Check if email and password are set in environment variables
    if not email or not password:
        return jsonify({"error": "Email and password must be set in environment variables"}), 400
    
    # Check if LinkedIn URL is provided in the request
    if not url:
        return jsonify({"error": "LinkedIn URL is required"}), 400
    
    try:
        data= None
        
        if is_linkedin_url(url):
            if "linkedin.com/company/" in url:
                # Scrape LinkedIn company page data
                company_data = scrape_linkedin_company(email, password, url)
                data = company_data
                print(data)
            else:    
                data = scrape_linkedin_profile(email, password, url)# Scrape LinkedIn profile data
             
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
                    "content": f"Please summarize the key details from the LinkedIn profile company website and portfolio  for the prospect. Focus on their current role key responsibilities and relevant experience'{data}'",
                }
            ],
            "max_tokens": 5000,
            "temperature": 0.7,
            "stream": False,
            # "stream": True

        }
        response = requests.post(initializ_url, headers=headers, json=data)
        # print(response.json())
        return jsonify(response.json()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8000)

