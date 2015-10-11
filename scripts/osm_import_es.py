# encoding: utf-8

"""
Copyright (c) 2012 - 2015, Ernesto Ruge
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from pymongo import MongoClient
from elasticsearch import Elasticsearch
import json
from datetime import datetime
from bson import ObjectId, DBRef
from webapp import app, mongo, es, db

class MyEncoder(json.JSONEncoder):
  def default(self, obj):
    if isinstance(obj, datetime.datetime):
      return obj.isoformat()
    elif isinstance(obj, ObjectId):
      return str(obj)
    elif isinstance(obj, DBRef):
      return {
        'collection': obj.collection,
        '_id': obj.id
      }
    return obj.__dict__


def run():
  now = datetime.utcnow()
  new_index = app.config['es_location_index'] + '-' + now.strftime('%Y%m%d-%H%M')
  try:
    es.indices.delete_index(new_index)
  except:
    pass
  
  bodies = db.get_body()
  new_bodies = {}
  for body in bodies:
    new_bodies[str(body['_id'])] = body
  bodies = new_bodies
  
  index_init = {
    'settings': {
      'index': {
        'analysis': {
          'analyzer': {
            'my_simple_german_analyzer': {
              'type': 'custom',
              'tokenizer': 'standard',
              'filter': ['standard', 'lowercase', 'my_synonym', 'my_stop']
            }
          },
          'filter': {
            'my_synonym': {
              'type': 'synonym',
              'synonyms_path': app.config['synonyms_path']
            },
            'my_stop': {
              'type': 'stop',
              'stopwords_path': app.config['stopwords_path']
            }
          }
        }
      }
    },
    'mappings': {
      'street': {
        '_source': {'enabled': True},
        '_all': {'enabled': True},
        'properties': {
          'bodyId': {
            'store': True,
            'type': 'string',
            'index': 'not_analyzed'
          },
          'bodyName': {
            'store': True,
            'type': 'string',
            'index': 'analyzed',
            'analyzer': 'my_simple_german_analyzer'
          },
          'name': {
            'store': True,
            'type': 'string',
            'index': 'analyzed',
            'analyzer': 'my_simple_german_analyzer'
          },
          'postalcode': {
            'store': True,
            'type': 'string',
            'index': 'analyzed',
            'analyzer': 'my_simple_german_analyzer'
          },
          'point': {
            'store': True,
            'type': 'geo_point'
          },
          'points': {
            'store': True,
            'type': 'geo_point'
          }
        }
      }
    }
  }
  print "Creating index %s" % new_index
  es.indices.create(index=new_index, ignore=400, body=index_init)
  
  streets = {}
  for location in mongo.db.locations.find({}):
    if 'name' in location:
      if location['name'] not in streets:
        streets[location['name']] = {}
      if 'postalcode' in location:
        current_postalcode = location['postalcode']
      else:
        current_postalcode = 'misc'
      if current_postalcode not in streets[location['name']]:
        streets[location['name']][current_postalcode] = {
          'name': location['name'],
          'bodyId': str(location['body'].id),
          'bodyName': bodies[str(location['body'].id)]['name'],
          'points': []
        }
        if current_postalcode != 'misc':
          streets[location['name']][current_postalcode]['postalcode'] = current_postalcode
      for node in location['nodes']:
        if node['location']['type'] == 'Point':
          streets[location['name']][current_postalcode]['points'].append(node['location']['coordinates'])
        else:
          print "unknown node type: %s" % node['location']['type']
    else:
      print "node without name found"
  
  for street_plz_key, street_plz in streets.iteritems():
    for street_key, street in street_plz.iteritems():
      street['point'] = street['points'][0]
      es.index(index=new_index,
               doc_type='street',
               body=street)
  
  # Setze nach dem Indexieren Alias auf neuen Index
  # z.B. 'location-20130414-1200' -> 'location-latest'
  latest_name = app.config['es_location_index'] + '-latest'
  latest_before = es.indices.get_alias(latest_name)
  alias_update = []
  for single_before in latest_before:
    alias_update.append({
                          'remove': {
                            'index': single_before,
                            'alias': latest_name
                          }
                        })
  alias_update.append({
                        'add': {
                          'index': new_index,
                          'alias': latest_name
                        }
                      })
  print "Aliasing index %s to '%s'" % (new_index, latest_name)
  es.indices.update_aliases({ 'actions': alias_update })
  index_before = es.indices.get('%s*' % app.config['es_location_index'])
  for single_index in index_before:
    if new_index != single_index:
      print "Deleting index %s" % single_index
      es.indices.delete(single_index)