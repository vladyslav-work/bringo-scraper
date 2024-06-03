FROM python:3.10.11

#set ENV
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update -y \
    && apt-get upgrade -y \
    && apt-get install -y python3-dev libproj-dev pkg-config build-essential wget unzip

# install google chrome
# RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
# RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
# RUN apt-get -y update
# RUN apt-get install -y google-chrome-stable
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
#run this command to install Chrome using the offline installer:
RUN apt-get install -y ./google-chrome-stable_current_amd64.deb
RUN apt-get -f install

# install chromedriver
RUN apt-get update && apt-get install -yqq unzip
RUN wget https://storage.googleapis.com/chrome-for-testing-public/125.0.6422.60/linux64/chromedriver-linux64.zip
RUN unzip chromedriver-linux64.zip
RUN mv chromedriver-linux64 /usr/bin/chromedriver
RUN chown root:root /usr/bin/chromedriver

# Set up project directory
WORKDIR /usr/src/glovo

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt
