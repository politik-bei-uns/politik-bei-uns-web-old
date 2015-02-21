#!/bin/bash

#echo "In welchen existierenden Ordner sollen Weboberfläche und Scraper installiert werden? (z.B. /srv/www)"

#read basepath

#if [ ! -d $basepath ]
#  then
#    echo "Dieser Ordner existiert nich."
#    exit 0
#fi

mkdir /srv/www
basepath="/srv/www"

#echo "Unter welchem Host kann die Weboberfläche später abgerufen werden? Für Testumgebungen: Port 23000 nicht vergessen. (z.B. localhost:23000)"
#read basehost

#echo "Welcher Admin-Nutzername soll genutzt werden?"
#read username

#echo "Welches Admin-Passwort soll genutzt werden?"
#read password

# Java Current for Elasticsearch
echo "Installiere Oracle Java 8 für ElasticSearch"
apt-get update
apt-get install software-properties-common
add-apt-repository ppa:webupd8team/java
apt-get update
apt-get install -y oracle-java8-installer 

# Elasticsearch
echo "Installiere ElasticSearch"
wget -qO - https://packages.elasticsearch.org/GPG-KEY-elasticsearch | sudo apt-key add -
echo 'deb http://packages.elasticsearch.org/elasticsearch/1.4/debian stable main' | sudo tee /etc/apt/sources.list.d/elasticsearch.list
apt-get update
apt-get install -y elasticsearch
update-rc.d elasticsearch defaults 95 10

# MongoDB
echo "Installiere MongoDB"
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 7F0CEB10
echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' | sudo tee /etc/apt/sources.list.d/mongodb.list
apt-get update
apt-get install -y mongodb-10gen

# More Packages
echo "Installiere weitere Pakete"
apt-get install -y git memcached python-virtualenv build-essential python-dev libxml2-dev libxslt1-dev ghostscript poppler-utils libpng12-dev libfreetype6-dev protobuf-compiler libprotobuf-dev libjpeg-dev
echo "Füge Systemnutzer hinzu und erstelle Pfade"

mkdir $basepath/ris-scraper
chown ris:ris -R $basepath/ris-scraper/
mkdir $basepath/ris-web
chown ris:ris -R $basepath/ris-web/

# Einrichtung des Webinterfaces
sudo -u ris bash << EOF
export HOME=/home/ris
cd $basepath/ris-web
echo "Downloade Webinterface"
git clone https://github.com/okfde/ris-web.git .
echo "Erstelle Virtual Enviroment für Webinterface"
virtualenv venv
echo "Installiere benötigte Pakete in Virtual Enviroment"
$basepath/ris-web/venv/bin/pip install --upgrade setuptools pip
$basepath/ris-web/venv/bin/pip install numpy
$basepath/ris-web/venv/bin/pip install -r requirements.txt
EOF
#echo "Erstelle Konfiguration"
#cp config_dist.py config.py
#replace="BASIC_AUTH_USERNAME = '$username'"
#sed -i "46s/.*/$replace/" config.py
#replace="BASIC_AUTH_PASSWORD = '$password'"
#sed -i "47s/.*/$replace/" config.py
#secret_key=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)
#replace="SECRET_KEY = '$secret_key'"
#sed -i "48s/.*/$replace/" config.py


# Einichtung des Scrapers
sudo -u ris bash << EOF
export HOME=/home/ris
cd $basepath/ris-scraper
echo "Downloade Scraper"
git clone https://github.com/okfde/ris-scraper.git .
echo "Erstelle Virtual Enviroment für Scraper"
virtualenv venv
echo "Installiere benötigte Pakete in Virtual Enviroment"
$basepath/ris-scraper/venv/bin/pip install --upgrade setuptools pip
$basepath/ris-scraper/venv/bin/pip install -r requirements.txt
EOF

# Importiere Konfiguration
mongoimport --db ris  --collection config --type json --jsonArray --file $basepath/ris-web/config/init.config.json

