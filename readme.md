
# Glovo Scraping Project

## Introduction

This project is designed to scrape the Glovo website for products collection purposes. The scraper automates the process of extracting information and storing it in both a MySQL database and CSV files on the file system.

## Prerequisites

Before setting up the project, please ensure you have the following prerequisites ready:
- Docker installed on your system
- A MySQL database accessible to store the scraped data

## Configuration

### 1. Environment Setup

You need to configure environment variables for the application to connect with your database. For this purpose, create a `.env` file in the root directory of the project with the following content:

```plaintext
MYSQL_USER="username"            # Replace with your MySQL username, e.g., "root"
MYSQL_PASSWORD="password"        # Replace with your MySQL password
MYSQL_HOST="database_host"       # Replace with your MySQL host, e.g., "127.0.0.1"
MYSQL_DATABASE="database_name"   # Replace with your MySQL database name, e.g., "glovo"
```

_Note: Don't include spaces around the "=" sign._

### 2. Proxy Configuration (Optional)

To prevent IP blocking by the target site, it's recommended to use proxies. If you have proxy servers available, list them in the `proxies.txt` file. Each line should contain one proxy in the following format:

```plaintext
http://proxy_username:proxy_password@proxy_ip_1:proxy_port
http://proxy_username:proxy_password@proxy_ip_2:proxy_port
http://proxy_username:proxy_password@proxy_ip_3:proxy_port
...
```

Replace `proxy_username`, `proxy_password`, `proxy_ip_1`, `proxy_port`, etc., with your actual proxy details.

## Installation

Docker must be installed to run this project. Download and install Docker from [the official Docker website](https://www.docker.com/get-started) if you haven't already.

## Usage

After setting up the configuration files, you can proceed with running the project using Docker Compose. Execute the following commands in your terminal:

```bash
sudo docker-compose build
sudo docker-compose up -d
```

The scraper is set to restart automatically in case of errors after a 30-second delay. It will also auto-restart daily upon successful completion of its scraping tasks.

## Logs and Results

The application generates logs that are captured in the `output.txt` file. This allows you to check the progress and status of the scraping process.

Scraped data is stored both as CSV files located in the `results` folder and in the `products` table within your specified MySQL database.