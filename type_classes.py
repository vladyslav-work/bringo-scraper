from selenium.webdriver.support import expected_conditions as EC

class Product:
    def __init__(self, name: str, price: float, currency: str, description: str, image: str, category: str, brand: str, vendor: str):
        self.name = name
        self.price = price
        self.currency = currency
        self.description = description
        self.image = image
        self.category = category
        self.brand = brand
        self.vendor = vendor

    def keys(self):
        return ["name", "price", "currency", "description", "image", "category", "brand", "vendor"]

    def to_dict(self):
        return {
            "name": self.name,
            "price": self.price,
            "currency": self.currency,
            "description": self.description,
            "image": self.image,
            "category": self.category,
            "brand": self.brand,
            "vendor": self.vendor
        }


class all_elements_clickable:
    def __init__(self, locator):
        self.locator = locator
    
    def __call__(self, driver):
        elements = driver.find_elements(*self.locator)
        filtered_elements = [element for element in elements if "Service" not in element.text]
        return all([EC.element_to_be_clickable(element) for element in filtered_elements]) 

    