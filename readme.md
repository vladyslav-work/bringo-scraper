# Glovo Scraping Project

## Environment For the Project

### Required tools

- python 3.10
- Chrome 123.x
- Chrome driver 123.x  

unzip chrome driver zip file and paste all files in `C:/windows`

### Create virtual environment

In the project, open the terminal

- Install `virtualenv` if it's not already installed:
```bash
pip install virtualenv
```
- Create a virtual environment
```bash
python -m venv myenv
```
- Activate the virtual environment:
```bash
myenv\Scripts\activate
```
- Install required modules
```bash
pip install -r requirements.txt
```

## Preparation for Run

### .env file

```
MYSQL_USER = "username" # e.g. "root"
MYSQL_PASSWORD = "password" # e.g. ""
MYSQL_HOST = "database_host" # e.g. "127.0.0.1"
MYSQL_DATABASE = "database_name" # e.g. "glovo"
```

### proxies.txt

This file is needed to avoid blocking your ip address by glovo site  
For example:
```
http://poxy_username:proxy_password@proxy_ip_1:proxy_port
http://poxy_username:proxy_password@proxy_ip_2:proxy_port
http://poxy_username:proxy_password@proxy_ip_3:proxy_port
...
```

## Run the project
On the terminal:
```cmd
py main.py
```
If an error occurs, scraping will start again after 30 seconds
If the scraping finished successfully, it will restart after a day

You can see csv files in `results` folder and products in the table `products` of your database