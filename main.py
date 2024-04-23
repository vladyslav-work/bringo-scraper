from glovo_scraper import GlovoScraper
import os
import time

def scrape_glovo():

    folder_path = "results"
    excluding_cities = [os.path.splitext(f)[0] for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

    print(excluding_cities)

    # read proxies
    proxies_file_path = "proxies.txt"
    proxies = []
    if os.path.exists(proxies_file_path):
        with open(proxies_file_path, 'r') as file:
            proxies = file.readlines()
    proxies = [proxy.strip().replace("\n", "").replace(",", "") for proxy in proxies if len(proxy.strip().replace("\n", "").replace(",", "")) > 0]    
    print(proxies)
    scraper = GlovoScraper(excluding_city_names=excluding_cities, proxies=proxies)
    scraper.start_scrape()

if __name__ == "__main__":
    while True:
        try:
            scrape_glovo()
            print("Succeeded Scraping, it will restart in a day")
            time.sleep(24 * 60 * 60)
        except Exception as e:
            print(f"Stopped Scraping : {e}\n After 30s, it will restart.")
            time.sleep(30)