# encoding: utf-8

# Copyright 2012-2015 Marian Steinbach, Ernesto Ruge. All rights reserved.
# Use of this source code is governed by BSD 3-Clause license that can be
# found in the LICENSE.txt file.

from flask.ext.script import Manager

from webapp import app
from webapp import util
from scripts import init_webapp as init_webapp_script
from scripts import osm_import as osm_import_script
from scripts import osm_import_es as osm_import_es_script

manager = Manager(app)

@manager.command
def init():
  init_webapp_script.run()

@manager.command
def verify_created_modified():
  util.verify_created_modified()

@manager.command
def osm_import(city_id):
  osm_import_script.run(city_id)

@manager.command
def osm_import_es():
  osm_import_es_script.run()


if __name__ == "__main__":
  manager.run()