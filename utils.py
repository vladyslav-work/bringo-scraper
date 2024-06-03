from selenium.webdriver.support import expected_conditions as EC

class all_elements_clickable:
    def __init__(self, locator):
        self.locator = locator
    
    def __call__(self, driver):
        elements = driver.find_elements(*self.locator)
        filtered_elements = [element for element in elements if "Service" not in element.text]
        return all([EC.element_to_be_clickable(element) for element in filtered_elements]) 
    
def remove_duplicates(list_of_dicts, key):
    seen = set()             
    new_list = []
    for d in list_of_dicts:
        value = d[key]
        if value not in seen:
            seen.add(value)
            new_list.append(d)
    return new_list
