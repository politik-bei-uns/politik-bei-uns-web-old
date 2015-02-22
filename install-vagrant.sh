#!/bin/bash

# Java Current for Elasticsearch
sudo apt-get update
sudo apt-get install python-software-properties software-properties-common
sudo add-apt-repository ppa:webupd8team/java
sudo apt-get update
sudo apt-get install -y oracle-java8-installer 

# Elasticsearch
wget -qO - https://packages.elasticsearch.org/GPG-KEY-elasticsearch | sudo apt-key add -
echo 'deb http://packages.elasticsearch.org/elasticsearch/1.4/debian stable main' | sudo tee /etc/apt/sources.list.d/elasticsearch.list
sudo apt-get update
sudo apt-get install -y elasticsearch
sudo update-rc.d elasticsearch defaults 95 10

# MongoDB
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 7F0CEB10
echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' | sudo tee /etc/apt/sources.list.d/mongodb.list
sudo apt-get update
sudo apt-get install -y mongodb-10gen

# More Packages
sudo apt-get install -y git memcached python-virtualenv build-essential python-dev libxml2-dev libxslt1-dev ghostscript poppler-utils libpng12-dev libfreetype6-dev protobuf-compiler libprotobuf-dev libjpeg-dev

mkdir venvs

# Einrichtung des Webinterfaces
virtualenv venvs/ris-web
venvs/ris-web/bin/pip install --upgrade setuptools pip
venvs/ris-web/bin/pip install numpy
venvs/ris-web/bin/pip install -r /vagrant/requirements.txt

#echo "Erstelle Konfiguration"
#cp config_dist.py config.py
#replace="BASIC_AUTH_USERNAME = '$username'"#sed -i "46s/.*/$replace/" config.py
#replace="BASIC_AUTH_PASSWORD = '$password'"
#sed -i "47s/.*/$replace/" config.py
#secret_key=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)
#replace="SECRET_KEY = '$secret_key'"
#sed -i "48s/.*/$replace/" config.py

# Einichtung des Scrapers
virtualenv venvs/ris-scraper
venvs/ris-scraper/bin/pip install --upgrade setuptools pip
venvs/ris-scraper/bin/pip install -r /ris-scraper/requirements.txt

# Importiere Konfiguration
mongoimport --db ris  --collection config --type json --jsonArray --file /vagrant/config/init.config.json
