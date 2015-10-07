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

def get_body(body_list=False, add_prefix='', add_postfix='', search_params={}):
  result = []
  if body_list:
    for body in mongo.db.body.find(search_params,{'_id':1}):
      result.append("%s%s%s" % (add_prefix, body['_id'], add_postfix))
  else:
    for body in mongo.db.body.find(search_params):
      result.append(body)
  return result

def get_legislativeTerm(legislativeTerm_list=False, add_prefix='', add_postfix='', search_params={}, deref={}):
  result = []
  if legislativeTerm_list:
    for legislativeTerm in mongo.db.legislativeTerm.find(search_params,{'_id':1}):
      result.append(add_prefix + str(legislativeTerm['_id']) + add_postfix)
  else:
    for legislativeTerm in mongo.db.legislativeTerm.find(search_params):
      result.append(legislativeTerm)
  return dereference_result_items(result, deref, add_prefix, add_postfix)


def get_organization(organization_list=False, add_prefix='', add_postfix='', search_params={}, deref={}):
  result = []
  #search_params = dereference_search_params(search_params, [
  #  {'from': 'body_id', 'to': 'body', 'field': '_id', 'get_function': get_body},
  #  {'from': 'person_id', 'to': 'person', 'field': '_id', 'get_function': get_person}
  #])
  if organization_list:
    for organization in mongo.db.organization.find(search_params,{'_id':1}):
      result.append(add_prefix + str(organization['_id']) + add_postfix)
  else:
    for organization in mongo.db.organization.find(search_params):
      result.append(organization)
  return dereference_result_items(result, deref, add_prefix, add_postfix)

def get_membership(membership_list=False, add_prefix='', add_postfix='', search_params={}, deref={}):
  result = []
  if membership_list:
    for membership in mongo.db.membership.find(search_params,{'_id':1}):
      result.append(add_prefix + str(membership['_id']) + add_postfix)
  else:
    for membership in mongo.db.membership.find(search_params):
      result.append(membership)
  return dereference_result_items(result, deref, add_prefix, add_postfix)

def get_person(person_list=False, add_prefix='', add_postfix='', search_params={}, deref={}, values={}):
  result = []
  #search_params = dereference_search_params(search_params, [
  #  {'from': 'body_slug', 'to': 'body', 'field': 'title', 'get_function': get_body},
  #  {'from': 'committee_slug', 'to': 'committee', 'field': 'slug', 'get_function': get_committee}
  #])
  if person_list:
    for person in mongo.db.person.find(search_params,{'_id':1}):
      result.append(add_prefix + str(person['_id']) + add_postfix)
  else:
    if len(values):
      for person in mongo.db.person.find(search_params, values):
        result.append(person)
    else:
      for person in mongo.db.person.find(search_params):
        result.append(person)
  return dereference_result_items(result, deref, add_prefix, add_postfix)

def get_meeting(meeting_list=False, add_prefix='', add_postfix='', search_params={}, deref={}, values={}):
  result = []
  #search_params = dereference_search_params(search_params, [
  #  {'from': 'body_slug', 'to': 'body', 'field': 'title', 'get_function': get_body},
  #  {'from': 'committee_slug', 'to': 'committee', 'field': 'slug', 'get_function': get_committee},
  #  {'from': 'agendaitem_slug', 'to': 'agendaitem', 'field': 'slug', 'get_function': get_agendaitem},
  #  {'from': 'document_slug', 'to': 'document', 'field': 'slug', 'get_function': get_document}
  #])
  if meeting_list:
    for meeting in mongo.db.meeting.find(search_params,{'_id':1}):
      result.append(add_prefix + str(meeting['_id']) + add_postfix)
  else:
    if len(values):
      for meeting in mongo.db.meeting.find(search_params, values):
        result.append(meeting)
    else:
      for meeting in mongo.db.meeting.find(search_params):
        result.append(meeting)
  return dereference_result_items(result, deref, add_prefix, add_postfix)

def get_agendaItem(agendaItem_list=False, add_prefix='', add_postfix='', search_params={}, deref={}, values={}):
  result = []
  #search_params = dereference_search_params(search_params, [
  #  {'from': 'body_slug', 'to': 'body', 'field': 'title', 'get_function': get_body},
  #  {'from': 'paper_slug', 'to': 'paper', 'field': 'slug', 'get_function': get_paper}
  #])
  if agendaItem_list:
    for agendaitem in mongo.db.agendaitem.find(search_params,{'_id':1}):
      result.append(add_prefix + str(agendaitem['_id']) + add_postfix)
  else:
    if len(values):
      for agendaitem in mongo.db.agendaitem.find(search_params, values):
        result.append(agendaitem)
    else:
      for agendaitem in mongo.db.agendaitem.find(search_params):
        result.append(agendaitem)
  return dereference_result_items(result, deref, add_prefix, add_postfix)

def get_consultation(consultation_list=False, add_prefix='', add_postfix='', search_params={}, deref={}):
  result = []
  #search_params = dereference_search_params(search_params, [
  #  {'from': 'body_slug', 'to': 'body', 'field': 'title', 'get_function': get_body},
  #  {'from': 'document_slug', 'to': 'document', 'field': 'slug', 'get_function': get_document}
  #])
  if consultation_list:
    for consultation in mongo.db.consultation.find(search_params,{'_id':1}):
      result.append(add_prefix + str(consultation['_id']) + add_postfix)
  else:
    for consultation in mongo.db.consultation.find(search_params):
      result.append(consultation)
  return dereference_result_items(result, deref, add_prefix, add_postfix)

def get_paper(paper_list=False, add_prefix='', add_postfix='', search_params={}, deref={}):
  result = []
  #search_params = dereference_search_params(search_params, [
  #  {'from': 'body_slug', 'to': 'body', 'field': 'title', 'get_function': get_body},
  #  {'from': 'document_slug', 'to': 'document', 'field': 'slug', 'get_function': get_document}
  #])
  if paper_list:
    for paper in mongo.db.paper.find(search_params,{'_id':1}):
      result.append(add_prefix + str(paper['_id']) + add_postfix)
  else:
    for paper in mongo.db.paper.find(search_params):
      result.append(paper)
  return dereference_result_items(result, deref, add_prefix, add_postfix)

def get_file(file_list=False, add_prefix='', add_postfix='', search_params={}, deref={}):
  result = []
  #search_params = dereference_search_params(search_params, [
  #  {'from': 'body_slug', 'to': 'body', 'field': 'title', 'get_function': get_body}
  #])
  if file_list:
    for file in mongo.db.file.find(search_params,{'_id':1}):
      result.append(add_prefix + str(file['_id']) + add_postfix)
  else:
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
      if value in result[0]:
        if isinstance(result[0][value], DBRef):
          result[0][value] = mongo.db.dereference(result[0][value])
        else:
          for item_id in range(len(result[0][value])):
            result[0][value][item_id] = mongo.db.dereference(result[0][value][item_id])
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

def get_papers_live(search_string):
  result = es.search(
    index = app.config['es_paper_index'] + '-latest',
    doc_type = 'paper',
    fields = 'name',
    body = {
      'query': {
        'match_phrase_prefix': {
          'name': search_string
        }
      },
      'aggs': {
        'fragment': {
          'terms': {
            'field': 'name',
            'include': search_string + '.*',
            'size': 0
          }
        }
      }
    },
    size = 0
  )
  print result
  search_results = []
  if result['hits']['total']:
    for search_result in result['hits']['hits']:
      tmp_search_result = {
        'name': search_result['fields']['name'][0],
        'bodyName': search_result['fields']['bodyName'][0],
        'point': search_result['fields']['point'][0]
      }
      if 'postalcode' in location['fields']:
        tmp_search_result['postalcode'] = search_result['fields']['postalcode'][0]
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

