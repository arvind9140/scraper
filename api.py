import os
import time
import logging
from flask import Flask, request, jsonify
import requests
from selenium.webdriver import Chrome, ChromeOptions
from linkedin_scraper import actions
from linkedin_scraper.person import Person
from linkedin_scraper.company import Company
from bs4 import BeautifulSoup
import html2text
import re
from urllib.parse import urlparse

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_selenium():
    options = ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--enable-unsafe-swiftshader")
    driver = Chrome(options=options)
    return driver

def fetch_html_selenium(url):
    Driver = setup_selenium()
    try:
        Driver.get(url)
        time.sleep(5)
       
        Driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)  
        html = Driver.page_source
        return html
    except Exception as e:
        return {"error": str(e)}

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
    Driver = setup_selenium()
    try:
        actions._login_with_cookie(Driver)
        person = Person(linkedin_url, driver=Driver)
        return person.__dict__
    except Exception as e:
        print(e)
        return ""

def scrape_linkedin_company(email, password, linkedin_url):
    Driver = setup_selenium()
    actions._login_with_cookie(Driver)
    company = Company(linkedin_url,driver=Driver)
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
                
                system_message = f"""
                You are an advanced AI tasked with helping a Sales Development Representative (SDR) at Initializ develop a personalized outreach strategy for a prospect. Your job is to analyze the provided data and generate an insightful outreach plan based on the following steps:
 
1.You are an experienced Sales Development Representative (SDR) at sender_company. Your goal is to research and create a personalized outreach strategy for first_name , atitle at company. Use the information provided to craft a detailed, relevant summary that will help engage this prospect effectively. Your analysis should be insightful, demonstrating a deep understanding of both sender_company's offerings and the prospect's potential needs.
Analyze Context: Briefly summarize first_name s role as title  at company , including industry and potential. When describing first_name  current role and activities, ensure you are referencing their most recent active experience as listed on their LinkedIn profile, which should be indicated by a date range ending with 'present' . Do not use information from older positions unless explicitly relevant to the current analysis
Identify Key Challenges: List 3 challenges company likely faces, based on our value propositions for title below focusing on areas sender_company  can address, based on our value propositions below. Focus on challenges specific to first_name  role as title , using the provided source data to identify role-specific priorities & symptoms of challenges. Ensure these solely align with the value propositions below.
Present sender_company  Solutions: For each challenge, explain how sender_company  a. Addresses the specific need challenges b. Highlights a benefit to company   c. Explains the benefit tocompany and first_name's role. For each solution, provide hyper-specific language that demonstrate how sender_company  can improve an outcome for company (ensure this is completely factual). Use words not numbers to communicate this.
Provide Concrete Example: Give one specific example of how sender_company could solve a unique challenge for company , based on their industry or structure. Ensure this example uses language and metrics highly specific to first_name's role and industry, avoiding generic AI buzzwords.
Recent Company News:
Identify a recent newsworthy event or development specific to company  or first_name's role. Ensure the news is from the last 6 months only. 
Briefly explain how this event might relate to the challenges or priorities identified earlier.
[Use the following information as sources]:
Linkedin profile: "linkedin_profile ."
Company Google News (ensure only last 6 months) "company_google_search_notes."
company website data: "company_website_data "
sender_company value propositions here: "sender_value_propositions
 
                """
                user_message = f""" 
"Summarize the content of the following webpage: {data_response}. Focus on any information that can help create an outreach strategy for a prospect.
                """


        elif is_valid_url(url):
            raw_html = fetch_html_selenium(url)
            data_response = html_to_markdown_with_readability(raw_html)
           
            system_message = f"You are an experienced Sales Development Representative (SDR) at **Initializ**. Your task is to create a personalized outreach strategy based on the content of a webpage. The webpage provides useful information that can help you understand the potential prospect's needs. Here is the content: {data_response}"

            user_message = f"Summarize the content of the following webpage: {data_response}. Focus on any information that can help create an outreach strategy for a prospect."

        else:
            return jsonify({"error": "Invalid URL"}), 400
        token = os.getenv("TOKEN")
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
        print(e)
        return jsonify({"error": str(e)}), 500
   
@app.route('/_healthz', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200
 

if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8000)