# Offenes Ratsinformationssystem

## Über dieses Repository

Dies ist das github-Repository für das [Offene Ratsinformationssystem](http://politik-bei-uns.de/).

Hier gibt es:

- Dokumentation (im [Wiki](https://github.com/okfde/ris-web/wiki))
- Die API (auf der [Oparl Seite](http://oparl.org/))
- [Issue-Tracking](https://github.com/okfde/ris-web/issues), also die Erfassung und Zuweisung von Fehlern
- Die [Installationsanleitung](https://github.com/okfde/ris-web/blob/master/INSTALL.txt)
- Quellcode

Der Bereich **Quellcode** enthält folgende Dateien:

- webapp: Die Web-Applikation
- scripts: Unterstützende Werkzeuge und Helferlein
- config: Startkonfiguration, Startdatenbank

Der **Scraper**, mit dem die Daten aus dem Ratsinformationssystemen der Unternehmen SessionNet und AllRis ausgelesen werden, ist ein eigenes Projekt auf Github:

[https://github.com/okfde/ris-scraper/](https://github.com/okfde/ris-scraper/)

###Installation mit Vagrant (z.B. für OSX, Windows)

Mit den folgenden Schritten kannst du ris-web in einer virtuellen Maschine installieren.

0. ris-web und ris-scraper clonen und in das ris-web Verzeichnis wechseln
```
	$ git clone https://github.com/okfde/ris-scraper.git
	$ git clone https://github.com/okfde/ris-web.git
	$ cd ris-web
```
1. [VirtualBox](https://www.virtualbox.org/) installieren
2. [Vagrant](http://vagrantup.com/) installieren
3. Vagrant Box runterladen und provisionieren

   ```
     $ vagrant plugin install vagrant-vbguest
     $ vagrant up
   ```
4. ris-web starten:

   ```
   	$ vagrant ssh
   	$ venvs/ris-web/bin/python /vagrant/runserver.py
   ```

Now you should see ris-web up and running at [http://localhost:23000](http://localhost:23000)

###Lizenz

Der Code steht unter einer MIT-artigen [Lizenz](https://github.com/okfde/ris-web/blob/master/LIZENZ.txt).

###Geschichte

Dieses Projekt ist eine Weiterentwicklung des von Marian Steinbach gestarteten Projektes [Offenes Köln](https://github.com/marians/offeneskoeln/)