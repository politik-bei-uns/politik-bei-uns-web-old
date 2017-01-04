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

import os
import json
import util
import db
import datetime
import time
import sys

from flask import Flask
from flask import abort
from flask import render_template
from flask import make_response
from flask import request
from flask import session
from flask import redirect
from flask import Response
from collections import OrderedDict
from bson import ObjectId, DBRef

import werkzeug

from webapp import app

####################################################
# system
####################################################

@app.route('/oparl')
def oparl_general():
  return oparl_basic(lambda params: {
    "id": "https://1-0.oparl.politik-bei-uns.de/oparl",
    "type": "https://schema.oparl.org/1.0/System",
    "oparlVersion": "http://oparl.org/specs/1.0/",
    "otherOparlVersions": [],
    "name": "OKF-DE OParl Service",
    "body": "%s/oparl/body%s" % (app.config['api_url'], generate_postfix(params)),
    "contactEmail": "kontakt@politik-bei-uns.de",
    "contactName": "Ernesto Ruge, Open Knowledge Foundation Deutschland e.V.",
    "website": "http://politik-bei-uns.de/",
    "vendor": "http://politik-bei-uns.de/",
    "product": "http://politik-bei-uns.de/",
    "created": "2015-01-01T00:00:00+01:00",
    "modified": "2015-01-01T00:00:00+01:00",
    "web": "https://politik-bei-uns.de/"
  })

####################################################
# body
####################################################

# body list
@app.route('/oparl/body')
def oparl_bodies():
  return oparl_basic(oparl_bodies_data)


def oparl_bodies_data(params):
  return db.get_body(add_prefix = "%s/oparl/body/" % app.config['api_url'],
                     add_postfix=generate_postfix(params))


def oparl_bodies_data(params):
  search_params = {}
  if 'q' in params:
    search_params['modified'] = { '$lt': datetime.datetime.strptime(params['q'].split(':<')[1], "%Y-%m-%dT%H:%M:%S.%f") }

  data = db.get_body(search_params = search_params, limit=app.config['oparl_items_per_page'])
  result_count = db.get_body_count(search_params=search_params)
  data = {
    'data': data,
    'pagination': {
      'elementsPerPage': app.config['oparl_items_per_page']
    },
    'links': {
    }
  }
  if result_count > app.config['oparl_items_per_page']:
    data['links']['next'] = '%s/oparl/body%s' % (app.config['api_url'], generate_postfix(params, ['q=modified:<%s' % datetime.datetime.strptime(data['data'][9]['modified'], "%Y-%m-%dT%H:%M:%S.%f+00:00").strftime("%Y-%m-%dT%H:%M:%S.%f")]))
  if 'modified' in search_params:
    data['links']['first'] = '%s/oparl/body%s' % (app.config['api_url'], generate_postfix(params))

  for key, single in enumerate(data['data']):
    data['data'][key] = oparl_body_layout(data=single, params=params)
  return data


# single body
@app.route('/oparl/body/<string:body_id>')
def oparl_body(body_id):
  return oparl_basic(oparl_body_data, params={'_id': body_id})


def oparl_body_data(params):
  data = db.get_body(search_params={'_id': ObjectId(params['_id'])})
  if len(data) == 1:
    return oparl_body_layout(data=data[0], params=params)
  elif len(data) == 0:
    abort(404)


def oparl_body_layout(data, params):
  # default values
  data['id'] = "%s/oparl/body/%s%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['type'] = 'https://schema.oparl.org/1.0/Body'
  data['created'] = datetime.datetime.strptime(data['created'], "%Y-%m-%dT%H:%M:%S.%f+00:00").strftime("%Y-%m-%dT%H:%M:%S+01:00")
  data['modified'] = datetime.datetime.strptime(data['modified'], "%Y-%m-%dT%H:%M:%S.%f+00:00").strftime("%Y-%m-%dT%H:%M:%S+01:00")

  # additional transformations
  data['system'] = "%s/oparl%s" % (app.config['api_url'], generate_postfix(params))
  data['organization'] = "%s/oparl/body/%s/organization%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['person'] = "%s/oparl/body/%s/person%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['meeting'] = "%s/oparl/body/%s/meeting%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['paper'] = "%s/oparl/body/%s/paper%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['legislativeTerm'] = []

  # delete stuff
  del data['config']
  del data['_id']
  return data


# body organization list
@app.route('/oparl/body/<string:body_id>/organization')
def oparl_body_organization(body_id):
  return oparl_basic(oparl_body_organization_data,
                     params={'body_id':body_id})


def oparl_body_organization_data(params):
  search_params = oparl_generate_list_search_params(params)
  data = db.get_organization(search_params = search_params, limit=app.config['oparl_items_per_page'])
  data = oparl_generate_list_items(params=params,
                                   search_params=search_params,
                                   result_count=db.get_organization_count(search_params=search_params),
                                   data=data,
                                   type='organization')
  for key, single in enumerate(data['data']):
    data['data'][key] = oparl_organization_layout(data=single, params=params)
  return data


# body person list
@app.route('/oparl/body/<string:body_id>/person')
def oparl_body_person(body_id):
  return oparl_basic(oparl_body_person_data,
                     params={'body_id': body_id})


def oparl_body_person_data(params):
  search_params = oparl_generate_list_search_params(params)
  data = db.get_person(search_params = search_params,
                       limit=app.config['oparl_items_per_page'],
                       deref={'values': ['membership']})
  data = oparl_generate_list_items(params=params,
                                   search_params=search_params,
                                   result_count=db.get_person_count(search_params=search_params),
                                   data=data,
                                   type='person')
  for key_person, single_person in enumerate(data['data']):
    data['data'][key_person] = oparl_person_layout(data=single_person, params=params)
  return data


# body meeting list
@app.route('/oparl/body/<string:body_id>/meeting')
def oparl_body_meeting(body_id):
  return oparl_basic(oparl_body_meeting_data,
                     params = {'body_id': body_id})


def oparl_body_meeting_data(params):
  search_params = oparl_generate_list_search_params(params)
  data = db.get_meeting(search_params = search_params,
                       limit=app.config['oparl_items_per_page'],
                       deref={'values': ['invitation', 'resultsProtocol', 'agendaItem', 'auxiliaryFile']})
  data = oparl_generate_list_items(params=params,
                                   search_params=search_params,
                                   result_count=db.get_meeting_count(search_params=search_params),
                                   data=data,
                                   type='meeting')
  for key_meeting, single_meeting in enumerate(data['data']):
    data['data'][key_meeting] = oparl_meeting_layout(data=single_meeting, params=params)
  return data


# body paper list
@app.route('/oparl/body/<string:body_id>/paper')
def oparl_body_paper(body_id):
  return oparl_basic(oparl_body_paper_data,
                     params={'body_id': body_id})


def oparl_body_paper_data(params):
  search_params = oparl_generate_list_search_params(params)
  data = db.get_paper(search_params = search_params,
                       limit=app.config['oparl_items_per_page'],
                       deref={'values': ['mainFile', 'auxiliaryFile', 'consultation', 'location', 'originatorPerson', 'originatorOrganization']})
  data = oparl_generate_list_items(params=params,
                                   search_params=search_params,
                                   result_count=db.get_paper_count(search_params=search_params),
                                   data=data,
                                   type='paper')

  for key_paper, single_paper in enumerate(data['data']):
    data['data'][key_paper] = oparl_paper_layout(data=single_paper, params=params)
  return data


####################################################
# organization
####################################################

# single organization
@app.route('/oparl/organization/<string:organization_id>')
def oparl_organization(organization_id):
  return oparl_basic(oparl_organization_data, params={'_id':organization_id})


def oparl_organization_data(params):
  data = db.get_organization(search_params={'_id': ObjectId(params['_id'])})
  if len(data) == 1:
    return oparl_organization_layout(data[0], params)
  else:
    abort(404)


def oparl_organization_layout(data, params):
  # default values
  data['id'] = "%s/oparl/organization/%s%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['type'] = 'https://schema.oparl.org/1.0/Organization'
  data['body'] = "%s/oparl/body/%s%s" % (app.config['api_url'], data['body'].id, generate_postfix(params))
  data['created'] = data['created'].strftime("%Y-%m-%dT%H:%M:%S+01:00")
  data['modified'] = data['modified'].strftime("%Y-%m-%dT%H:%M:%S+01:00")

  # additional transformations
  if 'startDate' in data:
    if isinstance(data['startDate'], datetime.datetime):
      data['startDate'] = data['startDate'].strftime("%Y-%m-%d")
  if 'endDate' in data:
    if isinstance(data['endDate'], datetime.datetime):
      data['endDate'] = data['endDate'].strftime("%Y-%m-%d")

  data['membership'] = generate_backref_list(db.get_membership(search_params={'organization': DBRef('organization', ObjectId(data['_id']))}), params)
  data['meeting'] = "%s/oparl/organization/%s/meeting%s" % (app.config['api_url'], data['_id'], generate_postfix(params))

  if 'originalId' in data:
    data['PolitikBeiUns:originalId'] = data['originalId']
  if 'originalUrl' in data:
    data['PolitikBeiUns:originalUrl'] = data['originalUrl']

  # delete stuff
  del data['_id']
  if 'originalId' in data:
    del data['originalId']
  if 'originalUrl' in data:
    del data['originalUrl']
  if 'slug' in data:
    del data['slug']
  return data

@app.route('/oparl/organization/<string:organization_id>/meeting')
def oparl_organization_meeting(organization_id):
  return oparl_basic(oparl_organization_meeting_data, params={'_id':organization_id})

def oparl_organization_meeting_data(params):
  meetings = db.get_meeting(search_params={'organization': DBRef('organization', ObjectId(params['_id']))})
  result = []
  for meeting in meetings:
    result.append(oparl_meeting_layout(meeting, params))
  return result

####################################################
# membership
####################################################

# single membership
@app.route('/oparl/membership/<string:membership_id>')
def oparl_membership(membership_id):
  return oparl_basic(oparl_membership_data, params={'_id': membership_id})


def oparl_membership_data(params):
  data = db.get_membership(search_params={'_id': ObjectId(params['_id'])})
  if len(data) == 1:
    return oparl_membership_layout(data[0], params)
  elif len(data) == 0:
    abort(404)


def oparl_membership_layout(data, params):
  # default values
  data['id'] = "%s/oparl/membership/%s%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['type'] = 'https://schema.oparl.org/1.0/Membership'
  data['body'] = generate_single_url(params=params, type='body', id=data['body'].id)
  data['created'] = data['created'].strftime("%Y-%m-%dT%H:%M:%S+01:00")
  data['modified'] = data['modified'].strftime("%Y-%m-%dT%H:%M:%S+01:00")

  # additional transformations
  if 'startDate' in data:
    if isinstance(data['startDate'], datetime.datetime):
      data['startDate'] = data['startDate'].strftime("%Y-%m-%d")
  if 'endDate' in data:
    if isinstance(data['endDate'], datetime.datetime):
      data['endDate'] = data['endDate'].strftime("%Y-%m-%d")

  data['organization'] = "%s/oparl/organization/%s%s" % (app.config['api_url'], data['organization'].id, generate_postfix(params))
  data['person'] = "%s/oparl/person/%s%s" % (app.config['api_url'], db.get_person(search_params={'membership': DBRef('membership', ObjectId(data['_id']))})[0]['_id'], generate_postfix(params))

  if 'originalId' in data:
    data['PolitikBeiUns:originalId'] = data['originalId']
  if 'originalUrl' in data:
    data['PolitikBeiUns:originalUrl'] = data['originalUrl']

  # delete stuff
  del data['_id']
  if 'originalId' in data:
    del data['originalId']
  if 'originalUrl' in data:
    del data['originalUrl']
  if 'slug' in data:
    del data['slug']

  return data


####################################################
# person
####################################################

# single person
@app.route('/oparl/person/<string:person_id>')
def oparl_person(person_id):
  return oparl_basic(oparl_person_data, params={'_id': person_id})

def oparl_person_data(params):
  data = db.get_person(search_params={'_id': ObjectId(params['_id'])},
                       deref={'values': ['membership']})
  if len(data) == 1:
    return oparl_person_layout(data[0], params)
  elif len(data) == 0:
    abort(404)

def oparl_person_layout(data, params):
  # default values
  data['id'] = "%s/oparl/person/%s%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['type'] = 'https://schema.oparl.org/1.0/Person'
  data['body'] = generate_single_url(params=params, type='body', id=data['body'].id)
  data['created'] = data['created'].strftime("%Y-%m-%dT%H:%M:%S+01:00")
  data['modified'] = data['modified'].strftime("%Y-%m-%dT%H:%M:%S+01:00")

  memberships = []
  for single_membership in data['membership']:
    memberships.append(oparl_membership_layout(single_membership, params))
  data['membership'] = memberships

  if 'originalId' in data:
    data['PolitikBeiUns:originalId'] = data['originalId']
  if 'originalUrl' in data:
    data['PolitikBeiUns:originalUrl'] = data['originalUrl']

  # delete stuff
  del data['_id']
  if 'originalId' in data:
    del data['originalId']
  if 'originalUrl' in data:
    del data['originalUrl']
  if 'slug' in data:
    del data['slug']

  return data


####################################################
# meeting
####################################################

# single meeting
@app.route('/oparl/meeting/<string:meeting_id>')
def oparl_meeting(meeting_id):
  return oparl_basic(oparl_meeting_data, params={'_id': meeting_id})


def oparl_meeting_data(params):
  data = db.get_meeting(search_params={'_id': ObjectId(params['_id'])},
                        deref={'values': ['invitation', 'resultsProtocol', 'agendaItem', 'auxiliaryFile']})
  if len(data) == 1:
    return oparl_meeting_layout(data[0], params)
  elif len(data) == 0:
    abort(404)


def oparl_meeting_layout(data, params):
  # default values
  data['id'] = "%s/oparl/meeting/%s%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['type'] = 'https://schema.oparl.org/1.0/Meeting'
  data['body'] = generate_single_url(params=params, type='body', id=data['body'].id)
  data['created'] = data['created'].strftime("%Y-%m-%dT%H:%M:%S+01:00")
  data['modified'] = data['modified'].strftime("%Y-%m-%dT%H:%M:%S+01:00")

  # additional transformations
  if 'start' in data:
    if isinstance(data['start'], datetime.datetime):
      data['start'] = data['start'].strftime("%Y-%m-%dT%H:%M:%S+01:00")
  if 'end' in data:
    if isinstance(data['end'], datetime.datetime):
      data['end'] = data['end'].strftime("%Y-%m-%dT%H:%M:%S+01:00")

  if 'address' in data:
    data['PolitikBeiUns:address'] = data['address']
    del data['address']

  if 'room' in data:
    data['PolitikBeiUns:room'] = data['room']
    del data['room']

  # if invitation is list -> Bug
  if 'invitation' in data:
    if isinstance(data['invitation'], list):
      # invitation is list -> Bug
      if len(data['invitation']):
        data['invitation'] = data['invitation'][0]
      else:
        del data['invitation']

  if 'invitation' in data:
    if data['invitation']:
      data['invitation'] = oparl_file_layout(data['invitation'], params)
    else:
      del data['invitation']

  if 'resultsProtocol' in data:
    if data['resultsProtocol']:
      data['resultsProtocol'] = oparl_file_layout(data['resultsProtocol'], params)
    else:
      del data['resultsProtocol']

  if 'verbatimProtocol' in data:
    if data['verbatimProtocol']:
      data['verbatimProtocol'] = oparl_file_layout(data['verbatimProtocol'], params)
    else:
      del data['verbatimProtocol']

  if 'participant' in data:
    data['membership'] = generate_backref_list(data['participant'], params)
  if 'auxiliaryFile' in data:
    auxiliaryFiles = []
    for single_auxiliaryFile in data['auxiliaryFile']:
      if single_auxiliaryFile:
        auxiliaryFiles.append(oparl_file_layout(single_auxiliaryFile, params))
    if len(auxiliaryFiles):
      data['auxiliaryFile'] = auxiliaryFiles
    else:
      del data['auxiliaryFile']

  if 'agendaItem' in data:
    agendaItems = []
    for single_agendaItem in data['agendaItem']:
      if single_agendaItem:
        agendaItems.append(oparl_agendaItem_layout(single_agendaItem, params))
    if len(agendaItems):
      data['agendaItem'] = agendaItems
    else:
      del data['agendaItem']

  if 'originalId' in data:
    data['PolitikBeiUns:originalId'] = data['originalId']
  if 'originalUrl' in data:
    data['PolitikBeiUns:originalUrl'] = data['originalUrl']


  # delete stuff
  del data['_id']
  if 'originalId' in data:
    del data['originalId']
  if 'originalUrl' in data:
    del data['originalUrl']
  if 'slug' in data:
    del data['slug']

  return data


####################################################
# agendaItem
####################################################

# single agendaItem
@app.route('/oparl/agendaItem/<string:agendaItem_id>')
def oparl_agendaItem(agendaItem_id):
  return oparl_basic(oparl_agendaItem_data, params={'_id': agendaItem_id})


def oparl_agendaItem_data(params):
  data = db.get_agendaItem(search_params={'_id': ObjectId(params['_id'])})
  if len(data) == 1:
    data = oparl_agendaItem_layout(data[0], params)
    meeting = db.get_meeting(search_params={'agendaItem': DBRef('agendaItem', ObjectId(params['_id']))})
    if len(meeting):
      data['meeting'] = "%s/oparl/meeting/%s%s" % (app.config['api_url'], meeting[0]['_id'], generate_postfix(params))
    return data
  elif len(data) == 0:
    abort(404)


def oparl_agendaItem_layout(data, params):
  # default values
  data['id'] = "%s/oparl/agendaItem/%s%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['type'] = 'https://schema.oparl.org/1.0/AgendaItem'
  data['body'] = generate_single_url(params=params, type='body', id=data['body'].id)
  data['created'] = data['created'].strftime("%Y-%m-%dT%H:%M:%S+01:00")
  data['modified'] = data['modified'].strftime("%Y-%m-%dT%H:%M:%S+01:00")

  # additional transformations
  if 'start' in data:
    if isinstance(data['start'], datetime.datetime):
      data['start'] = data['start'].strftime("%Y-%m-%dT%H:%M:%S")
  if 'end' in data:
    if isinstance(data['end'], datetime.datetime):
      data['end'] = data['end'].strftime("%Y-%m-%dT%H:%M:%S")

  if 'consultation' in data:
    data['consultation'] = "%s/oparl/consultation/%s%s" % (app.config['api_url'], data['consultation'].id, generate_postfix(params))


  if 'originalId' in data:
    data['PolitikBeiUns:originalId'] = data['originalId']
  if 'originalUrl' in data:
    data['PolitikBeiUns:originalUrl'] = data['originalUrl']

  # delete stuff
  del data['_id']
  if 'originalId' in data:
    del data['originalId']
  if 'originalUrl' in data:
    del data['originalUrl']
  if 'slug' in data:
    del data['slug']

  return data


####################################################
# consultation
####################################################

# single consultation
@app.route('/oparl/consultation/<string:consultation_id>')
def oparl_consultation(consultation_id):
  return oparl_basic(oparl_consultation_data, params={'_id': consultation_id})

def oparl_consultation_data(params):
  data = db.get_consultation(search_params={'_id': ObjectId(params['_id'])})
  if len(data) == 1:
    data = oparl_consultation_layout(data[0], params)
    agendaItem = db.get_agendaItem(search_params={'consultation': DBRef('consultation', ObjectId(params['_id']))})
    if len(agendaItem):
      data['agendaItem'] = "%s/oparl/agendaItem/%s%s" % (app.config['api_url'], agendaItem[0]['_id'], generate_postfix(params))
    return data
  elif len(data) == 0:
    abort(404)


def oparl_consultation_layout(data, params):
  # default values
  data['id'] = "%s/oparl/consultation/%s%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['type'] = 'https://schema.oparl.org/1.0/Consultation'
  data['body'] = generate_single_url(params=params, type='body', id=data['body'].id)
  data['created'] = data['created'].strftime("%Y-%m-%dT%H:%M:%S+01:00")
  data['modified'] = data['modified'].strftime("%Y-%m-%dT%H:%M:%S+01:00")

  # additional transformations
  if 'publishedDate' in data:
    if isinstance(data['publishedDate'], datetime.datetime):
      data['publishedDate'] = data['publishedDate'].strftime("%Y-%m-%d")

  if 'paper' in data:
    data['paper'] = "%s/oparl/paper/%s%s" % (app.config['api_url'], data['paper'].id, generate_postfix(params))

  if 'originalId' in data:
    data['PolitikBeiUns:originalId'] = data['originalId']
  if 'originalUrl' in data:
    data['PolitikBeiUns:originalUrl'] = data['originalUrl']

  # delete stuff
  del data['_id']
  if 'originalId' in data:
    del data['originalId']
  if 'originalUrl' in data:
    del data['originalUrl']
  if 'slug' in data:
    del data['slug']

  return data


####################################################
# paper
####################################################

# single paper
@app.route('/oparl/paper/<string:paper_id>')
def oparl_paper(paper_id):
  return oparl_basic(oparl_paper_data, params={'_id': paper_id})


def oparl_paper_data(params):
  data = db.get_paper(search_params={'_id': ObjectId(params['_id'])},
                      deref={'values': ['mainFile', 'auxiliaryFile', 'consultation', 'location', 'originatorPerson', 'originatorOrganization']})
  if len(data) == 1:
    return oparl_paper_layout(data[0], params)
  elif len(data) == 0:
    abort(404)


def oparl_paper_layout(data, params):
  # default values
  data['id'] = "%s/oparl/paper/%s%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['type'] = 'https://schema.oparl.org/1.0/Paper'
  data['body'] = generate_single_url(params=params, type='body', id=data['body'].id)
  data['created'] = data['created'].strftime("%Y-%m-%dT%H:%M:%S+01:00")
  data['modified'] = data['modified'].strftime("%Y-%m-%dT%H:%M:%S+01:00")

  # mainFile
  if 'mainFile' in data:
    if data['mainFile']:
      data['mainFile'] = oparl_file_layout(data['mainFile'], params)
    else:
      del data['mainFile']

  # auxiliaryFiles
  if 'auxiliaryFile' in data:
    auxiliaryFiles = []
    for single_auxiliaryFile in data['auxiliaryFile']:
      if single_auxiliaryFile:
        auxiliaryFiles.append(oparl_file_layout(single_auxiliaryFile, params))
    if len(auxiliaryFiles):
      data['auxiliaryFile'] = auxiliaryFiles
    else:
      del data['data']

  data['consultation'] = []
  consultations = db.get_consultation(search_params={'paper': DBRef('paper', ObjectId(data['_id']))})
  for consultation in consultations:
    data['consultation'].append(oparl_consultation_layout(consultation, params))
  if len(data['consultation']) == 0:
    del data['consultation']

  # additional transformations
  if 'publishedDate' in data:
    if isinstance(data['publishedDate'], datetime.datetime):
      data['PolitikBeiUns:publishedDate'] = data['publishedDate'].strftime("%Y-%m-%d")
    del data['publishedDate']

  # TODO for data model
  if 'georeferences' in data:
    del data['georeferences']
  if 'georeferences' in data:
    del data['georeferencesGenerated']
  if 'title' in data:
    del data['title']

  if 'originalId' in data:
    data['PolitikBeiUns:originalId'] = data['originalId']
  if 'originalUrl' in data:
    data['PolitikBeiUns:originalUrl'] = data['originalUrl']
  if 'nameShort' in data:
    data['reference'] = data['nameShort']

  # delete stuff
  del data['_id']
  if 'originalId' in data:
    del data['originalId']
  if 'originalUrl' in data:
    del data['originalUrl']
  if 'slug' in data:
    del data['slug']
  if 'nameShort' in data:
    del data['nameShort']
  if 'georeferencesGenerated' in data:
    del data['georeferencesGenerated']
  return data



####################################################
# file
####################################################

# single file
@app.route('/oparl/file/<string:file_id>')
def oparl_document(file_id):
  return oparl_basic(oparl_file_data, params={'_id': file_id})

def oparl_file_data(params):
  data = db.get_file(search_params={'_id': ObjectId(params['_id'])})
  if len(data) == 1:
    data = oparl_file_layout(data[0], params)
    # Get Backrefs for Meeting
    data['meeting'] = []
    meeting = db.get_meeting(search_params={'invitation': DBRef('file', ObjectId(params['_id']))})
    if len(meeting):
      data['meeting'].append("%s/oparl/meeting/%s%s" % (app.config['api_url'], meeting[0]['_id'], generate_postfix(params)))
    meeting = db.get_meeting(search_params={'resultsProtocol': DBRef('file', ObjectId(params['_id']))})
    if len(meeting):
      data['meeting'].append("%s/oparl/meeting/%s%s" % (app.config['api_url'], meeting[0]['_id'], generate_postfix(params)))
    meeting = db.get_meeting(search_params={'verbatimProtocol': DBRef('file', ObjectId(params['_id']))})
    if len(meeting):
      data['meeting'].append("%s/oparl/meeting/%s%s" % (app.config['api_url'], meeting[0]['_id'], generate_postfix(params)))
    meeting = db.get_meeting(search_params={'verbatimProtocol': DBRef('auxiliaryFile', ObjectId(params['_id']))})
    for single_meeting in meeting:
      data['meeting'].append("%s/oparl/meeting/%s%s" % (app.config['api_url'], single_meeting['_id'], generate_postfix(params)))
    if len(data['meeting']) == 0:
      del data['meeting']
    # Get Backrefs for AgendaItem
    data['agendaItem'] = []
    agendaItem = db.get_agendaItem(search_params={'resolutionFile': DBRef('file', ObjectId(params['_id']))})
    if len(agendaItem):
      data['agendaItem'].append("%s/oparl/agendaItem/%s%s" % (app.config['api_url'], agendaItem[0]['_id'], generate_postfix(params)))
    agendaItem = db.get_agendaItem(search_params={'auxiliaryFile': DBRef('file', ObjectId(params['_id']))})
    for single_agendaItem in agendaItem:
      data['agendaItem'].append("%s/oparl/agendaItem/%s%s" % (app.config['api_url'], single_agendaItem['_id'], generate_postfix(params)))
    if len(data['agendaItem']) == 0:
      del data['agendaItem']
    # Get Backrefs for Paper
    data['paper'] = []
    paper = db.get_agendaItem(search_params={'mainFile': DBRef('file', ObjectId(params['_id']))})
    if len(paper):
      data['paper'].append("%s/oparl/paper/%s%s" % (app.config['api_url'], paper[0]['_id'], generate_postfix(params)))
    paper = db.get_agendaItem(search_params={'auxiliaryFile': DBRef('file', ObjectId(params['_id']))})
    for single_paper in paper:
      data['paper'].append("%s/oparl/paper/%s%s" % (app.config['api_url'], single_paper['_id'], generate_postfix(params)))
    if len(data['paper']) == 0:
      del data['paper']
    return data
  elif len(data) == 0:
    abort(404)


def oparl_file_layout(data, params):
  # default values
  data['id'] = "%s/oparl/file/%s%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['type'] = 'https://schema.oparl.org/1.0/File'
  data['body'] = "%s/oparl/body/%s%s" % (app.config['api_url'], data['body'].id, generate_postfix(params))
  data['created'] = data['created'].strftime("%Y-%m-%dT%H:%M:%S+01:00")
  data['modified'] = data['modified'].strftime("%Y-%m-%dT%H:%M:%S+01:00")

  # additional transformations
  data['accessUrl'] = "%s/oparl/file/%s/access%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['downloadUrl'] = "%s/oparl/file/%s/download%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  if 'date' in data:
    if isinstance(data['date'], datetime.datetime):
      data['date'] = data['date'].strftime("%Y-%m-%d")

  # TODO: rename stuff
  if 'fulltext' in data:
    data['text'] = data['fulltext']
    del data['fulltext']
  if 'mimetype' in data:
    data['mimeType'] = data['mimetype']
    del data['mimetype']
  if 'filename' in data:
    data['fileName'] = data['filename']
    del data['filename']

  if 'originalId' in data:
    data['PolitikBeiUns:originalId'] = data['originalId']
  if 'originalUrl' in data:
    data['PolitikBeiUns:originalUrl'] = data['originalUrl']
  if 'originalDownloadPossible' in data:
    data['PolitikBeiUns:originalDownloadPossible'] = data['originalDownloadPossible']

  # delete stuff
  del data['_id']
  if 'originalId' in data:
    del data['originalId']
  if 'originalUrl' in data:
    del data['originalUrl']
  if 'originalDownloadPossible' in data:
    del data['originalDownloadPossible']
  if 'file' in data:
    del data['file']
  if 'thumbnails' in data:
    del data['thumbnails']
  if 'fulltextGenerated' in data:
    del data['fulltextGenerated']
  if 'thumbnailsGenerated' in data:
    del data['thumbnailsGenerated']
  return data


# file accessUrl
@app.route('/oparl/file/<string:file_id>/access')
def oparl_file_accessUrl(file_id):
  return oparl_basic(oparl_file_accessUrl_data, params={'file_id': file_id}, direct_output=True)

def oparl_file_accessUrl_data(params):
  file_data = db.get_file(deref={'values': ['file']},
                              search_params={'_id': ObjectId(params['file_id'])})

  if len(file_data) == 0:
    # TODO: Rendere informativere 404 Seite
    abort(404)
  file_data = file_data[0]
  # extension doesn't match file extension (avoiding arbitrary URLs)
  #proper_extension = attachment_info['filename'].split('.')[-1]
  #if proper_extension != extension:
  #    abort(404)

  # 'file' property is not set (e.g. due to depublication)
  if 'file' not in file_data:
    if 'depublication' in file_data:
      abort(410)  # Gone
    else:
      # TODO: log this as unexplicable...
      abort(500)

  # handle conditional GET
  #if 'If-Modified-Since' in request.headers:
  #  file_date = attachment_info['file']['uploadDate'].replace(tzinfo=None)
  #  request_date = util.parse_rfc1123date(request.headers['If-Modified-Since'])
  #  difference = file_date - request_date
  #  if difference < datetime.timedelta(0, 1):  # 1 second
  #    return Response(status=304)

  #if 'if-none-match' in request.headers:
  #    print "Conditional GET: If-None-Match"
  # TODO: handle ETag in request

  handler = db.get_file_data(file_data['file']['_id'])
  response = make_response(handler.read(), 200)
  response.mimetype = file_data['mimetype']
  response.headers['X-Robots-Tag'] = 'noarchive'
  response.headers['ETag'] = file_data['sha1Checksum']
  response.headers['Last-modified'] = util.rfc1123date(file_data['file']['uploadDate'])
  response.headers['Expires'] = util.expires_date(hours=(24 * 30))
  response.headers['Cache-Control'] = util.cache_max_age(hours=(24 * 30))
  return response


# file downloadUrl
@app.route('/oparl/file/<string:file_id>/download')
def oparl_file_downloadUrl(file_id):
  return oparl_basic(oparl_file_downloadUrl_data, params={'file_id': file_id}, direct_output=True)

def oparl_file_downloadUrl_data(params):
  file_data = db.get_file(deref={'values': ['file']},
                          search_params={'_id': ObjectId(params['file_id'])})

  if len(file_data) == 0:
    # TODO: Rendere informativere 404 Seite
    abort(404)
  file_data = file_data[0]

  # 'file' property is not set (e.g. due to depublication)
  if 'file' not in file_data:
    if 'depublication' in file_data:
      abort(410)  # Gone
    else:
      # TODO: log this as unexplicable...
      abort(500)

  handler = db.get_file_data(file_data['file']['_id'])
  response = make_response(handler.read(), 200)
  response.mimetype = file_data['mimetype']
  response.headers['X-Robots-Tag'] = 'noarchive'
  response.headers['ETag'] = file_data['sha1Checksum']
  response.headers['Last-modified'] = util.rfc1123date(file_data['file']['uploadDate'])
  response.headers['Expires'] = util.expires_date(hours=(24 * 30))
  response.headers['Cache-Control'] = util.cache_max_age(hours=(24 * 30))
  response.headers['Content-Disposition'] = 'attachment; filename=' + file_data['filename']
  return response


####################################################
# misc
####################################################

def oparl_basic(content_fuction, params=None, direct_output=False):
  start_time = time.time()
  jsonp_callback = request.args.get('callback', None)
  if not params:
    params = {}
  request_info = {}
  html = request.args.get('html', False)
  if html:
    request_info['html'] = 1
  extended_info = request.args.get('i')
  extended_info = extended_info == '1'
  if extended_info:
    request_info['i'] = 1
  search_query = request.args.get('q', "")
  if search_query:
    request_info['q'] = search_query
  page = request.args.get('page')
  try:
    page = int(page)
  except (ValueError, TypeError):
    page = 1
  request_info['page'] = page
  params.update(request_info)
  response = content_fuction(params)
  if direct_output:
    return response
  if extended_info:
    ret = {
      'status': 0,
      'duration': int((time.time() - start_time) * 1000),
      'request': request_info,
      'response': response
    }
  else:
    ret = response
  json_output = json.dumps(ret, cls=util.MyEncoder)#, sort_keys=True)
  if jsonp_callback is not None:
    json_output = jsonp_callback + '(' + json_output + ')'
  if html:
    return render_template('oparl.html', data=json.JSONDecoder(object_pairs_hook=OrderedDict).decode(json_output))
  else:
    response = make_response(json_output, 200)
    response.mimetype = 'application/json'
    response.headers['Expires'] = util.expires_date(hours=24)
    response.headers['Cache-Control'] = util.cache_max_age(hours=24)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


def generate_postfix(params, additional_params=[]):
  postfix = []
  if 'html' in params:
    postfix.append('html='+str(params['html']))
  if 'p' in params:
    if params['p'] > 1:
      postfix.append('p='+str(params['p']))
  if 'i' in params:
    postfix.append('i='+str(params['i']))
  postfix = postfix + additional_params
  if len(postfix):
    postfix = '?'+'&'.join(postfix)
  else:
    postfix = ''
  return(postfix)

def generate_single_url(params={}, type='', id=''):
  return "%s/oparl/%s/%s%s" % (app.config['api_url'], type, id, generate_postfix(params))

def generate_single_backref_url(params={}, get='', type='', reverse_type='', id=''):
  get = getattr(db, get)
  uid = str((get(search_params={reverse_type: DBRef(reverse_type, ObjectId(id))}, values={'_id':1}))[0]['_id'])
  return "%s/oparl/%s/%s%s" % (app.config['api_url'], type, uid, generate_postfix(params))

def generate_backref_list(data, params):
  result = []
  for item in data:
    result.append("%s/oparl/membership/%s%s" % (app.config['api_url'], item['_id'], generate_postfix(params)))
  return result

def oparl_generate_list_search_params(params):
  search_params = {'body': DBRef('body', ObjectId(params['body_id']))}
  if 'q' in params:
    search_params['modified'] = { '$lt': datetime.datetime.strptime(params['q'].split(':<')[1], "%Y-%m-%dT%H:%M:%S.%f") }
  return search_params

def oparl_generate_list_items(params, search_params, result_count, data, type):
  result = {
    'data': data,
    'pagination': {
      'elementsPerPage': app.config['oparl_items_per_page']
    },
    'links': {
    }
  }
  if result_count > app.config['oparl_items_per_page']:
    result['links']['next'] = '%s/oparl/body/%s/%s%s' % (app.config['api_url'], params['body_id'], type, generate_postfix(params, ['q=modified:<%s' % result['data'][9]['modified'].strftime("%Y-%m-%dT%H:%M:%S.%f")]))
  if 'modified' in search_params:
    result['links']['first'] = '%s/oparl/body/%s/%s%s' % (app.config['api_url'], params['body_id'], type, generate_postfix(params))
  return result

