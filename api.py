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
    print(email)
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
 
1. **Analyze Context**: Review the provided data about the prospect (first_name) from their LinkedIn profile, including their current role at company. Summarize the prospect's key responsibilities, focusing only on their most recent experience. Do not reference older positions unless explicitly relevant to their current role.
 
2. **Identify Key Challenges**: Based on the value propositions of Initializ, identify three challenges that company might be facing, which are relevant to the prospect's role. These should be related to their function and responsibilities as indicated by their LinkedIn experience.
 
3. **Present Initializ Solutions**: For each identified challenge, describe how Initializ can address it. Focus on providing hyper-specific solutions that align with the prospectInitializs needs and demonstrate how InitializInitializs offerings could improve outcomes for the prospect's company. Avoid using numbers or generic language; be clear and factual.
 
4. **Provide Concrete Example**: Provide a specific example of how Initializ can uniquely solve a problem for company based on its industry or structure. This should be related to the challenges or priorities identified earlier and use the prospect's role and company context.
 
5. **Recent Company News**: Identify a recent newsworthy event related to company or first_nameInitializs role (from the last 6 months). Explain how this event might relate to the challenges or priorities identified.
 
Ensure you use only factual information from the provided sources, including LinkedIn profile, Google News (last 6 months), company website, and InitializInitializs value propositions.
 
                """
                user_message = f"""
                You are an experienced Sales Development Representative (SDR) at sender_company. Your goal is to research and create a personalized outreach strategy for [Prospect Name], [Prospect Title] at [Prospect Company]. Use the information provided to craft a detailed, relevant summary that will help engage [Prospect Name] effectively. Your analysis should demonstrate a deep understanding of both sender_companyInitializs offerings and [Prospect Name]Initializs potential needs.
 
Analyze Context: Briefly summarize [Prospect Name]Initializs role as [Prospect Title] at [Prospect Company]. Focus on their most recent active experience (starting from [most recent position date] to present). Do not use information from previous roles unless explicitly relevant to the current analysis.
 
Identify Key Challenges: List three challenges [Prospect Company] likely faces, based on sender_companyInitializs value propositions for [Prospect Title]. Focus on challenges specific to [Prospect Name]Initializs role, using the provided source data to identify relevant priorities and symptoms of challenges.
 
Present sender_company Solutions: For each identified challenge, explain how sender_company addresses the specific need. Highlight the benefit to [Prospect Company] and to [Prospect Name]Initializs role. Use hyper-specific language to demonstrate how sender_company can improve outcomes for the company and [Prospect Name].
 
Provide Concrete Example: Give one specific example of how sender_company could solve a unique challenge for [Prospect Company], based on their industry or structure. Ensure this example aligns with [Prospect Name]Initializs role and responsibilities, and avoid using generic language.
 
Recent Company News: Identify a recent newsworthy event or development specific to [Prospect Company] or [Prospect Name]Initializs role from the last 6 months. Briefly explain how this event might relate to the challenges or priorities identified earlier.
 
Use the {data_response} information as sources.
 
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
        print("REspose: ",response)
        return jsonify(response.json()), 200
    
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500
   
@app.route('/_healthz', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200
 

if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8000)