# encoding: utf-8

"""
Copyright (c) 2012 - 2015, Marian Steinbach, Ernesto Ruge
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys
sys.path.append('./')

import config as sysconfig
import os
import argparse
from datetime import datetime
from pymongo import MongoClient
from elasticsearch import Elasticsearch
import json
from bson import ObjectId, DBRef


def get_config(db):
  """
  Returns Config JSON
  """
  config = db.config.find_one()
  if '_id' in config:
    del config['_id']
  return config

def merge_dict(x, y):
  merged = dict(x,**y)
  xkeys = x.keys()
  for key in xkeys:
    if type(x[key]) is types.DictType and y.has_key(key):
      merged[key] = merge_dict(x[key],y[key])
  return merged

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


def index_papers(config, index):
  """
  Import alle Einträge aus paper in den Index mit dem gegebenen Namen.
  """
  for paper in db.paper.find({}, {'_id': 1}):
    index_paper(config, index, paper['_id'])


def index_paper(config, index, paper_id):
  paper = db.paper.find_one(paper_id)
  text_all = []
  # Body dereferenzieren
  paper['body'] = db.dereference(paper['body'])
  # Zugehörige files sammeln
  files = []
  if 'mainFile' in paper:
    files.append(db.dereference(paper['mainFile']))
  if 'auxiliaryFile' in paper:
    for n in range(len(paper['auxiliaryFile'])):
      files.append(db.dereference(paper['auxiliaryFile'][n]))
  if 'invitation' in paper:
    files.append(db.dereference(paper['invitation']))
  # Ergebnis-Dict erstellen
  result = {
    '_id': str(paper['_id']),
    'file': [],
    'bodyId': str(paper['body']['_id']),
    'bodyName': paper['body']['name']
  }
  if 'publishedDate' in paper:
    result['publishedDate'] = paper['publishedDate']
  if 'modified' in paper:
    result['modified'] = paper['modified']
  if 'originalId' in paper:
    result['originalId'] = paper['originalId']
  if 'name' in paper:
    result['name'] = paper['name']
    text_all.append(paper['name'])
  if 'paperType' in paper:
    result['paperType'] = paper['paperType']
  for file in files:
    result_file = {
      'id': str(file['_id'])
    }
    if 'fulltext' in file:
      result_file['fulltext'] = file['fulltext']
      text_all.append(file['fulltext'])
    if 'name' in file:
      result_file['name'] = file['name']
      text_all.append(file['name'])
    result['file'].append(result_file)
  
  result['text_all'] = ' '.join(text_all)
  es.index(index=index,
           doc_type='paper',
           id=str(paper_id),
           body=result)

def index_streets(config, index):
  """
  Import alle Einträge aus paper in den Index mit dem gegebenen Namen.
  """
  for street in db.locations.find({}, {'_id': 1}):
    index_street(config, index, paper['_id'])


def index_street():
  # Ergebnis-Dict erstellen
  result = {
    '_id': str(street['_id'])
  }
  es.index(index=index,
           doc_type='street',
           id=str(street_id),
           body=result)



if __name__ == '__main__':
  parser = argparse.ArgumentParser(
    description='Generate Fulltext for given City Conf File')
  options = parser.parse_args()
  connection = MongoClient(sysconfig.MONGO_HOST, sysconfig.MONGO_PORT)
  db = connection[sysconfig.MONGO_DBNAME]
  config = get_config(db)
  host = sysconfig.ES_HOST + ':' + str(sysconfig.ES_PORT)
  es = Elasticsearch([sysconfig.ES_HOST+':'+str(sysconfig.ES_PORT)], timeout=300)

  now = datetime.utcnow()
  new_index = config['es_paper_index'] + '-' + now.strftime('%Y%m%d-%H%M')
  try:
    es.indices.delete_index(new_index)
  except:
    pass

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
              'synonyms_path': config['synonyms_path']
            },
            'my_stop': {
              'type': 'stop',
              'stopwords_path': config['stopwords_path']
            }
          }
        }
      }
    },
    'mappings': {
      'paper': {
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
            'index': 'not_analyzed'
          },
          'file': {
            'type': 'nested',
            'include_in_parent': True, 
            'properties': {
              'id': {
                'store': True,
                'type': 'string',
                'index': 'analyzed'
              },
              'name': {
                'store': True,
                'type': 'string',
                'index': 'analyzed',
                'analyzer': 'my_simple_german_analyzer'
              },
              'fulltext': {
                'store': True,
                'type': 'string',
                'index': 'analyzed',
                'analyzer': 'my_simple_german_analyzer'
              },
            }
          },
          'publishedDate': {
            'store': True,
            'type': 'date'
          },
          'originalId': {
            'store': False,
            'type': 'string',
            'index': 'not_analyzed'
          },
          'originalUrl': {
            'store': False,
            'type': 'string',
            'index': 'not_analyzed'
          },
          'text_all': {
            'store': True,
            'type': 'string',
            'index': 'analyzed'
          },
          'name': {
            'store': True,
            'type': 'string',
            'index': 'analyzed',
            'analyzer': 'my_simple_german_analyzer'
          },
          'paperType': {
            'store': True,
            'type': 'string',
            'index': 'not_analyzed'
          }
        }
      }
    }
  }
  print "Creating index %s" % new_index
  es.indices.create(index=new_index, ignore=400, body=index_init)
  
  index_papers(config, new_index)
  # Setze nach dem Indexieren Alias auf neuen Index
  # z.B. 'paper-20130414-1200' -> 'paper-latest'
  latest_name = config['es_paper_index'] + '-latest'
  latest_before = es.indices.get_alias(latest_name).keys()
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
  index_before = es.indices.get('%s*' % config['es_paper_index'])
  for single_index in index_before:
    if new_index != single_index:
      print "Deleting index %s" % single_index
      es.indices.delete(single_index)
