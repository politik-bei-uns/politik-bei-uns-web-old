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

import datetime
import email.utils
import calendar
import json
import bson
import re
import urllib
import urllib2
import sys
from flask import request
from collections import OrderedDict
import HTMLParser

from webapp import app, mongo

def verify_created_modified():
  result = []
  collections = ['body', 'organization', 'person', 'membership', 'meeting', 'consultation', 'agendaitem', 'paper', 'file', 'region']
  for collection in collections:
    print '########## now working at %s ##########' % collection
    mongo_collection = getattr(mongo.db, collection)
    for item in mongo_collection.find({},{'_id':1,'lastModified':1,'modified':1,'created':1}):
      state = ['ID: %s' % item['_id']]
      # modified
      if 'modified' in item:
        state.append('modified found')
      else:
        if 'lastModified' in item:
          state.append('modified insertet with lastModified')
          mongo_collection.update({'_id': item['_id']}, {'$set': {'modified': item['lastModified']}})
        else:
          state.append('modified insertet with datetime')
          mongo_collection.update({'_id': item['_id']}, {'$set': {'modified': datetime.datetime.now()}})
      # created
      if 'created' in item:
        state.append('created found')
      else:
        if 'createdAt' in item:
          state.append('created insertet with createdAt')
          mongo_collection.update({'_id': item['_id']}, {'$set': {'created': item['createdAt']}})
        elif 'modified' in item:
          state.append('created insertet with modified')
          mongo_collection.update({'_id': item['_id']}, {'$set': {'created': item['modified']}})
        elif 'lastModified' in item:
          state.append('created insertet with lastModified')
          mongo_collection.update({'_id': item['_id']}, {'$set': {'created': item['lastModified']}})
        else:
          state.append('created insertet with datetime')
          mongo_collection.update({'_id': item['_id']}, {'$set': {'created': datetime.datetime.now()}})
      # lastModified
      if 'lastModified' in item:
        state.append('lastModified deleted')
        mongo_collection.update({'_id': item['_id']}, {'$unset': {'lastModified':1}})
      else:
        state.append('no lastModified found')
      # createdAt
      if 'createdAt' in item:
        state.append('createdAt deleted')
        mongo_collection.update({'_id': item['_id']}, {'$unset': {'createdAt':1}})
      else:
        state.append('no createdAt found')
      print ', '.join(state)

def rfc1123date(value):
  """
  Gibt ein Datum (datetime) im HTTP Head-tauglichen Format (RFC 1123) zurück
  """
  tpl = value.timetuple()
  stamp = calendar.timegm(tpl)
  return email.utils.formatdate(timeval=stamp, localtime=False, usegmt=True)


def parse_rfc1123date(string):
  return datetime.datetime(*email.utils.parsedate(string)[:6])


def expires_date(hours):
  """Date commonly used for Expires response header"""
  dt = datetime.datetime.now() + datetime.timedelta(hours=hours)
  return rfc1123date(dt)


def cache_max_age(hours):
  """String commonly used for Cache-Control response headers"""
  seconds = hours * 60 * 60
  return 'max-age=' + str(seconds)


def attachment_url(attachment_id, filename=None, extension=None):
  if filename is not None:
    extension = filename.split('.')[-1]
  return app.config['ATTACHMENT_DOWNLOAD_URL'] % (attachment_id, extension)


def thumbnail_url(attachment_id, size, page):
  attachment_id = str(attachment_id)
  url = app.config['THUMBS_URL']
  url += attachment_id[-1] + '/' + attachment_id[-2] + '/' + attachment_id
  url += '/' + str(size)
  url += '/' + str(page) + '.' + app.config['THUMBNAILS_SUFFIX']
  return url


def submission_url(identifier):
  url = app.config['BASE_URL']
  url += 'dokumente/' + urllib.quote_plus(identifier) + '/'
  return url


def geocode(location_string, region):
  """
  Löst eine Straßen- und optional PLZ-Angabe zu einer Geo-Postion
  auf. Beispiel: "Straßenname (12345)"
  """
  if region != app.config['region_default']:
    location_string += ' ' + app.config['regions'][region]['name']
  address = location_string.encode('utf-8')
  
  # Filter Postalcode in Brackets from Selection
  postalre = re.compile(r'(.+), ([0-9]{5}) (.+)')
  postal_matching = re.match(postalre, address)
  postal = None
  if postal_matching is not None:
    postal = postal_matching.group(2)
  url = 'http://open.mapquestapi.com/nominatim/v1/search.php'
  params = {'format': 'json',  # json
        'q': address,
        'addressdetails': 1,
        'accept-language': 'de_DE',
        'countrycodes': 'DE'}
  request = urllib2.urlopen(url + '?' + urllib.urlencode(params))
  response = request.read()
  addresses = json.loads(response)
  addresses_out = []
  for n in range(len(addresses)):
    for key in addresses[n].keys():
      if key in ['address', 'boundingbox', 'lat', 'lon', 'osm_id']:
        continue
      del addresses[n][key]
    # skip if no road contained
    if 'road' not in addresses[n]['address']:
      continue
    # skip if not in correct county
    if 'county' not in addresses[n]['address']:
      continue
    
    # TODO: Filter for County
    #if addresses[n]['address']['county'] != app.config['GEOCODING_FILTER_COUNTY']:
    #  continue
    if postal is not None:
      if 'postcode' in addresses[n]['address'] and addresses[n]['address']['postcode'] == postal:
        addresses_out.append(addresses[n])
    else:
      addresses_out.append(addresses[n])
  return addresses_out


class MyEncoder(json.JSONEncoder):
  def default(self, obj):
    if isinstance(obj, datetime.datetime):
      return obj.isoformat()
    elif isinstance(obj, bson.ObjectId):
      return str(obj)
    elif isinstance(obj, bson.DBRef):
      return {
        'collection': obj.collection,
        '_id': obj.id
      }
    return obj.__dict__


# Some simple Jinja2 Functions
app.jinja_env.globals.update(is_dict=lambda value: type(value) == type({}) or type(value) == type(OrderedDict()))
app.jinja_env.globals.update(is_list=lambda value: type(value) == type([]))
app.jinja_env.globals.update(is_link=lambda value: value[0:7] == 'http://' or value[0:8] == 'https://' if isinstance(value, basestring) else False)
app.jinja_env.globals.update(dir=dir)

def dottify(value):
  if value:
    if value > 999:
      return str(value)[:-3] + '.' + str(value)[-3:]
  return value

app.jinja_env.filters['dottify'] = dottify

def utfunescape(value):
  h = HTMLParser.HTMLParser()
  return h.unescape(value)

app.jinja_env.filters['utfunescape'] = utfunescape