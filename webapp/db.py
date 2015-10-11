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

import util
import gridfs
import re
import urllib2
import datetime
import dateutil.relativedelta

from flask import abort
from bson import ObjectId, DBRef
from webapp import app, mongo, es
from flask.ext.pymongo import PyMongo
from pymongo import ASCENDING, DESCENDING

def get_config(body_uid=False):
  """
  Returns Config JSON
  """
  config = mongo.db.config.find_one({})
  if '_id' in config:
    del config['_id']
  config['regions'] = {}
  for region in mongo.db.region.find({}):
    bodies = []
    for body in region['body']:
      bodies.append(str(body.id))
    region['body'] = bodies
    region['id'] = str(region['_id'])
    del region['_id']
    config['regions'][region['id']] = region
  config['bodies'] = {}
  for body in mongo.db.body.find({}):
    config['bodies'][str(body['_id'])] = body
  return config

def merge_dict(self, x, y):
  merged = dict(x,**y)
  xkeys = x.keys()
  for key in xkeys:
    if type(x[key]) is types.DictType and y.has_key(key):
      merged[key] = merge_dict(x[key],y[key])
  return merged

def get_body(add_prefix='', add_postfix='', search_params={}, deref={}, sort=['modified', -1], limit=100):
  result = []
  for body in mongo.db.body.find(search_params).sort(sort[0], sort[1]).limit(limit):
    result.append(body)
  return dereference_result_items(result, deref, add_prefix, add_postfix)

def get_body_count(search_params={}):
  return mongo.db.body.find(search_params).count()


# legislativeTerm
def get_legislativeTerm(add_prefix='', add_postfix='', search_params={}, deref={}, sort=['modified', -1], limit=100):
  result = []
  for legislativeTerm in mongo.db.legislativeTerm.find(search_params).sort(sort[0], sort[1]).limit(limit):
    result.append(legislativeTerm)
  return dereference_result_items(result, deref, add_prefix, add_postfix)


# organization
def get_organization(add_prefix='', add_postfix='', search_params={}, deref={}, sort=['modified', -1], limit=100):
  result = []
  for organization in mongo.db.organization.find(search_params).sort(sort[0], sort[1]).limit(limit):
    result.append(organization)
  return dereference_result_items(result, deref, add_prefix, add_postfix)

def get_organization_count(search_params={}):
  return mongo.db.organization.find(search_params).count()


# membership
def get_membership(add_prefix='', add_postfix='', search_params={}, deref={}, sort=['modified', -1], limit=100):
  result = []
  for membership in mongo.db.membership.find(search_params).sort(sort[0], sort[1]).limit(limit):
    result.append(membership)
  return dereference_result_items(result, deref, add_prefix, add_postfix)


# person
def get_person(add_prefix='', add_postfix='', search_params={}, deref={}, sort=['modified', -1], limit=100):
  result = []
  for person in mongo.db.person.find(search_params).sort(sort[0], sort[1]).limit(limit):
    result.append(person)
  return dereference_result_items(result, deref, add_prefix, add_postfix)

def get_person_count(search_params={}):
  return mongo.db.person.find(search_params).count()


# meeting
def get_meeting(add_prefix='', add_postfix='', search_params={}, deref={}, sort=['modified', -1], limit=100):
  result = []
  for meeting in mongo.db.meeting.find(search_params).sort(sort[0], sort[1]).limit(limit):
    result.append(meeting)
  return dereference_result_items(result, deref, add_prefix, add_postfix)

def get_meeting_count(search_params={}):
  return mongo.db.meeting.find(search_params).count()

# agendaItem
def get_agendaItem(add_prefix='', add_postfix='', search_params={}, deref={}, sort=['modified', -1], limit=100):
  result = []
  for agendaitem in mongo.db.agendaitem.find(search_params).sort(sort[0], sort[1]).limit(limit):
    result.append(agendaitem)
  return dereference_result_items(result, deref, add_prefix, add_postfix)

# consultation
def get_consultation(add_prefix='', add_postfix='', search_params={}, deref={}, sort=['modified', -1], limit=100):
  result = []
  for consultation in mongo.db.consultation.find(search_params).sort(sort[0], sort[1]).limit(limit):
    result.append(consultation)
  return dereference_result_items(result, deref, add_prefix, add_postfix)


# paper
def get_paper(add_prefix='', add_postfix='', search_params={}, deref={}, sort=['modified', -1], limit=100):
  result = []
  for paper in mongo.db.paper.find(search_params).sort(sort[0], sort[1]).limit(limit):
    result.append(paper)
  return dereference_result_items(result, deref, add_prefix, add_postfix)

def get_paper_count(search_params={}):
  return mongo.db.paper.find(search_params).count()


# file
def get_file(add_prefix='', add_postfix='', search_params={}, deref={}):
  result = []
  for file in mongo.db.file.find(search_params):
    result.append(file)
  return dereference_result_items(result, deref, add_prefix, add_postfix)


def get_file_data(file_id):
  """Return the actual file info"""
  fs = gridfs.GridFS(mongo.db)
  return fs.get(file_id)

def dereference_search_params(search_params, to_dereference):
  for key in to_dereference:
    if key['from'] in search_params:
      if key['field'] == '_id':
        search_params[key['to']] = key['get_function'](search_params={key['field']: ObjectId(search_params[key['from']])})
      else:
        search_params[key['to']] = key['get_function'](search_params={key['field']: search_params[key['from']]})
      if len(search_params[key['to']]) == 1:
        search_params[key['to']] = DBRef(key['to'], search_params[key['to']][0]['_id'])
        del search_params[key['from']]
      elif len(search_params['body']) == 0:
        abort(404)
      else:
        abort(500)
  return search_params


# derefs is {'value': 'string', 'list_select': 'string'} or {'values': ['string1', 'string2']}
def dereference_result_items(result, deref, add_prefix, add_postfix):
  # dereference value and select them
  if 'list_select' in deref:
    if deref['value'] in result[0]:
      if isinstance(result[0][deref['value']], DBRef):
        if deref['list_select'] == '_id':
          result[0][deref['value']] = "%s%s%s" % (add_prefix, result[0][deref['value']].id, add_postfix)
        else:
          result[0][deref['value']] = "%s%s%s" % (add_prefix, mongo.db.dereference(result[0][deref['value']])[deref['list_select']], add_postfix)
      else:
        for item_id in range(len(result[0][deref['value']])):
          if deref['list_select'] == '_id':
            result[0][deref['value']][item_id] = "%s%s%s" % (add_prefix, result[0][deref['value']][item_id].id, add_postfix)
          else:
            result[0][deref['value']][item_id] = "%s%s%s" % (add_prefix, mongo.db.dereference(result[0][deref['value']][item_id])[deref['list_select']], add_postfix)
      return result[0][deref['value']]
    else:
      return []
  # dereference values in dict
  elif 'values' in deref:
    for value in deref['values']:
      for result_key, result_value in enumerate(result):
        if value in result[result_key]:
          if isinstance(result[result_key][value], DBRef):
            result[result_key][value] = mongo.db.dereference(result[result_key][value])
          else:
            for item_id in range(len(result[result_key][value])):
              result[result_key][value][item_id] = mongo.db.dereference(result[result_key][value][item_id])
    return result
  # do nothing
  else:
    return result


### Queries over all collections ###

def get_all_new():
  result = []
  for item in mongo.db.body.find({},{'_id':1,'created':1}).sort('created', PyMongo.DESCENDING):
    result.append({
      'id': "%s/body/%s" % (app.config['api_url'], item['_id']),
      'type': "http://oparl.org/schema/1.0/Body",
      'created': item['created'].isoformat()
    })
  #TODO: All Other Stuff
  return []


### Elasticsearch-Based ###


def query_paper(region=None, q='', fq=None, sort='score desc', start=0, papers_per_page=10, facets=None):
  (sort_field, sort_order) = sort.split(':')
  if sort_field == 'score':
    sort_field = '_score'
  sort = {sort_field: {'order': sort_order}}
  rest = True
  x = 0
  result = []
  while rest:
    y = fq.find(":", x)
    if y == -1:
      break
    temp = fq[x:y]
    x = y + 1
    if fq[x:x+5] == "&#34;":
      y = fq.find("&#34;", x+5)
      if y == -1:
        break
      result.append((temp, fq[x+5:y]))
      x = y + 6
      if x > len(fq):
        break
    else:
      y = fq.find(";", x)
      if y == -1:
        result.append((temp, fq[x:len(fq)]))
        break
      else:
        result.append((temp, fq[x:y]))
        x = y + 1
  facet_terms = []
  for sfq in result:
    if sfq[0] == 'publishedDate':
      (year, month) = sfq[1].split('-')
      date_start = datetime.datetime(int(year), int(month), 1)
      date_end = date_start + dateutil.relativedelta.relativedelta(months=+1,seconds=-1)
      facet_terms.append({
        'range': {
          'publishedDate': {
            'gt': date_start.isoformat('T'),
            'lt': date_end.isoformat('T')
          }
        }
      })
    else:
      facet_terms.append({
        'term': {
          sfq[0]: sfq[1]
        }
      })
  if region:
    facet_terms.append({
      'terms': {
        'bodyId': app.config['regions'][region]['body'],
        'minimum_should_match': 1
      }
    })
  
  # Let's see if there are some " "s in our search string
  matches = re.findall("&#34;(.*?)&#34;", q, re.DOTALL)
  match_query = []
  for match in matches:
    if match.strip():
      match_query.append({
        'multi_match': {
          'fields': ['file.fulltext', 'file.name', 'name'],
          'type': 'phrase',
          'query': match.strip()
        }
      })
    q = q.replace("&#34;" + match + "&#34;", "")
  q = q.replace("&#34;", "").strip()
  if q:
    simple_query = [{
      'query_string': {
        'fields': ['file.fulltext', 'file.name', 'name'],
        'query': q,
        'default_operator': 'and'
      }
    }]
  else:
    simple_query = []
  
  query = {
    'query': {
      'bool': {
        'must': simple_query + match_query + facet_terms
      }
    },
    'highlight': {
      'pre_tags' : ['<strong>'],
      'post_tags' : ['</strong>'],
      'fields': {
        'file.fulltext': {
          'fragment_size': 200,
          'number_of_fragments': 1
        }
      }
    },
    'aggs': {
      'publishedDate': {
        'date_histogram': {
          'field': 'publishedDate',
          'interval': 'month'
        }
      },
      'paperType': {
        'terms': {
          'field': 'paperType'
        }
      },
      'bodyName': {
        'terms': {
          'field': 'bodyName'
        }
      }
    },
  }

  result = es.search(
    index = app.config['es_paper_index'] + '-latest',
    doc_type = 'paper',
    fields = 'name,paperType,publishedDate,bodyId,bodyName,externalId,file.fulltext',
    body = query,
    from_ = start,
    size = 10,
    sort = sort_field + ':' + sort_order
  )
  
  ret = {
    'numhits': result['hits']['total'],
    'maxscore': result['hits']['max_score'],
    'result': [],
    'facets': {}
  }
  for r in result['hits']['hits']:
    ret['result'].append({
      'id': r['_id'],
      'score': r['_score'],
      'bodyId': r['fields']['bodyId'][0],
      'bodyName': r['fields']['bodyName'][0],
      'name': r['fields']['name'][0] if 'name' in r['fields'] else '',
      'paperType': r['fields']['paperType'][0] if 'paperType' in r['fields'] else '',
      'publishedDate': r['fields']['publishedDate'][0] if 'publishedDate' in r['fields'] else '',
      'fileFulltext': r['highlight']['file.fulltext'][0].strip() if 'highlight' in r else None
    })
  if result['hits']['max_score'] is not None:
    ret['maxscore'] = result['hits']['max_score']
  for key in result['aggregations']:
    ret['facets'][key] = {}
    if key == 'publishedDate':
      for subval in result['aggregations'][key]['buckets']:
        ret['facets'][key][datetime.datetime.fromtimestamp(int(subval['key'])/1000).strftime('%Y-%m')] = subval['doc_count']
    if key in ['paperType', 'bodyName']:
      for subval in result['aggregations'][key]['buckets']:
        ret['facets'][key][subval['key']] = subval['doc_count']
  return ret


def query_paper_num(region_id, q):
  result = es.search(
    index = app.config['es_paper_index'] + '-latest',
    doc_type = 'paper',
    fields = 'name,publishedDate',
    body = {
      'query': {
        'bool': {
          'must': [
            {
              'multi_match': {
                'fields': ['file.fulltext', 'file.name', 'name'],
                'type': 'phrase',
                'query': q
              }
            },
            {
              'terms': {
                'bodyId': app.config['regions'][region_id]['body'],
                'minimum_should_match': 1
              }
            }
          ]
        }
      }
    },
    size = 1,
    sort = 'publishedDate:desc'
  )
  if result['hits']['total']:
    return {
      'num': result['hits']['total'],
      'name': result['hits']['hits'][0]['fields']['name'][0],
      'publishedDate': result['hits']['hits'][0]['fields']['publishedDate'][0] if 'publishedDate' in result['hits']['hits'][0]['fields'] else None
    }
  else:
    return {
      'num': result['hits']['total']
    }

def get_papers_live(search_string, region_id):
  search_string = search_string.split()
  if not len(search_string):
    return []
  search_string_to_complete = search_string[-1]
  
  query_parts = []
  
  query_parts.append({ 
    'match_phrase_prefix': {
      'text_all': search_string_to_complete
    }
  })
  
  query_parts.append({
    'terms': {
      'bodyId': app.config['regions'][region_id]['body'],
      'minimum_should_match': 1
    }
  })

  if len(search_string[0:-1]):
    query_parts.append({
      'query_string': {
        'fields': ['text_all'],
        'query': " ".join(search_string[0:-1]),
        'default_operator': 'and'
      }
    })

  print query_parts
  result = es.search(
    index = app.config['es_paper_index'] + '-latest',
    doc_type = 'paper',
    fields = 'name',
    body = {
      'query': {
        'bool': {
          'must': query_parts
        }
      },
      'aggs': {
        'fragment': {
          'terms': {
            'field': 'text_all',
            'include': {
              'pattern': search_string_to_complete + '.*',
              'flags': 'CANON_EQ|CASE_INSENSITIVE'
            },
            'size': 10
          }
        }
      }
    },
    size = 0
  )
  
  search_results = []
  prefix = ""
  if len(search_string[0:-1]):
    prefix = " ".join(search_string[0:-1]) + " "
  for search_result in result['aggregations']['fragment']['buckets']:
    tmp_search_result = {
      'name': prefix + search_result['key'].capitalize(),
      'count' : search_result['doc_count']
    }
    search_results.append(tmp_search_result)
  return search_results


def get_locations_by_name(location_string, region_id):
  """
  Liefert Location-Einträge für einen Namen zurück.
  """
  query_parts = []
  for location_string in location_string.replace(',', '').split():
    query_parts.append({
              'multi_match': {
                'fields': ['name', 'bodyName', 'postalcode'],
                'type': 'phrase_prefix',
                'query': location_string
              }
            })
  query_parts.append({
    'terms': {
      'bodyId': app.config['regions'][region_id]['body'],
      'minimum_should_match': 1
    }
  })
  print query_parts
  result = es.search(
    index = app.config['es_location_index'] + '-latest',
    doc_type = 'street',
    fields = 'name,bodyName,postalcode,point',
    body = {
      'query': {
        'bool': {
          'must': query_parts
        }
      }
    },
    size = 10
  )
  
  locations = []
  if result['hits']['total']:
    for location in result['hits']['hits']:
      tmp_location = {
        'name': location['fields']['name'][0],
        'bodyName': location['fields']['bodyName'][0],
        'point': location['fields']['point'][0]
      }
      if 'postalcode' in location['fields']:
        tmp_location['postalcode'] = location['fields']['postalcode'][0]
      locations.append(tmp_location)
  return locations


def get_locations(lon, lat, radius=1000):
  """
  Liefert Location-Einträge im Umkreis eines Punkts zurück
  """
  if type(lon) != float:
    lon = float(lon)
  if type(lat) != float:
    lat = float(lat)
  if type(radius) != int:
    radius = int(radius)
  earth_radius = 6371000.0
  bodies = []
#  for single_body_id, single_body in app.config['bodies'].iteritems():
#    bodies.append(DBRef('body', single_body['_id']))
  res = mongo.db.locations.aggregate([
    {
      '$geoNear': {
        'near': [lon, lat],
        'distanceField': 'distance',
        'distanceMultiplier': earth_radius,
        'maxDistance': (float(radius) / earth_radius),
        'spherical': True
      }
    } #,
#    {
#      'body':
#        {
#          '$in': bodies
#        }
#    }
  ])
  streets = []
  for street in res['result']:
    street['distance'] = int(round(street['distance']))
    streets.append(street)
  return streets

def get_responses():
  cursor = mongo.db.responses.find()
  responses = []
  for response in cursor:
    responses.append(response)
  return responses

def add_response(response):
  mongo.db.responses.insert(response)
  return True

