import time
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

from bs4 import BeautifulSoup
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils import all_elements_clickable
from scraper import Scraper
from selenium.webdriver.support import expected_conditions as EC


def remove_duplicates(list_of_dicts, key):
    seen = set()
    new_list = []
    for d in list_of_dicts:
        value = d[key]
        if value not in seen:
            seen.add(value)
            new_list.append(d)
    return new_list

class BringoScraper(Scraper):
    # Class variables - Name of scraper, main url of the site and the url of the page that contain urls of cities
    name = 'Bringo-Scraper'
    city = 'Boulevard Mohamed V, Casablanca'
    tower = 44
    main_url = "https://www.bringo.ma"

    # Name of the database table
    table_name = "bringo_products"    
    
    # Folder name for storing csv files
    folder_name = "bringo_products"
    cookies = {}

    def __init__(self):
        """
        Initialize the Bringo Scraper with provided parameters.
        """

        super().__init__(self.main_url, self.folder_name)
        current_date = datetime.datetime.now()  # Get the current date and time
        self.file_path = f"{current_date.strftime('%Y_%m_%d_%H_%M')}.csv"  # Format the date
    
    # def __del__(self):
    #     """
    #     Clean up resources when the GlovoScraper instance is deleted.
    
    #     This method closes the database cursor and connection to ensure proper cleanup.
    #     """
    #     super()

    def run(self, city=None):
        """
        Start the scraping process.
    
        This method initiates the scraping process based on the specified city or all available cities.
        If a specific city is provided, it scrapes data for that city; otherwise, it scrapes data for all cities.
        
        Parameters:
        - city (str): The name of the city to scrape. If None, data will be scraped for all cities except those in the exclusion list.
        """
    
        print('START scraping')  # Print a message indicating the start of the scraping process
        markets = self.__get_markets()
        stores = [store for market in markets for store in self.__get_stores(market)]
        for store in stores:
            self.__scrape_store(store)
    
    def __scrape_store(self, store):
        print(f'===> store : {store["store_name"]} / {store["store_url"]}')
        pages = self.__get_pages(store)
        print(f'---> pages : {len(pages)}')
        products_list = self._apply_multi_threading(pages, self.__get_products)
        print(f'---> product lists : {len(products_list)}')
        products = [product for products in products_list for product in products]
        print(f'---> found products : {len(products)}')
        products = self._apply_multi_threading(products, self.__scrape_product)
        print(f'---> store products : {len(products)}')
        self._save_products_in_csv(products, self._get_file_path(f"{store['store_name']}_{self.file_path}"))
        
    def __get_products(self, page: dict[str, str]) -> dict[str, str]:
        print(f'---> page : {page["store_url"]}')
        response, _ = self._get_response_until_success(page["store_url"], cookies=self.cookies)  # Get the response from the cities URL
        if response == "":
            return []
        soup = BeautifulSoup(response, "html.parser")
        product_elements = soup.select(".box-product a")
        products = []
        for element in product_elements:
            products.append({
                **page,
                "product_url": element.get("href")
            })
        return products
    
    def __scrape_product(self, product: dict[str, str]) -> dict[str, str]:
        print(f'---> product : {product["product_url"]}')
        response, _ = self._get_response_until_success(product["product_url"], cookies=self.cookies)  # Get the response from the cities URL
        if response == "":
            return []
        soup = BeautifulSoup(response, "html.parser")
        product_name = soup.select_one("h1.product-name").get_text(strip=True)
        price_list = soup.select_one(".product-price").get_text(strip=True).split()
        calculator = soup.select_one("div.product-price-calculator")
        product_price= ""
        product_currency= ""
        
        if calculator:
            price_element = soup.select_one("div.product-price-calculator p:first-child")
            product_price, product_currency = price_element.get_text(strip=True).replace("~", "").replace("/", "").strip().split()
        else: product_price, product_currency = soup.select_one(".product-price").get_text(strip=True).replace("~", "").replace("/", "").strip().split()
        product_brand = ""
        product_number = ""
        product_description = ""
        
        images_elements = soup.select(".thumbnail-image img")
        product_images = [element.get("src") for element in images_elements]
        
        details_elements = soup.select("#details p")
        if len(details_elements) == 0:
            description_element = soup.select_one("#details")
            product_description = description_element.get_text(separator="\n", strip=True) if description_element else ""
        else :
            for element in details_elements:
                content = element.get_text(strip=True)
                if "Numéro du produit" in content:
                    product_number = content.split(":").pop().strip()
                elif "Marque" in content:
                    product_brand = content.split(":").pop().strip()
                else:
                    product_description += element.get_text(separator="\n", strip=True)
        product_image = soup.select_one("#main-image").get("src")
        return {
            "product_id": self._get_hash(f"{product_name}_{product_image}"),
            "market": product["market_name"],
            "market_image": product["market_image"],
            "store": product["store_name"],
            "store_image": product["store_image"],
            "name": product_name,
            "price": product_price,
            "currency": product_currency,
            "brand": product_brand,
            "description": product_description,
            "number": product_number,
            "image": product_image,
            "images": ",".join(product_images),
            "url": self._get_full_url(product["product_url"]),
            "date": datetime.datetime.utcnow().isoformat() + "Z"
        }

    def __get_stores(self, market: dict[str, str]) -> list[dict[str, str]]:
        response, _ = self._get_response_until_success(market["market_url"], cookies=self.cookies)  # Get the response from the cities URL
        # with open("response.html", "w") as file:
        #     file.write(str(response))
        if response == "":
            return []
        soup = BeautifulSoup(response, "html.parser")
        store_elements = soup.select(".box-inner")
        stores = []
        for store_element in store_elements:
            store_url = store_element.get("href")
            store_image = store_element.select_one("img").get("src")
            store_name = store_element.select_one("h4").get_text(strip=True)
            stores.append({
                "market_name": market["market_title"],
                "market_image": market["market_image"],
                "market_open_programs": market["market_open_programs"],
                "market_close_program": market["market_close_program"],
                "store_url": store_url,
                "store_image": store_image,
                "store_name": store_name
            })
        return stores

    def __get_pages(self, store: dict[str, str]) -> list[dict[str, str]]:
        response, _ = self._get_response_until_success(store["store_url"])
        if response == "":
            return []
        soup = BeautifulSoup(response, "html.parser")
        pagination = soup.select('ul.pagination a.page-link')
        page_size = 1
        if pagination:
            page_size = int(pagination[-2].get_text()) if len(pagination) >= 2 else 1
        pages = [store]
        count = 2
        while count <= page_size:
            page_url = f"{store['store_url']}?page={count}"
            page = {**store}
            page["store_url"] = page_url
            pages.append(page)
            count += 1

        print(f"Page size of category {store['store_name']} : {len(pages)}")
        return pages

    def __get_markets(self):
        try:
            (_, status_code) = self._get_response_until_success(self.main_url)
            print(f'{self.main_url} -> status : {status_code}')
            if status_code == 404 or status_code == 301 or status_code == 500: return []
            driver, wait = self._create_driver()
            while driver is None:
                time.sleep(5)
                driver, wait = self._create_driver()
            if driver is None:
                print("can't create chrome driver")
                return []
            driver.get(self.main_url)
                
            address_xpath = '//*[@id="address"]'
            street_num_xpath = '//*[@id="street_number"]'

            street_num = driver.find_element(By.XPATH, street_num_xpath)
            street_num.send_keys(self.tower)

            address = driver.find_element(By.XPATH, address_xpath)
            address.send_keys(self.city)
            address.click()
            
            wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'pac-item'))).click()

            button = driver.find_element(By.XPATH, '//*[@id="view_stores"]')
            button.click()
            markets_list = wait.until(EC.presence_of_element_located((By.ID, 'stores-list')))
            markets_elements_soup = BeautifulSoup(markets_list.get_attribute("outerHTML"), "html.parser")
            markets_elements = markets_elements_soup.select(".box-store")
            markets = []
            for market_element in markets_elements:
                market_url = market_element.select_one("a").get("href")
                market_title = market_element.select_one(".store-title").get_text(strip=True)
                market_image = market_element.select_one(".store-image-thumbnail img").get("src")
                market_close_program_element = market_element.select_one(".store-close-program")
                market_close_program = ""
                if market_close_program_element:
                    market_close_program = market_close_program_element.get_text(strip=True)
                market_open_program_elements = market_element.select(".store-program-day")
                market_open_programs = []
                for market_open_program_element in market_open_program_elements:
                    print(4)
                    market_open_program_week_day = market_open_program_element.select_one(".store-program-week-day").get_text(strip=True)
                    print(5)
                    market_open_program_time = market_open_program_element.get_text(strip=True).replace(market_open_program_week_day, "").strip()
                    market_open_programs.append({
                        "week_day": market_open_program_week_day,
                        "time": market_open_program_time
                    })
                markets.append({
                    "market_url": market_url,
                    "market_image": market_image,
                    "market_title": market_title,
                    "market_close_program": market_close_program,
                    "market_open_programs": market_open_programs 
                })
                pass
            print(driver.get_cookies())
            cookie = driver.get_cookie("PHPSESSID")
            driver.quit()
            self.cookies = {"PHPSESSID": cookie["value"]}
            return markets
                

        except Exception as e:
            print(f"Error in selenium : {e}")
            driver.quit()
            return []
  
if __name__ == "__main__":
    bot = BringoScraper()
    bot.run()
