# encoding: utf-8

# Copyright 2012-2015 Marian Steinbach, Ernesto Ruge. All rights reserved.
# Use of this source code is governed by BSD 3-Clause license that can be
# found in the LICENSE.txt file.

import os, shutil, subprocess, urllib, inspect
from osm import pyosm, multipolygon
from imposm.parser import OSMParser
from pymongo import MongoClient
from bson.son import SON
from bson import ObjectId, DBRef
from webapp import mongo, app
import config

# Wir legen alle nodes in diesem dict ab. Das bedeutet, dass wir
# ausreichend Arbeitsspeicher voraussetzen.
nodes = {}

class NodeCollector(object):
  def coords(self, coords):
    for osmid, lon, lat in coords:
      if osmid not in nodes:
        nodes[osmid] = {
          'osmid': osmid,
          'location': [lon, lat]
        }
      nodes[osmid]['lat'] = lat
      nodes[osmid]['lon'] = lat

class StreetCollector(object):
  wanted_nodes = {}
  streets = []

  def ways(self, ways):
    #global nodes
    for osmid, tags, refs in ways:
      if 'highway' not in tags or 'name' not in tags:
        # Wenn der way keinen "highway" tag hat oder keinen
        # Namen, ist er für uns nicht interessant.
        continue
      street = {
        'osmid': osmid,
        'name': tags['name'],
        'nodes': []
      }
      if 'postal_code' in tags:
        street['postalcode'] = tags['postal_code']
      for ref in refs:
        if ref not in nodes:
          continue
        self.wanted_nodes[ref] = True
        street['nodes'].append(ref)
      self.streets.append(street)

def run(city_id):
  tmp_base_path = '/srv/www/ris-web/temp/osm-import/'
  reuse_old_data = False
  print app.config['bodies']
  if not reuse_old_data:
    # remove old data
    if os.path.exists(tmp_base_path):
      shutil.rmtree(tmp_base_path)
    os.makedirs(tmp_base_path)
    os.chdir(tmp_base_path)
    
    # download osmosis
    subprocess.call('wget -N http://bretth.dev.openstreetmap.org/osmosis-build/osmosis-latest.tgz', shell=True)
    subprocess.call('tar xzf osmosis-latest.tgz', shell=True)
    shutil.rmtree(tmp_base_path + 'script')
    os.remove(tmp_base_path + 'osmosis-latest.tgz')
    os.remove(tmp_base_path + 'readme.txt')
    os.remove(tmp_base_path + 'copying.txt')
    os.remove(tmp_base_path + 'changes.txt')
    os.remove(tmp_base_path + 'package.iml')
    
    # download geofabrik data
    subprocess.call('wget -N -O city-regbez-latest.osm.bz2 http://download.geofabrik.de/europe/germany/%s' % app.config['bodies'][city_id]['geofabrik_data'], shell=True)
    subprocess.call('bunzip2 city-regbez-latest.osm.bz2', shell=True)
    #os.rename('%s-latest.osm' % (regbez), 'city-regbez-latest.osm')
    
    # download osmfilter
    subprocess.call('wget -O - http://m.m.i24.cc/osmfilter.c |cc -x c - -O3 -o osmfilter', shell=True)
    
    # create city.poly
    API='http://www.openstreetmap.org/api/0.6'
    osmfile = urllib.urlopen('%s/relation/%s/full' % (API, app.config['bodies'][city_id]['osm_relation']))
    osmobj = pyosm.OSMXMLFile(osmfile)
    mp = multipolygon.multipolygon(osmobj.relations[int(app.config['bodies'][city_id]['osm_relation'])])
    mp.write_osmosis_file(tmp_base_path + 'city.poly')
  
    # run osmosis to get city.osm
    subprocess.call('bin/osmosis --read-xml file="city-regbez-latest.osm" --bounding-polygon file="city.poly" --write-xml file="city.osm"', shell=True)
  
    # filter streets
    subprocess.call('./osmfilter city.osm --keep="highway=primary =secondary =tertiary =residential =unclassified =road =living-street =pedestrian" --drop-author --drop-version > city-streets.osm', shell=True)
  
  os.chdir(tmp_base_path)
  mongo.db.locations.remove({'body': DBRef('body', ObjectId(city_id))})
  mongo.db.locations.ensure_index('osmid')
  mongo.db.locations.ensure_index('name')
  mongo.db.locations.ensure_index([('nodes.location', '2dsphere')])
  
  print "Sammle Nodes..."
  nodecollector = NodeCollector()
  p = OSMParser(concurrency=2, coords_callback=nodecollector.coords)
  p.parse('city-streets.osm')

  print "Sammle Straßen..."
  streetcollector = StreetCollector()
  p = OSMParser(concurrency=2, ways_callback=streetcollector.ways)
  p.parse('city-streets.osm')

  # Iteriere über alle gesammelten nodes und finde die,
  # welche von anderen Objekten referenziert werden.
  wanted_nodes = {}
  non_existing_nodes = 0
  for ref in streetcollector.wanted_nodes.keys():
    if ref in nodes:
      wanted_nodes[ref] = nodes[ref]
    else:
      non_existing_nodes += 1

  # reduziere das nodes dict auf das wesentliche
  wanted_nodes.values()

  for street in streetcollector.streets:
    for n in range(len(street['nodes'])):
      street['nodes'][n] = {
        'osmid': street['nodes'][n],
        'location': SON([
          ('type', 'Point'),
          ('coordinates', wanted_nodes[street['nodes'][n]]['location'])
        ])
      }
    street['body'] = DBRef('body', ObjectId(city_id))
    mongo.db.locations.save(street)
  