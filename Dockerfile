FROM python:3

#set ENV
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update \
    && apt-get install netcat -y
RUN apt-get upgrade -y && apt-get install python3-dev musl-dev -y

# -- Update system
RUN apt-get update
RUN apt-get install binutils libproj-dev gdal-bin -y

# install google chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
RUN apt-get -y update
RUN apt-get install -y google-chrome-stable

# install chromedriver
RUN apt-get install -yqq unzip
RUN wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE`/chromedriver_linux64.zip
RUN unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/

# copy project
WORKDIR /usr/src/glovo
COPY . .

# setup virtual environment
RUN python3 venv -v myenv
RUN source myenv/bin/activate

# install neccesary packages
RUN apt-get install python3-dev pkg-config libmysqlclient-dev build-essential

# install python modules
RUN pip install -r requirements.txt
