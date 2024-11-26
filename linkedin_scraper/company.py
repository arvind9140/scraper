import requests
from lxml import html
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from .objects import Scraper
from .person import Person
import time
import os
import json
import logging

AD_BANNER_CLASSNAME = ('ad-banner-container', '__ad')

def getchildren(elem):
    return elem.find_elements(By.XPATH, ".//*")

class CompanySummary(object):
    linkedin_url = None
    name = None
    followers = None

    def __init__(self, linkedin_url = None, name = None, followers = None):
        self.linkedin_url = linkedin_url
        self.name = name
        self.followers = followers

    def __repr__(self):
        if self.followers == None:
            return """ {name} """.format(name = self.name)
        else:
            return """ {name} {followers} """.format(name = self.name, followers = self.followers)

class Company(Scraper):
    linkedin_url = None
    name = None
    about_us =None
    website = None
    headquarters = None
    founded = None
    industry = None
    company_type = None
    company_size = None
    specialties = None
    showcase_pages = []
    affiliated_companies = []
    employees = []
    headcount = None

    def __init__(self, linkedin_url = None, name = None, about_us =None, website = None, headquarters = None, founded = None, industry = None, company_type = None, company_size = None, specialties = None, showcase_pages =[], affiliated_companies = [], driver = None, scrape = True, get_employees = True, close_on_complete = True):
        self.linkedin_url = linkedin_url
        self.name = name
        self.about_us = about_us
        self.website = website
        self.headquarters = headquarters
        self.founded = founded
        self.industry = industry
        self.company_type = company_type
        self.company_size = company_size
        self.specialties = specialties
        self.showcase_pages = showcase_pages
        self.affiliated_companies = affiliated_companies

        if driver is None:
            try:
                if os.getenv("CHROMEDRIVER") == None:
                    driver_path = os.path.join(os.path.dirname(__file__), 'drivers/chromedriver')
                else:
                    driver_path = os.getenv("CHROMEDRIVER")

                driver = webdriver.Chrome(driver_path)
            except:
                driver = webdriver.Chrome()

        driver.get(linkedin_url)
        self.driver = driver

        if scrape:
            self.scrape(get_employees=get_employees, close_on_complete=close_on_complete)

    def __get_text_under_subtitle(self, elem):
        return "\n".join(elem.text.split("\n")[1:])

    def __get_text_under_subtitle_by_class(self, driver, class_name):
        return self.__get_text_under_subtitle(driver.find_element(By.CLASS_NAME, class_name))

    def scrape(self, get_employees=True, close_on_complete=True):
        if self.is_signed_in():
            self.scrape_logged_in(get_employees = get_employees, close_on_complete = close_on_complete)
        else:
            self.scrape_not_logged_in(get_employees = get_employees, close_on_complete = close_on_complete)

    def __parse_employee__(self, employee_raw):

        try:
            # print()
            employee_object = {}
            employee_object['name'] = (employee_raw.text.split("\n") or [""])[0].strip()
            employee_object['designation'] = (employee_raw.text.split("\n") or [""])[3].strip()
            employee_object['linkedin_url'] = employee_raw.find_element(By.TAG_NAME, "a").get_attribute("href")
            # print(employee_raw.text, employee_object)
            # _person = Person(
            #     # linkedin_url = employee_raw.find_element_by_tag_name("a").get_attribute("href"),
            #     linkedin_url = employee_raw.find_element_by_tag_name("a").get_attribute("href"),
            #     name = (employee_raw.text.split("\n") or [""])[0].strip(),
            #     driver = self.driver,
            #     get = True,
            #     scrape = False,
            #     designation = (employee_raw.text.split("\n") or [""])[3].strip()
            #     )
            # print(_person, employee_object)
            # return _person
            return employee_object
        except Exception as e:
            # print(e)
            return None

    def get_employees(self, wait_time=10):
        total = []
        list_css = "list-style-none"
        next_xpath = '//button[@aria-label="Next"]'
        driver = self.driver

        try:
            see_all_employees = driver.find_element(By.XPATH,'//a[@data-control-name="topcard_see_all_employees"]')
        except:
            pass
        driver.get(os.path.join(self.linkedin_url, "people"))

        _ = WebDriverWait(driver, 3).until(EC.presence_of_all_elements_located((By.XPATH, '//span[@dir="ltr"]')))

        driver.execute_script("window.scrollTo(0, Math.ceil(document.body.scrollHeight/2));")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, Math.ceil(document.body.scrollHeight*3/4));")
        time.sleep(1)

        results_list = driver.find_element(By.CLASS_NAME, list_css)
        results_li = results_list.find_elements(By.TAG_NAME, "li")
        for res in results_li:
            total.append(self.__parse_employee__(res))

        def is_loaded(previous_results):
          loop = 0
          driver.execute_script("window.scrollTo(0, Math.ceil(document.body.scrollHeight));")
          results_li = results_list.find_elements(By.TAG_NAME, "li")
          while len(results_li) == previous_results and loop <= 5:
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, Math.ceil(document.body.scrollHeight));")
            results_li = results_list.find_elements(By.TAG_NAME, "li")
            loop += 1
          return loop <= 5

        def get_data(previous_results):
            results_li = results_list.find_elements(By.TAG_NAME, "li")
            for res in results_li[previous_results:]:
                total.append(self.__parse_employee__(res))

        results_li_len = len(results_li)
        while is_loaded(results_li_len):
            try:
                driver.find_element(By.XPATH,next_xpath).click()
            except:
                pass
            _ = WebDriverWait(driver, wait_time).until(EC.presence_of_element_located((By.CLASS_NAME, list_css)))

            driver.execute_script("window.scrollTo(0, Math.ceil(document.body.scrollHeight/2));")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, Math.ceil(document.body.scrollHeight*2/3));")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, Math.ceil(document.body.scrollHeight*3/4));")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, Math.ceil(document.body.scrollHeight));")
            time.sleep(1)

            get_data(results_li_len)
            results_li_len = len(total)
        return total



    def scrape_logged_in(self, get_employees = True, close_on_complete = True):
        driver = self.driver

        driver.get(self.linkedin_url)

        _ = WebDriverWait(driver, 3).until(EC.presence_of_all_elements_located((By.XPATH, '//div[@dir="ltr"]')))

        navigation = driver.find_element(By.CLASS_NAME, "org-page-navigation__items ")

        self.name = driver.find_element(By.CLASS_NAME,"org-top-card-summary__title").text.strip()

        # Click About Tab or View All Link
        try:
          self.__find_first_available_element__(
            navigation.find_elements(By.XPATH, "//a[@data-control-name='page_member_main_nav_about_tab']"),
            navigation.find_elements(By.XPATH, "//a[@data-control-name='org_about_module_see_all_view_link']"),
          ).click()
        except:
          driver.get(os.path.join(self.linkedin_url, "about"))

        _ = WebDriverWait(driver, 3).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'section')))
        time.sleep(3)

        if 'Cookie Policy' in driver.find_elements(By.TAG_NAME, "section")[1].text or any(classname in driver.find_elements(By.TAG_NAME, "section")[1].get_attribute('class') for classname in AD_BANNER_CLASSNAME):
            section_id = 4
        else:
            section_id = 3
       #section ID is no longer needed, we are using class name now.
        #grid = driver.find_elements_by_tag_name("section")[section_id]
        grid = driver.find_element(By.CLASS_NAME, "artdeco-card.org-page-details-module__card-spacing.artdeco-card.org-about-module__margin-bottom")
        descWrapper = grid.find_elements(By.TAG_NAME, "p")
        if len(descWrapper) > 0:
            self.about_us = descWrapper[0].text.strip()
        labels = grid.find_elements(By.TAG_NAME, "dt")
        values = grid.find_elements(By.TAG_NAME, "dd")
        num_attributes = min(len(labels), len(values))
        #print("The length of the labels is " + str(len(labels)), "The length of the values is " + str(len(values)))
        # if num_attributes == 0:
        #     exit()
        x_off = 0
        for i in range(num_attributes):
            txt = labels[i].text.strip()
            if txt == 'Website':
                self.website = values[i+x_off].text.strip()
            elif txt == 'Industry':
                self.industry = values[i+x_off].text.strip()
            elif txt == 'Company size':
                self.company_size = values[i+x_off].text.strip()
                if len(values) > len(labels):
                    x_off = 1
            elif txt == 'Headquarters':
                    self.headquarters = values[i+x_off].text.strip()
            elif txt == 'Type':
                self.company_type = values[i+x_off].text.strip()
            elif txt == 'Founded':
                self.founded = values[i+x_off].text.strip()
            elif txt == 'Specialties':
                self.specialties = "\n".join(values[i+x_off].text.strip().split(", "))
        
        # try:
        #     grid = driver.find_element(By.CLASS_NAME, "mt1")
        #     spans = grid.find_elements(By.TAG_NAME, "span")
        #     for span in spans:
        #         txt = span.text.strip()
        #         if "See all" in txt and "employees on LinkedIn" in txt:
        #             self.headcount = int(txt.replace("See all", "").replace("employees on LinkedIn", "").strip())
        # except NoSuchElementException: # Does not exist in page, skip it
        #     pass

        # driver.execute_script("window.scrollTo(0, Math.ceil(document.body.scrollHeight/2));")


        # try:
        #     _ = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'company-list')))
        #     showcase, affiliated = driver.find_elements(By.CLASS_NAME, "company-list")
        #     driver.find_element(By.ID,"org-related-companies-module__show-more-btn").click()

        #     # get showcase
        #     for showcase_company in showcase.find_elements(By.CLASS_NAME, "org-company-card"):
        #         companySummary = CompanySummary(
        #                 linkedin_url = showcase_company.find_element(By.CLASS_NAME, "company-name-link").get_attribute("href"),
        #                 name = showcase_company.find_element(By.CLASS_NAME, "company-name-link").text.strip(),
        #                 followers = showcase_company.find_element(By.CLASS_NAME, "company-followers-count").text.strip()
        #             )
        #         self.showcase_pages.append(companySummary)

        #     # affiliated company

        #     for affiliated_company in showcase.find_element(By.CLASS_NAME, "org-company-card"):
        #         companySummary = CompanySummary(
        #                  linkedin_url = affiliated_company.find_element(By.CLASS_NAME, "company-name-link").get_attribute("href"),
        #                 name = affiliated_company.find_element(By.CLASS_NAME, "company-name-link").text.strip(),
        #                 followers = affiliated_company.find_element(By.CLASS_NAME, "company-followers-count").text.strip()
        #                 )
        #         self.affiliated_companies.append(companySummary)

        # except:
        #     pass

        # if get_employees:
        #     self.employees = self.get_employees()

        # driver.get(self.linkedin_url)

        # if close_on_complete:
        #     driver.close()

 
    def __repr__(self):
        return "<Company {name}\n\nAbout Us\n{about_us}\n\nWebsite\n{website}\n\nHeadquarters\n{headquarters}\n\nFounded\n{founded}\n\nIndustry\n{industry}\n\nCompany Size\n{company_size}\n\nSpecialties\n{specialties}\n\nEmployees\n{employees}>".format(
            name=self.name,
            about_us=self.about_us or "N/A",  
            website=self.website or "N/A",   
            headquarters=self.headquarters or "N/A", 
            founded=self.founded or "N/A",   
            industry=self.industry or "N/A", 
            company_size=self.company_size or "N/A", 
            specialties=self.specialties or "N/A", 
            employees=len(self.employees) if self.employees else "N/A"  
        )

