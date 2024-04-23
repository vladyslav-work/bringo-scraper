# Glovo Scraping Project

## Preparation for Running the Project

Before running the project, ensure you have added the necessary `.env` and `proxies.txt` (optional) files.

### .env File

Create a `.env` file with the following format:

```plaintext
MYSQL_USER = "username" # e.g. "root"
MYSQL_PASSWORD = "password" # e.g. ""
MYSQL_HOST = "database_host" # e.g. "127.0.0.1"
MYSQL_DATABASE = "database_name" # e.g. "glovo"
```

### proxies.txt

The `proxies.txt` file is optional but recommended to prevent IP blocking by the Glovo site. An example format is as follows:

```plaintext
http://poxy_username:proxy_password@proxy_ip_1:proxy_port
http://poxy_username:proxy_password@proxy_ip_2:proxy_port
http://poxy_username:proxy_password@proxy_ip_3:proxy_port
...
```

## Running the Project

To run the project, execute the following commands in your terminal:

```bash
docker compose build
docker compose up -d
```

If an error occurs during scraping, it will automatically restart after 30 seconds. Upon successful completion, the scraping process will restart daily.

All logs are stored in `output.txt`, allowing you to monitor the project's status.

The results of the scraping can be found in CSV files within the `results` folder and in the `products` table within your database.