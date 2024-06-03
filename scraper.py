import time
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
import datetime
import csv
import os
import requests
import hashlib
from typing import Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.service import Service
from requests import Response
# from conf.models import Scraper as ScraperModel

class Scraper:
       
    name = "Scraper"

    proxy_index = 0

    proxies_file_path = "proxies.txt"
    # proxies_file_path = "../proxies.txt"
    proxies = []
    if os.path.exists(proxies_file_path):
        with open(proxies_file_path, 'r') as file:
            proxies = file.readlines()
    proxies = [proxy.strip().replace("\n", "").replace(",", "") for proxy in proxies if len(proxy.strip().replace("\n", "").replace(",", "")) > 0]

    print("================== proxies >>>>>>>>>>>", proxies)
    
    folder_name = "default_results"

    model=None

    def __init__(self, main_url: str, folder_name: str):
        """
        Initialize the Scraper with provided parameters.

        Parameters:
        - main_url (str): The url of main site.
        - folder_name (str): The folder name of csv files
        """
        
        self.main_url = main_url

        # Initialize instance variables
        self.start_date = datetime.datetime.utcnow()  # Record the starting time of scraping

        folder_path = f"../results"
        # Create a folder for storing CSV files if it doesn't exist
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Folder '{folder_path}' created successfully.")

        folder_path = f"../results/{folder_name}"
        # Create a folder for storing CSV files if it doesn't exist
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Folder '{folder_path}' created successfully.")

        print("========= proxies >>>>>>", self.proxies)

    @staticmethod
    def _get_proxy():
        """
        Get a proxy configuration from the list of proxies.
    
        This method retrieves a proxy configuration based on the current index in the proxy list.
        The proxy configuration includes both HTTP and HTTPS proxies.
        If the index exceeds the number of proxies in the list, it resets to 0 for rotation.
        
        Returns:
        - proxy (dict): A dictionary containing HTTP and HTTPS proxy configurations. Returns None if no proxies are available.
        """
    
        if len(Scraper.proxies) == 0:
            return None  # Return None if there are no proxies in the list
    
        proxy = {
            "http": Scraper.proxies[Scraper.proxy_index],  # Define the HTTP proxy configuration
            "https": Scraper.proxies[Scraper.proxy_index]  # Define the HTTPS proxy configuration
        }
        
        Scraper.proxy_index += 1  # Move to the next proxy in the list
        
        if Scraper.proxy_index >= len(Scraper.proxies): 
            Scraper.proxy_index = 0  # Reset the index if it exceeds the number of proxies
        
        return proxy  # Return the proxy configuration
    
    def _get_file_path(self, file_name: str):
        return f"results/{self.folder_name}/{file_name}"

    def _save_products_in_csv(self, products: list[dict[str, str]], file_path: str) -> None:
        """
        Save a list of products to a CSV file.
    
        This method takes a list of product dictionaries and saves them to a CSV file specified by the file path.
        If the file does not exist, it creates a new file with the product data.
    
        Parameters:
        - products (list[dict[str, str]]): List of product dictionaries to be saved.
        - file_path (str): Path to the CSV file where the products will be saved.
        """
    
        if len(products) == 0:
            return  # Return if there are no products to save
    
        if not os.path.exists(file_path):
            # Create the CSV file if it doesn't exist
            with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=products[0].keys())
                writer.writeheader()
    
        try:
            with open(file_path, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=products[0].keys())
                for product in products:
                    writer.writerow(product)  # Write each product to the CSV file
        except IOError as e:
            print(f"An I/O error occurred: {e.strerror}")  # Handle I/O errors
        except Exception as e:
            print(f"Error while saving in CSV: {e}")  # Handle other exceptions

    def _get_response_until_success(self, url: str, method: str = "get", data: dict[str, Any] = {}, cookies={}) -> tuple[bytes | str, int]:
        """
        Retrieve response content from the specified URL with retries until a successful response is obtained.

        This method attempts to retrieve the response content from the given URL by handling various status codes and exceptions.
        
        Parameters:
        - url (str): The URL to fetch the response from.
        
        Returns:
        - tuple: A tuple containing the response content (byte string) and the HTTP status code.
        """

        headers = {'User-Agent': 'Mozilla/5.0'}  # Define user-agent headers

        if not url.startswith("http"):
            url = f"{self.main_url}{url}"  # Append base URL if needed


        while True:
            try:
                proxy = Scraper._get_proxy()  # Get a proxy configuration for the request
                response = None
                if proxy is not None:
                    if method == "get": response = requests.get(url, headers=headers, proxies=proxy, timeout=20, cookies=cookies)
                    else: response = requests.post(url, headers=headers, proxies=proxy, timeout=20, data=data, cookies=cookies)
                else:
                    if method == "get": response = requests.get(url, headers=headers, timeout=20, cookies=cookies)
                    else: response = requests.post(url, headers=headers, timeout=20, data=data, cookies=cookies)
                if response.status_code == 404 or response.status_code == 301:   
                    return ("", response.status_code)  # Return empty content and status code for specific response codes
                elif response.status_code < 300:
                    return (response.content, response.status_code)  # Return response content and status code for successful requests

                print(f'Waiting: {url}')  # Print a message indicating waiting
                time.sleep(10)  # Adjust sleep time as needed (in seconds)

            except Exception as e:
                print(e)  # Log any exceptions that occur during the request
                time.sleep(20)  # Wait before retrying in case of exceptions

    def _create_driver(self) -> tuple[WebDriver, WebDriverWait]:
        """
        Create a WebDriver instance for web scraping.
    
        This method sets up a WebDriver instance with the specified options, including handling headless mode,
        proxy configurations, browser window size, and wait conditions.
    
        Returns:
        - tuple: A tuple containing the WebDriver instance and WebDriverWait object.
        """
    
        options = Options()  # Initialize browser options
        if os.getenv("ENV") != "dev":
            options.add_argument("--headless")  # Enable headless mode if not in development environment
        options.add_argument("--disable-gpu")
        options.add_argument('--no-sandbox')  # Bypass OS security model.
        options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems.
        options.add_argument("--enable-features=SameSiteByDefaultCookies,CookiesWithoutSameSiteMustBeSecure")
    
        proxies = Scraper._get_proxy()  # Retrieve proxy configuration

        print("========== A proxy >>>>>>>>>>", proxies)
        driver = None
        wait = None

        # chromedriver_path = '/usr/bin/chromedriver/chromedriver' 
        # service = Service(executable_path=chromedriver_path)
    
        try:
            if proxies is not None:
                seleniumwire_options = {
                    'proxy': {
                        'http': proxies['http'],
                        'https': proxies['https'],
                        'verify_ssl': True,
                    },
                }
                driver = webdriver.Chrome(seleniumwire_options=seleniumwire_options, options=options)  # Create WebDriver with proxy settings
                # driver = webdriver.Chrome(seleniumwire_options=seleniumwire_options, options=options, service = service)  # Create WebDriver with proxy settings
            else:
                driver = webdriver.Chrome(options=options)  # Create WebDriver without proxy settings
                # driver = webdriver.Chrome(options=options, service = service)  # Create WebDriver without proxy settings
            print("========== driver >>>>>>>>>>", driver)
            driver.set_window_size(1920, 1600)  # Set browser window size
            wait = WebDriverWait(driver, 30, ignored_exceptions=[NoSuchElementException, StaleElementReferenceException])  # Set WebDriverWait object
            return (driver, wait)  # Return the WebDriver instance and WebDriverWait object
        except Exception as e:
            print(f"Booting Driver Error: {e}")  # Log any errors that occur during WebDriver setup
            return (None, None)  # Return None values if WebDriver setup fails

    def _get_full_url(self, url : str):
        return f"{self.main_url}{url}" if not url.startswith("http") else url

    # def start(self, user: str) -> None:
    #     scraper = ScraperModel(
    #             name=self.name,
    #             user=user,
    #             status="Running",
    #             start_date=datetime.datetime.utcnow()
    #         ).save()
    #     self.model = scraper
    #     try:
    #         self.run()
    #         scraper.status="Finished"
    #         scraper.end_date=datetime.datetime.utcnow()
    #         scraper.save()
    #     except Exception as e:
    #         print(f"Error : {e}")
    #         scraper.status="Failed"
    #         scraper.error=str(e)
    #         scraper.end_date=datetime.datetime.utcnow()
    #         scraper.save()

    def run(self) -> None:
        pass

    @staticmethod
    def _get_hash(data : str):
        hash_object = hashlib.sha256()
        hash_object.update(data.encode())
        hashed_data = hash_object.hexdigest()
        return hashed_data
    
    @staticmethod
    def _adjust_special_characters(values:list[str]):
        return [value.replace("'", "\'").replace('"', "\"") for value in values]
    
    @staticmethod
    def _apply_multi_threading(inputs: list[Any], callback: Callable, max_threads: int = 30):
        results = []
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            # Map each collection to the future object executing it
            future_to_post = {executor.submit(callback, input): input for input in inputs}
            
            # Iterate over the futures as they complete (in the order they complete)
            for future in as_completed(future_to_post):
                try:
                    input = future_to_post[future]
                    # Get the result from the future
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    results.append(None)
                    # Handle any exceptions that were raised during processing
                    print(f'Input {input} generated an exception while multi threading: {exc}')
        return results
