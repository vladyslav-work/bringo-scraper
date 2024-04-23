import time
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

from bs4 import BeautifulSoup
import datetime
import csv
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from type_classes import all_elements_clickable

import mysql.connector
import hashlib
import dotenv
import asyncio

dotenv.load_dotenv()

def remove_duplicates(list_of_dicts, key):
    seen = set()
    new_list = []
    for d in list_of_dicts:
        value = d[key]
        if value not in seen:
            seen.add(value)
            new_list.append(d)
    return new_list

class GlovoScraper:
    # Class variables - Name of scraper, main url of the site and the url of the page that contain urls of cities
    name = 'Glovo' 
    cities_url = 'https://glovoapp.com/ma/fr/map/villes/'
    main_url = 'https://glovoapp.com'

    # Name of the database table
    table_name = "products"
    
    # List of columns for the database table
    columns = ["product_id", "city", "category", "store", "section", "collection", "group", "name", "image", "price", "currency", "original_price", "url", "date", "file_path"]
    
    # String containing column names for SQL queries
    columns_str = ", ".join([f"`{column}` TEXT" for column in columns])
    
    # Database configuration dictionary
    config = {
            'user': os.getenv("MYSQL_USER"),
            'password': os.getenv("MYSQL_PASSWORD"),
            'host': os.getenv("MYSQL_HOST"),
            'database': os.getenv("MYSQL_DATABASE"),
            'raise_on_warnings': True
        }
    
    # Folder name for storing csv files
    folder_name = "results"

    def __init__(self, excluding_city_names: list[str] = [], proxies=[]):
        """
        Initialize the Glovo Scraper with provided parameters.

        Parameters:
        - excluding_city_names (list): List of city names to exclude in scraping.
        - proxies (list): List of proxy servers for rotating IP addresses.
        """

        # Initialize instance variables
        self.start_date = datetime.datetime.utcnow()  # Record the starting time of scraping
        self.proxy_index = 0  # Initialize proxy index as 0 to rotate through proxies
        self.excluding = excluding_city_names  # Store the list of city names to exclude in scraping
        self.proxy_list = proxies  # Initialize the list of proxies

        # Create a folder for storing CSV files if it doesn't exist
        if not os.path.exists(self.folder_name):
            os.makedirs(self.folder_name)
            print(f"Folder '{self.folder_name}' created successfully.")
        else:
            print(f"Folder '{self.folder_name}' already exists.")

        # Connect to the database, retry after 30s if connection fails
        while True:
            try:
                self.cnx = mysql.connector.connect(**self.config)
                break
            except Exception as e:
                print(f"Can't connect to the database: {e}\nRetrying in 30 seconds...")
                time.sleep(30)

        # Check if the table for storing products exists in the database
        self.cursor = self.cnx.cursor()
        self.cursor.execute(f"SHOW TABLES LIKE '{self.table_name}'")
        result = self.cursor.fetchone()

        if result:
            print(f"Table '{self.table_name}' already exists")
            return

        print(f"Creating a new table '{self.table_name}'")

        # Create the table in the database if it doesn't exist
        create_table_query = f"CREATE TABLE IF NOT EXISTS {self.table_name} ({self.columns_str})"
        self.cursor.execute(create_table_query)
        self.cnx.commit()
    
    def __del__(self):
        """
        Clean up resources when the GlovoScraper instance is deleted.
    
        This method closes the database cursor and connection to ensure proper cleanup.
        """
        if self.cursor: self.cursor.close()  # Close the database cursor
        if self.cnx: self.cnx.close()  # Close the database connection

    def __get_proxy(self):
        """
        Get a proxy configuration from the list of proxies.
    
        This method retrieves a proxy configuration based on the current index in the proxy list.
        The proxy configuration includes both HTTP and HTTPS proxies.
        If the index exceeds the number of proxies in the list, it resets to 0 for rotation.
        
        Returns:
        - proxy (dict): A dictionary containing HTTP and HTTPS proxy configurations. Returns None if no proxies are available.
        """
    
        if len(self.proxy_list) == 0:
            return None  # Return None if there are no proxies in the list
    
        proxy = {
            "http": self.proxy_list[self.proxy_index],  # Define the HTTP proxy configuration
            "https": self.proxy_list[self.proxy_index]  # Define the HTTPS proxy configuration
        }
        
        self.proxy_index += 1  # Move to the next proxy in the list
        
        if self.proxy_index >= len(self.proxy_list): 
            self.proxy_index = 0  # Reset the index if it exceeds the number of proxies
        
        return proxy  # Return the proxy configuration

    def __save_products(self, products: list[dict[str, str]], file_path: str) -> None:
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

    def start_scrape(self, city=None):
        """
        Start the scraping process.
    
        This method initiates the scraping process based on the specified city or all available cities.
        If a specific city is provided, it scrapes data for that city; otherwise, it scrapes data for all cities.
        
        Parameters:
        - city (str): The name of the city to scrape. If None, data will be scraped for all cities except those in the exclusion list.
        """
    
        print('START scraping')  # Print a message indicating the start of the scraping process
    
        if city:
            self.__scrape_city({"city_url": city, "city_name": "your_city"})  # Scrape data for the specified city
        else:
            city_urls = self.__get_city_urls()  # Get the URLs of all available cities
            
            # Iterate through each city URL and scrape data if it's not excluded
            for a_city_url in city_urls:
                if a_city_url["city_name"] in self.excluding:
                    continue  # Skip scraping for cities in the exclusion list
                self.__scrape_city(a_city_url)  # Scrape data for the current city URL

    def __get_city_urls(self) -> list[dict[str, str]]:
        """
        Retrieve city URLs and names from the cities URL.
    
        This method fetches the response from the cities URL and extracts city names and corresponding URLs.
        
        Returns:
        - List[dict[str, str]]: A list of dictionaries containing city names and their respective URLs.
        """
    
        response, _ = self.__get_response_until_success(self.cities_url)  # Get the response from the cities URL
        
        soup = BeautifulSoup(response, "html.parser")  # Parse the HTML response using BeautifulSoup
        city_tags = soup.find_all("a", class_="city-list__city")  # Find all city tags in the parsed HTML
        
        # Construct a list of dictionaries containing city names and URLs
        return [{"city_name": city_tag.text.replace("\n", "").strip(), "city_url": city_tag.get("href")} for city_tag in city_tags]

    def __get_response_until_success(self, url : str) -> tuple:
        headers = {'User-Agent': 'Mozilla/5.0'}

        if not url.startswith("http"):
            url = f"https://www.glovoapp.com{url}"

    
    def __get_response_until_success(self, url: str) -> tuple:
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
            url = f"https://www.glovoapp.com{url}"  # Append base URL if needed

        while True:
            try:
                proxy = self.__get_proxy()  # Get a proxy configuration for the request
                if proxy is not None:
                    response = requests.get(url, headers=headers, proxies=proxy, timeout=10)
                else:
                    response = requests.get(url, headers=headers, timeout=10)

                if response.status_code == 404 or response.status_code == 301:   
                    return ("", response.status_code)  # Return empty content and status code for specific response codes
                elif response.status_code < 300:
                    return (response.content, response.status_code)  # Return response content and status code for successful requests

                print(f'Waiting: {url}')  # Print a message indicating waiting
                time.sleep(10)  # Adjust sleep time as needed (in seconds)

            except Exception as e:
                print(e)  # Log any exceptions that occur during the request
                time.sleep(20)  # Wait before retrying in case of exceptions

            
    def __scrape_city(self, city: dict[str, str]):
        """
        Scrape data for a specific city.
    
        This method scrapes data for a given city by fetching categories and selecting relevant ones based on keywords.
        It then proceeds to scrape supermarkets within the selected categories for the city.
    
        Parameters:
        - city (dict[str, str]): A dictionary containing information about the city to be scraped.
        """
    
        current_date = datetime.datetime.now()  # Get the current date and time
        formatted_date = current_date.strftime("%Y_%m_%d_%H_%M")  # Format the date
        file_path = f"{self.folder_name}/{city['city_name']}_{formatted_date}.csv"  # Set the file path for saving data
    
        categories = []
        while True:
            result = self.__get_categories(city)  # Retrieve categories for the city
            if result is not None:
                categories = result  # Assign the retrieved categories
                break
            time.sleep(5)  # Wait before retrying to get categories
    
        selectedCategories = []
        keywords = ["super", "marjane", "mfccas", "carrefour", "march"]  # Keywords to select relevant categories
        # Select categories containing specific keywords for scraping
        selectedCategories = [category for category in categories if any(keyword in category["category_url"] for keyword in keywords) or any(keyword in category["category_name"].lower() for keyword in keywords)]
    
        # Scrape supermarkets within the selected categories for the city
        for category in selectedCategories:
            self.__scrape_supermarket(category, city["city_name"], file_path)

    def __create_driver(self) -> tuple:
        """
        Create a WebDriver instance for web scraping.
    
        This method sets up a WebDriver instance with the specified options, including handling headless mode,
        proxy configurations, browser window size, and wait conditions.
    
        Returns:
        - tuple: A tuple containing the WebDriver instance and WebDriverWait object.
        """
    
        options = Options()  # Initialize browser options
        if os.getenv("ENV") != "dev":
            options.add_argument("headless")  # Enable headless mode if not in development environment
        options.add_argument("--disable-gpu")
        options.add_argument("--enable-features=SameSiteByDefaultCookies,CookiesWithoutSameSiteMustBeSecure")
    
        proxies = self.__get_proxy()  # Retrieve proxy configuration
        driver = None
        wait = None
    
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
            else:
                driver = webdriver.Chrome(options=options)  # Create WebDriver without proxy settings
    
            driver.set_window_size(1920, 1600)  # Set browser window size
            wait = WebDriverWait(driver, 30, ignored_exceptions=[NoSuchElementException, StaleElementReferenceException])  # Set WebDriverWait object
            return (driver, wait)  # Return the WebDriver instance and WebDriverWait object
        except Exception as e:
            print(f"Booting Driver Error: {e}")  # Log any errors that occur during WebDriver setup
            return (None, None)  # Return None values if WebDriver setup fails

    def __get_categories(self, city: dict[str, str]):
        try:
            url = city["city_url"]
            (_, status_code) = self.__get_response_until_success(url)
            if not url.startswith("http"):
                url = f"https://www.glovoapp.com{url}"
            print(f'{url} -> status : {status_code}')
            if status_code == 404 or status_code == 301: return []
            driver, wait = self.__create_driver()
            while driver is None:
                time.sleep(5)
                driver, wait = self.__create_driver()
            if driver is None:
                print("can't create chrome driver")
                return []
            categories = []
            while True:
                driver.get(url)
                
                elements = driver.find_elements(By.XPATH, "//section[@class='desktop-bubbles']//a[@class='category-bubble__link']")
                
                for element in elements:
                    name = element.text.replace("\n", "").strip()
                    href = element.get_attribute("href")
                    categories.append({"category_name": name, "category_url" : href})
                if len(categories) > 0: break
                error_elements = driver.find_elements(By.XPATH, "//div[@class='error-page']")
                if len(error_elements) == 0:
                    break
                time.sleep(5)
                print(f"Waiting for {url} on selenium")
            locator = (By.XPATH, "//section[@class='desktop-bubbles']//div[@class='category-bubble__link']")
            wait.until(all_elements_clickable(locator))
            bubble_elements = driver.find_elements(By.XPATH, "//section[@class='desktop-bubbles']//div[@class='category-bubble__link']")
            bubble_elements = [element for element in bubble_elements if "Service" not in element.text and "Coursier" not in element.text ]
            time.sleep(10)
            for index, element in enumerate(bubble_elements):
                bubble_links = []
                count = 0
                while len(bubble_links) == 0:
                    try:
                        element.click()
                        print('click to bubble element')
                        count += 1
                        if count > 20: break
                        time.sleep(2)
                    except Exception as e:
                        print(e)
                    bubble_links = driver.find_elements(By.XPATH, "//div[@class='modal-wrapper bubble-modal']//a[@class='category-bubble__link']")
                for bubble in bubble_links:
                    name = bubble.text.replace("\n", "").strip()
                    href = bubble.get_attribute("href")
                    categories.append({"category_name": name, "category_url" : href})
                # Click at coordinates (10, 10)
                if index >= len(bubble_elements) - 1:
                    break
                modal_overlay_tag = driver.find_element(By.CLASS_NAME, "modal-overlay")
                action = ActionChains(driver)
                action.move_to_element_with_offset(modal_overlay_tag, 200, 200).click().perform()
                count = 0
                while modal_overlay_tag.value_of_css_property("display") != 'none':
                    if count > 10: return None
                    action.move_to_element_with_offset(modal_overlay_tag, -40 * count, 0).click().perform()
                    print("Element display is not 'none'. Clicking again. {}")
                    cursor_position = driver.execute_script("return [window.scrollX + window.innerWidth, window.scrollY + window.innerHeight];")
                    print("Cursor Position:", cursor_position)
                    count += 1
                    time.sleep(3)
                time.sleep(2)
            driver.quit()
            return remove_duplicates(categories, "category_url")
        except Exception as e:
            print(f"Error in selenium : {e}")
            driver.quit()
            return None
        
    def __get_full_url(self, url : str):
        return f"https://www.glovoapp.com{url}" if not url.startswith("http") else url

    def __scrape_supermarket(self, category : dict[str, str], city : str, file_path: str):
        print(f'++ ++ ++ category : {category["category_name"]} / {category["category_url"]} ++ ++ ++')
        url = category['category_url']
        url = self.__get_full_url(url)
        page_text_element = None
        stores = []
        response, _ = self.__get_response_until_success(url)
        if response == "":
            return
        soup = BeautifulSoup(response, "html.parser")

        page_text_element = soup.find("span", class_="current-page-text")
        page_size = 1
        try:
            page_size = int(page_text_element.get_text(strip=True).split().pop()) if page_text_element is not None else 1
        except:
            page_size = 1

        store_elements = soup.select("div.category-page__pagination-wrapper > div a")
        if len(store_elements) == 0:
            stores.append({"store_name": "", "store_url": category['category_url'], "store_tag": ""})
        for store_element in store_elements:
            store_name_element = store_element.select_one(".store-card__footer__title")
            store_name = store_name_element.get_text(strip=True)
            store_tag_element = store_element.select_one(".store-card__footer__tag")
            store_tag = store_tag_element.get_text(strip=True) if store_tag_element is not None else ""
            store_url = store_element.get("href")
            stores.append({"store_name": store_name, "store_url": store_url, "store_tag": store_tag})
        
        count = 2
        while count <= page_size:
            print(f'====> category : {category["category_name"]} : {category["category_url"]}?page={count} --- --- ---')
            response, _ = self.__get_response_until_success(f"{url}?page={count}")
            if response == "":
                count += 1
                continue
            soup = BeautifulSoup(response, "html.parser")
            store_elements = soup.select("div.category-page__pagination-wrapper > div a")
            
            if len(store_elements) == 0:
                stores.append({"store_name": "", "store_url": category['category_url'], "store_tag": ""})
            for store_element in store_elements:
                store_name = store_element.select_one(".store-card__footer__title").get_text(strip=True)
                store_tag_element = store_element.select_one(".store-card__footer__tag")
                store_tag = store_tag_element.get_text(strip=True) if store_tag_element is not None else ""
                store_url = store_element.get("href")
                stores.append({"store_name": store_name, "store_url": store_url, "store_tag": store_tag})

            count += 1

        for store in stores:
            print(f'========> store : {store["store_name"]} / {store["store_url"]} --- ---')
            url = self.__get_full_url(store['store_url'])
            response, _ = self.__get_response_until_success(url)
            soup = BeautifulSoup(response, "html.parser")
            section_elements = soup.find_all("div", class_="store__body__dynamic-content")
            collections = []
            if len(section_elements) > 1:
                section_elements.pop(0)
            for section_element in section_elements:
                section_title_element = section_element.select_one("h2.grid__title")
                section_title= ""
                if section_title_element is None : section_title_element = section_element.select_one("h2.carousel__title")
                if section_title_element is not None: section_title = section_title_element.get_text(strip=True)
                collection_elements = section_element.select("div.grid__content a")
                if len(collection_elements) == 0: collection_elements = section_element.select("div.carousel__content a")
                print("============> section : " + section_title + "---")
                for collection_element in collection_elements:
                    collection_name = collection_element.select_one("div.tile__description").get_text(strip=True)
                    collection_url = collection_element.get("href")
                    collections.append({"collection_name": collection_name, "collection_url": collection_url, "section_name": section_title, "city_name": city, "store_name": store["store_name"], "category_name": category["category_name"], "file_path": file_path})
                print(f"number of collections : {len(collections)}")
                if len(collections) == 0:
                    collections.append({"collection_name": "", "collection_url": store['store_url'], "section_name": section_title, "city_name": city, "store_name": store["store_name"], "category_name": category["category_name"], "file_path": file_path})
            
            
            max_threads = 30
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                # Map each collection to the future object executing it
                future_to_collection = {executor.submit(self.__scrape_collection, collection): collection for collection in collections}
                
                results = []
                # Iterate over the futures as they complete (in the order they complete)
                for future in as_completed(future_to_collection):
                    collection = future_to_collection[future]
                    try:
                        # Get the result from the future
                        result = future.result()
                        results.append(result)
                    except Exception as exc:
                        # Handle any exceptions that were raised during processing
                        print(f'Collection {collection} generated an exception: {exc}')
                        results.append(None)  # Or handle this another way
            

            for products in results:
                print(f"saving {len(products)} products")
                self.__save_products(products, file_path)

    def __scrape_collection(self, collection):
        print(f"------- collection : {collection['collection_url']} --------")
        url = self.__get_full_url(collection['collection_url'])
        response, _ = self.__get_response_until_success(url)
        soup = BeautifulSoup(response, "html.parser")
        group_elements = soup.select("div.store__body__dynamic-content")
        products = []
        for group_element in group_elements:
            group_title_element = group_element.select_one("h2.grid__title")
            group_name = group_title_element.get_text(strip=True) if group_title_element is not None else ""
            products_elements = group_element.select("div.grid__content > section")
            print(f"------- Group : {group_name}")
            for product_element in products_elements:
                product_image = product_element.select_one('img').get("src") if product_element.select_one('img') else ""
                product_name = product_element.select_one('span.tile__description').get_text(strip=True)  if product_element.select_one('span.tile__description') else ""
                product_price_text = product_element.select_one('span.product-price__effective').get_text(strip=True) if product_element.select_one('span.product-price__effective') else ""
                product_price, product_currency = ("", "")
                if len(product_price_text.split()) == 1: product_price = product_price_text
                elif len(product_price_text.split()) >= 2: product_price, product_currency = product_price_text.split()
                product_original_price_element = product_element.select_one('span.product-price-original')
                product_original_price = product_original_price_element.get_text(strip=True).split(" ")[0] if product_original_price_element is not None else ''
                product = {
                    "product_id" : self.__get_hash(f"{product_name}_{product_image}"),
                    "city" : collection["city_name"],
                    "category" : collection["category_name"],
                    "store" : collection["store_name"],
                    "section" : collection["section_name"],
                    "collection" : collection["collection_name"],
                    "group" : group_name,
                    "name" : product_name,
                    "image" : product_image,
                    "price" : product_price,
                    "currency" : product_currency,
                    "original_price" : product_original_price,
                    "url" : self.__get_full_url(collection["collection_url"]),
                    "date" : datetime.datetime.utcnow().isoformat() + 'Z'
                }
                products.append(product)
        self.__store_products(products, collection["file_path"])
        return products

    def __store_products(self, products:list[dict[str, str]], file_path):
        print(f"store {len(products)} products")
        if len(products) == 0: return
        updated_products = [(*(self.__adjust_special_characters(list(product.values()))), file_path) for product in products]
        placeholders = f"({', '.join(['%s' for _ in range(len(updated_products[0]))])})"
        insert_query = f"INSERT INTO {self.table_name} ({', '.join([f'`{value}`' for value in self.columns])}) VALUES {placeholders}"
    
        while True:
            try:
                conn = mysql.connector.connect(**self.config)
                cursor = conn.cursor()
                cursor.executemany(insert_query, updated_products) 
                conn.commit()
                cursor.close()
                conn.close()
                break
            except Exception as e:
                print(e) 
                time.sleep(1)

    def __get_hash(self, text):
        data = text
        hash_object = hashlib.sha256()
        hash_object.update(data.encode())
        hashed_data = hash_object.hexdigest()
        return hashed_data
    
    def __adjust_special_characters(self, values:list[str]):
        return [value.replace("'", "\'").replace('"', "\"") for value in values]