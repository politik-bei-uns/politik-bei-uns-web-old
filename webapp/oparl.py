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

import pprint
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
    "id": "de.politik-bei-uns",
    "type": "http://oparl.org/schema/1.0/System",
    "oparlVersion": "http://oparl.org/specs/1.0/",
    "name": "OKF-DE OParl Service",
    "body": "%s/oparl/body%s" % (app.config['api_url'], generate_postfix(params)),
    "contactEmail": "kontakt@politik-bei-uns.de",
    "contactName": "Ernesto Ruge, Open Knowledge Foundation Deutschland e.V.",
    "website": "http://politik-bei-uns.de/",
    "vendor": "http://politik-bei-uns.de/",
    "product": "http://politik-bei-uns.de/"
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

  # TODO: working pagination, fails because of modified value = string insead of datetime
  data = db.get_body(search_params = search_params, limit=1000)
  result_count = db.get_body_count(search_params=search_params)
  data = {
    'items': data,
    'itemsPerPage': 1000
  }
  if result_count > 1000:
    data['nextPage'] = '%s/oparl/body%s' % (app.config['api_url'], generate_postfix(params, ['q=modified:<%s' % data['items'][9]['modified'].strftime("%Y-%m-%dT%H:%M:%S.%f")]))
  if 'modified' in search_params:
    data['firstPage'] = '%s/oparl/body%s' % (app.config['api_url'], generate_postfix(params))

  for key, single in enumerate(data['items']):
    print single
    data['items'][key] = oparl_body_layout(data=single, params=params)
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
  data['type'] = 'https://oparl.org/schema/1.0/Body'
  #data['created'] = data['created'].strftime("%Y-%m-%dT%H:%M:%S")
  #data['modified'] = data['modified'].strftime("%Y-%m-%dT%H:%M:%S")
  
  # additional transformations
  data['system'] = "%s/oparl%s" % (app.config['api_url'], generate_postfix(params))
  data['organization'] = "%s/oparl/body/%s/organization%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['person'] = "%s/oparl/body/%s/person%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['meeting'] = "%s/oparl/body/%s/meeting%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['paper'] = "%s/oparl/body/%s/paper%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  
  
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
  for key, single in enumerate(data['items']):
    data['items'][key] = oparl_organization_layout(data=single, params=params)
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
  for key_person, single_person in enumerate(data['items']):
    data['items'][key_person] = oparl_person_layout(data=single_person, params=params)
    memberships = []
    for single_membership in data['items'][key_person]['membership']:
      memberships.append(oparl_membership_layout(single_membership, params))
    data['items'][key_person]['membership'] = memberships
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
  for key_meeting, single_meeting in enumerate(data['items']):
    data['items'][key_meeting] = oparl_meeting_layout(data=single_meeting, params=params)
    # auxiliaryFiles
    if 'auxiliaryFile' in data['items'][key_meeting]:
      auxiliaryFiles = []
      for single_auxiliaryFile in data['items'][key_meeting]['auxiliaryFile']:
        if single_auxiliaryFile:
          auxiliaryFiles.append(oparl_file_layout(single_auxiliaryFile, params))
      if len(auxiliaryFiles):
        data['items'][key_meeting]['auxiliaryFile'] = auxiliaryFiles
      else:
        del data['items'][key_meeting]['auxiliaryFile']
    # agendaItems
    if 'agendaItem' in data['items'][key_meeting]:
      agendaItems = []
      for single_agendaItem in data['items'][key_meeting]['agendaItem']:
        if single_agendaItem:
          agendaItems.append(oparl_agendaItem_layout(single_agendaItem, params))
      if len(agendaItems):
        data['items'][key_meeting]['agendaItem'] = agendaItems
      else:
        del data['items'][key_meeting]['agendaItem']
    # resultsProtocol
    if 'resultsProtocol' in data['items'][key_meeting]:
      if data['items'][key_meeting]['resultsProtocol']:
        data['items'][key_meeting]['resultsProtocol'] = oparl_file_layout(data['items'][key_meeting]['resultsProtocol'], params)
      else:
        del data['items'][key_meeting]['resultsProtocol']
    # invitation
    if 'invitation' in data['items'][key_meeting]:
      if isinstance(data['items'][key_meeting]['invitation'], list):
        # TODO: invitation = list? wtf?!
        del data['items'][key_meeting]['invitation']
      else:
        if data['items'][key_meeting]['invitation']:
          data['items'][key_meeting]['invitation'] = oparl_file_layout(data['items'][key_meeting]['invitation'], params)
        else:
          del data['items'][key_meeting]['invitation']
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
                                   type='person')
  for key_paper, single_paper in enumerate(data['items']):
    data['items'][key_paper] = oparl_paper_layout(data=single_paper, params=params)
    # mainFile
    if 'mainFile' in data['items'][key_paper]:
      if data['items'][key_paper]['mainFile']:
        data['items'][key_paper]['mainFile'] = oparl_file_layout(data['items'][key_paper]['mainFile'], params)
      else:
        del data['items'][key_paper]['mainFile']
    # auxiliaryFiles
    if 'auxiliaryFile' in data['items'][key_paper]:
      auxiliaryFiles = []
      for single_auxiliaryFile in data['items'][key_paper]['auxiliaryFile']:
        if single_auxiliaryFile:
          auxiliaryFiles.append(oparl_file_layout(single_auxiliaryFile, params))
      if len(auxiliaryFiles):
        data['items'][key_paper]['auxiliaryFile'] = auxiliaryFiles
      else:
        del data['items'][key_paper]['auxiliaryFile']
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
  data['type'] = 'https://oparl.org/schema/1.0/Organization'
  data['body'] = "%s/oparl/body/%s%s" % (app.config['api_url'], data['body'].id, generate_postfix(params))
  data['created'] = data['created'].strftime("%Y-%m-%dT%H:%M:%S")
  data['modified'] = data['modified'].strftime("%Y-%m-%dT%H:%M:%S")
  
  # additional transformations
  if 'startDate' in data:
    if isinstance(data['startDate'], datetime.datetime):
      data['startDate'] = data['startDate'].strftime("%Y-%m-%d")
  if 'endDate' in data:
    if isinstance(data['endDate'], datetime.datetime):
      data['endDate'] = data['endDate'].strftime("%Y-%m-%d")
  
  # delete stuff
  del data['_id']
  return data

"""
# organization membership list
@app.route('/oparl/organization/<string:organization_id>/membership')
def oparl_rganization_membership(organization_id):
  return oparl_basic(oparl_organization_membership_data, params={'organization_id': organization_id})

def oparl_organization_membership_data(params):
  data = db.get_membership(membership_list = True,
                           search_params = {'organization': DBRef('organization', ObjectId(params['organization_id']))},
                           add_prefix = "%s/oparl/membership/" % app.config['api_url'],
                           add_postfix = generate_postfix(params))
  return data


# organization meeting list
@app.route('/oparl/organization/<string:organization_id>/meeting')
def oparl_organization_meeting(organization_id):
  return oparl_basic(oparl_organization_meeting_data, params={'organization_id': organization_id})

def oparl_organization_meeting_data(params):
  data = db.get_meeting(meeting_list = True,
                        search_params = {'organization': DBRef('organization', ObjectId(params['organization_id']))},
                        add_prefix = "%s/oparl/meeting/" % app.config['api_url'],
                        add_postfix = generate_postfix(params))
  return data
"""

####################################################
# membership
####################################################

"""
# membership list
@app.route('/oparl/membership')
def oparl_memberships():
  return oparl_basic(oparl_memberships_data)

def oparl_memberships_data(params):
  return db.get_membership(membership_list=True,
                           add_prefix = "%s/oparl/membership/" % app.config['api_url'],
                           add_postfix=generate_postfix(params))
"""

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
  data['type'] = 'http://oparl.org/schema/1.0/Membership'
  data['body'] = generate_single_url(params=params, type='body', id=data['body'].id)
  data['created'] = data['created'].strftime("%Y-%m-%dT%H:%M:%S")
  data['modified'] = data['modified'].strftime("%Y-%m-%dT%H:%M:%S")
  
  # additional transformations
  if 'startDate' in data:
    if isinstance(data['startDate'], datetime.datetime):
      data['startDate'] = data['startDate'].strftime("%Y-%m-%d")
  if 'endDate' in data:
    if isinstance(data['endDate'], datetime.datetime):
      data['endDate'] = data['endDate'].strftime("%Y-%m-%d")
  
  # delete stuff
  if 'organization' in data:
    del data['organization']
  del data['_id']
  return data
  

####################################################
# person
####################################################

# single person
@app.route('/oparl/person/<string:person_id>')
def oparl_person(person_id):
  return oparl_basic(oparl_person_data, params={'_id': person_id})

def oparl_person_data(params):
  data = db.get_person(search_params={'_id': ObjectId(params['_id'])})
  if len(data) == 1:
    data[0]['body'] = generate_single_url(params=params, type='body', id=data[0]['body'].id)
    data[0]['membership'] = generate_sublist_url(params=params, main_type='person', sublist_type='membership')
    data[0]['type'] = 'OParlPerson'
    data[0]['id'] = data[0]['_id']
    return data[0]
  elif len(data) == 0:
    abort(404)

def oparl_person_layout(data, params):
  # default values
  data['id'] = "%s/oparl/person/%s%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['type'] = 'http://oparl.org/schema/1.0/Person'
  data['body'] = generate_single_url(params=params, type='body', id=data['body'].id)
  data['created'] = data['created'].strftime("%Y-%m-%dT%H:%M:%S")
  data['modified'] = data['modified'].strftime("%Y-%m-%dT%H:%M:%S")
  
  # delete stuff
  del data['_id']
  return data


"""
# person membership list
@app.route('/oparl/person/<string:person_id>/membership')
def oparl_person_membership(person_id):
  return oparl_basic(oparl_person_membership_data, params={'person_id': person_id})

def oparl_person_membership_data(params):
  data = db.get_person(deref={'value': 'membership', 'list_select': '_id'},
                       search_params={'_id': ObjectId(params['person_id'])},
                       add_prefix = "%s/oparl/membership/" % app.config['api_url'],
                       add_postfix = generate_postfix(params))
  return data
"""

####################################################
# meeting
####################################################

# single meeting
@app.route('/oparl/meeting/<string:meeting_id>')
def oparl_meeting(meeting_id):
  return oparl_basic(oparl_meeting_data, params={'_id': meeting_id})

def oparl_meeting_data(params):
  data = db.get_meeting(search_params={'_id': ObjectId(params['_id'])})
  if len(data) == 1:
    data[0]['body'] = generate_single_url(params=params, type='body', id=data[0]['body'].id)
    data[0]['organization'] = generate_sublist_url(params=params, main_type='meeting', sublist_type='organization')
    data[0]['agendaItem'] = generate_sublist_url(params=params, main_type='meeting', sublist_type='agendaItem')
    data[0]['invitation'] = generate_sublist_url(params=params, main_type='meeting', sublist_type='invitation')
    if 'resultsProtocol' in data[0]:
      data[0]['resultsProtocol'] = generate_single_url(params=params, type='file', id=data[0]['resultsProtocol'].id)
    if 'verbatimProtocol' in data[0]:
      data[0]['verbatimProtocol'] = generate_single_url(params=params, type='file', id=data[0]['verbatimProtocol'].id)
    data[0]['auxiliaryFile'] = generate_sublist_url(params=params, main_type='meeting', sublist_type='auxiliaryFile')
    data[0]['type'] = 'OParlMeeting'
    data[0]['id'] = data[0]['_id']
    return data[0]
  elif len(data) == 0:
    abort(404)

def oparl_meeting_layout(data, params):
  # default values
  data['id'] = "%s/oparl/meeting/%s%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['type'] = 'http://oparl.org/schema/1.0/Meeting'
  data['body'] = generate_single_url(params=params, type='body', id=data['body'].id)
  data['created'] = data['created'].strftime("%Y-%m-%dT%H:%M:%S")
  data['modified'] = data['modified'].strftime("%Y-%m-%dT%H:%M:%S")
  
  # additional transformations
  if 'start' in data:
    if isinstance(data['start'], datetime.datetime):
      data['start'] = data['start'].strftime("%Y-%m-%dT%H:%M:%S")
  if 'end' in data:
    if isinstance(data['end'], datetime.datetime):
      data['end'] = data['end'].strftime("%Y-%m-%dT%H:%M:%S")
  
  # delete stuff
  del data['_id']
  return data

"""
# meeting organization list
@app.route('/oparl/meeting/<string:meeting_id>/organization')
def oparl_meeting_organization(meeting_id):
  return oparl_basic(oparl_meeting_organization_data, params={'meeting_id': meeting_id})

def oparl_meeting_organization_data(params):
  data = db.get_meeting(deref={'value': 'organization', 'list_select': '_id'},
                        search_params={'_id': ObjectId(params['meeting_id'])},
                        add_prefix = "%s/oparl/organization/" % app.config['api_url'],
                        add_postfix = generate_postfix(params))
  return data

# meeting agendaItem list
@app.route('/oparl/meeting/<string:meeting_id>/agendaItem')
def oparl_meeting_agendaItem(meeting_id):
  return oparl_basic(oparl_meeting_agendaItem_data, params={'meeting_id': meeting_id})

def oparl_meeting_agendaItem_data(params):
  data = db.get_meeting(deref={'value': 'agendaItem', 'list_select': '_id'},
                        search_params={'_id': ObjectId(params['meeting_id'])},
                        add_prefix = "%s/oparl/agendaItem/" % app.config['api_url'],
                        add_postfix = generate_postfix(params))
  return data

# meeting invitation list
@app.route('/oparl/meeting/<string:meeting_id>/invitation')
def oparl_meeting_invitation(meeting_id):
  return oparl_basic(oparl_meeting_invitation_data, params={'meeting_id': meeting_id})

def oparl_meeting_invitation_data(params):
  data = db.get_meeting(deref={'value': 'invitation', 'list_select': '_id'},
                        search_params={'_id': ObjectId(params['meeting_id'])},
                        add_prefix = "%s/oparl/file/" % app.config['api_url'],
                        add_postfix = generate_postfix(params))
  return data

# meeting auxiliaryFile list
@app.route('/oparl/meeting/<string:meeting_id>/auxiliaryFile')
def oparl_meeting_auxiliaryFile(meeting_id):
  return oparl_basic(oparl_meeting_auxiliaryFile_data, params={'meeting_id': meeting_id})

def oparl_meeting_auxiliaryFile_data(params):
  data = db.get_meeting(deref={'value': 'auxiliaryFile', 'list_select': '_id'},
                        search_params={'_id': ObjectId(params['meeting_id'])},
                        add_prefix = "%s/oparl/file/" % app.config['api_url'],
                        add_postfix = generate_postfix(params))
  return data
"""

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
    data[0]['body'] = generate_single_url(params=params, type='body', id=data[0]['body'].id)
    data[0]['meeting'] = generate_single_backref_url(params=params, get='get_meeting', type='meeting', reverse_type='agendaItem', id=params['_id'])
    if 'consultation' in data[0]:
      data[0]['consultation'] = generate_single_url(params=params, type='consultation', id=data[0]['consultation'].id)
    data[0]['type'] = 'OParlAgendaItem'
    data[0]['id'] = data[0]['_id']
    return data[0]
  elif len(data) == 0:
    abort(404)

def oparl_agendaItem_layout(data, params):
  # default values
  data['id'] = "%s/oparl/agendaItem/%s%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['type'] = 'http://oparl.org/schema/1.0/AgendaItem'
  data['body'] = generate_single_url(params=params, type='body', id=data['body'].id)
  data['created'] = data['created'].strftime("%Y-%m-%dT%H:%M:%S")
  data['modified'] = data['modified'].strftime("%Y-%m-%dT%H:%M:%S")
  
  # additional transformations
  if 'start' in data:
    if isinstance(data['start'], datetime.datetime):
      data['start'] = data['start'].strftime("%Y-%m-%dT%H:%M:%S")
  if 'end' in data:
    if isinstance(data['end'], datetime.datetime):
      data['end'] = data['end'].strftime("%Y-%m-%dT%H:%M:%S")
  
  # delete stuff
  del data['_id']
  return data

####################################################
# consultation
####################################################

"""
# consultation list
@app.route('/oparl/consultation')
def oparl_consultations():
  return oparl_basic(oparl_consultations_data)

def oparl_consultations_data(params):
  return db.get_consultation(consultation_list = True,
                           add_prefix = "%s/oparl/consultation/" % app.config['api_url'],
                           add_postfix=generate_postfix(params))
"""

# single consultation
@app.route('/oparl/consultation/<string:consultation_id>')
def oparl_consultation(consultation_id):
  return oparl_basic(oparl_consultation_data, params={'_id': consultation_id})

def oparl_consultation_data(params):
  data = db.get_consultation(search_params={'_id': ObjectId(params['_id'])})
  if len(data) == 1:
    data[0]['body'] = generate_single_url(params=params, type='body', id=data[0]['body'].id)
    data[0]['agendaItem'] = generate_single_backref_url(params=params, get='get_agendaItem', type='agendaItem', reverse_type='consultation', id=params['_id'])
    data[0]['paper'] = generate_single_url(params=params, type='paper', id=data[0]['paper'].id)
    data[0]['organization'] = generate_sublist_url(params=params, main_type='consultation', sublist_type='organization')
    data[0]['type'] = 'OParlConsultation'
    data[0]['id'] = data[0]['_id']
    return data[0]
  elif len(data) == 0:
    abort(404)

def oparl_consultation_layout(data, params):
  # default values
  data['id'] = "%s/oparl/consultation/%s%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['type'] = 'http://oparl.org/schema/1.0/Consultation'
  data['body'] = generate_single_url(params=params, type='body', id=data['body'].id)
  data['created'] = data['created'].strftime("%Y-%m-%dT%H:%M:%S")
  data['modified'] = data['modified'].strftime("%Y-%m-%dT%H:%M:%S")
  
  # additional transformations
  if 'publishedDate' in data:
    if isinstance(data['publishedDate'], datetime.datetime):
      data['publishedDate'] = data['publishedDate'].strftime("%Y-%m-%d")
  
  # delete stuff
  del data['_id']
  return data

"""
# consultation organization list
@app.route('/oparl/consultation/<string:consultation_id>/organization')
def oparl_consultation_meeting(consultation_id):
  return oparl_basic(oparl_consultation_organization_data, params={'consultation_id': consultation_id})

def oparl_consultation_organization_data(params):
  data = db.get_consultation(deref={'value': 'organization', 'list_select': '_id'},
                             search_params={'_id': ObjectId(params['consultation_id'])},
                             add_prefix = "%s/oparl/organization/" % app.config['api_url'],
                             add_postfix = generate_postfix(params))
  return data
"""

####################################################
# paper
####################################################

# single paper
@app.route('/oparl/paper/<string:paper_id>')
def oparl_paper(paper_id):
  return oparl_basic(oparl_paper_data, params={'_id': paper_id})

def oparl_paper_data(params):
  data = db.get_paper(search_params={'_id': ObjectId(params['_id'])})
  if len(data) == 1:
    return oparl_paper_layout(data[0])
  elif len(data) == 0:
    abort(404)

def oparl_paper_layout(data, params):
  # default values
  data['id'] = "%s/oparl/paper/%s%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['type'] = 'http://oparl.org/schema/1.0/Paper'
  data['body'] = generate_single_url(params=params, type='body', id=data['body'].id)
  data['created'] = data['created'].strftime("%Y-%m-%dT%H:%M:%S")
  data['modified'] = data['modified'].strftime("%Y-%m-%dT%H:%M:%S")
  
  # additional transformations
  if 'publishedDate' in data:
    if isinstance(data['publishedDate'], datetime.datetime):
      data['publishedDate'] = data['publishedDate'].strftime("%Y-%m-%d")
  
  # TODO for data model
  if 'georeferences' in data:
    del data['georeferences']
  if 'georeferences' in data:
    del data['georeferencesGenerated']
  if 'title' in data:
    del data['title']
  
  # delete stuff
  del data['_id']
  return data


"""
# paper auxiliaryFile list
@app.route('/oparl/paper/<string:paper_id>/auxiliaryFile')
def oparl_paper_auxiliaryFile(paper_id):
  return oparl_basic(oparl_paper_auxiliaryFile_data, params={'paper_id': paper_id})

def oparl_paper_auxiliaryFile_data(params):
  data = db.get_paper(deref={'value': 'auxiliaryFile', 'list_select': '_id'},
                      search_params={'_id': ObjectId(params['paper_id'])},
                      add_prefix = "%s/oparl/file/" % app.config['api_url'],
                      add_postfix = generate_postfix(params))
  return data

# paper consultation list
@app.route('/oparl/paper/<string:paper_id>/consultation')
def oparl_paper_consultation(paper_id):
  return oparl_basic(oparl_paper_consultation_data, params={'paper_id': paper_id})

def oparl_paper_consultation_data(params):
  data = db.get_consultation(consultation_list = True,
                             search_params = {'paper': DBRef('paper', ObjectId(params['paper_id']))},
                             add_prefix = "%s/oparl/consultation/" % app.config['api_url'],
                             add_postfix = generate_postfix(params))
  return data

# paper relatedPaper list
@app.route('/oparl/paper/<string:paper_id>/relatedPaper')
def oparl_paper_relatedPaper(paper_id):
  return oparl_basic(oparl_paper_relatedPaper_data, params={'paper_id': paper_id})

def oparl_paper_relatedPaper_data(params):
  data_1 = db.get_paper(paper_list = True,
                        search_params = {'relatedPaper': DBRef('paper', ObjectId(params['paper_id']))},
                        add_prefix = "%s/oparl/paper/" % app.config['api_url'],
                        add_postfix = generate_postfix(params))
  data_2 = db.get_paper(deref={'value': 'relatedPaper', 'list_select': '_id'},
                        search_params = {'_id': ObjectId(params['paper_id'])},
                        add_prefix = "%s/oparl/paper/" % app.config['api_url'],
                        add_postfix = generate_postfix(params))
  data = data_1 + data_2
  return data

# paper subordinatedPaper list
@app.route('/oparl/paper/<string:paper_id>/subordinatedPaper')
def oparl_paper_subordinatedPaper(paper_id):
  return oparl_basic(oparl_paper_subordinatedPaper_data, params={'paper_id': paper_id})


def oparl_paper_subordinatedPaper_data(params):
  data_super = db.get_paper(paper_list = True,
                            search_params = {'superordinatedPaper': DBRef('paper', ObjectId(params['paper_id']))},
                            add_prefix = "%s/oparl/paper/" % app.config['api_url'],
                            add_postfix = generate_postfix(params))
  data_sub = db.get_paper(deref = {'value': 'subordinatedPaper', 'list_select': '_id'},
                        search_params = {'_id': ObjectId(params['paper_id'])},
                        add_prefix = "%s/oparl/paper/" % app.config['api_url'],
                        add_postfix = generate_postfix(params))
  print data_super + data_sub
  data = list(set(data_super + data_sub))
  return data

# paper superordinatedPaper list
@app.route('/oparl/paper/<string:paper_id>/superordinatedPaper')
def oparl_paper_superordinatedPaper(paper_id):
  return oparl_basic(oparl_paper_superordinatedPaper_data, params={'paper_id': paper_id})


def oparl_paper_superordinatedPaper_data(params):
  data_sub = db.get_paper(paper_list = True,
                          search_params = {'subordinatedPaper': DBRef('paper', ObjectId(params['paper_id']))},
                          add_prefix = "%s/oparl/paper/" % app.config['api_url'],
                          add_postfix = generate_postfix(params))
  data_super = db.get_paper(deref = {'value': 'superordinatedPaper', 'list_select': '_id'},
                            search_params = {'_id': ObjectId(params['paper_id'])},
                            add_prefix = "%s/oparl/paper/" % app.config['api_url'],
                            add_postfix = generate_postfix(params))
  data = list(set(data_super + data_sub))
  return data

# paper underDirectionOf list
@app.route('/oparl/paper/<string:paper_id>/underDirectionOf')
def oparl_paper_underDirectionOf(paper_id):
  return oparl_basic(oparl_paper_underDirectionOf_data, params={'paper_id': paper_id})

def oparl_paper_underDirectionOf_data(params):
  data = db.get_paper(deref={'value': 'underDirectionOf', 'list_select': '_id'},
                      search_params = {'_id': ObjectId(params['paper_id'])},
                      add_prefix = "%s/oparl/consultation/" % app.config['api_url'],
                      add_postfix = generate_postfix(params))
  return data
"""

####################################################
# file
####################################################

"""
# file list
@app.route('/oparl/file')
def oparl_files():
  return oparl_basic(oparl_files_data)

def oparl_files_data(params):
  return db.get_file(file_list = True,
                     add_prefix = "%s/oparl/file/" % app.config['api_url'],
                     add_postfix=generate_postfix(params))
"""

# single file
@app.route('/oparl/file/<string:file_id>')
def oparl_document(file_id):
  return oparl_basic(oparl_file_data, params={'_id': file_id})

def oparl_file_data(params):
  data = db.get_file(search_params={'_id': ObjectId(params['_id'])})
  if len(data) == 1:
    return (oparl_file_layout(data[0], params))
  elif len(data) == 0:
    abort(404)

def oparl_file_layout(data, params):
  # default values
  data['id'] = "%s/oparl/file/%s%s" % (app.config['api_url'], data['_id'], generate_postfix(params))
  data['type'] = 'https://oparl.org/schema/1.0/File'
  data['body'] = "%s/oparl/body/%s%s" % (app.config['api_url'], data['body'].id, generate_postfix(params))
  data['created'] = data['created'].strftime("%Y-%m-%dT%H:%M:%S")
  data['modified'] = data['modified'].strftime("%Y-%m-%dT%H:%M:%S")
  
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
  
  # delete stuff
  del data['_id']
  if 'file' in data:
    del data['file']
  if 'thumbnails' in data:
    del data['thumbnails']
  if 'fulltextGenerated' in data:
    del data['fulltextGenerated']
  if 'thumbnailsGenerated' in data:
    del data['thumbnailsGenerated']
  return data

"""
# file meeting list
@app.route('/oparl/file/<string:file_id>/meeting')
def oparl_file_meeting(file_id):
  return oparl_basic(oparl_file_meeting_data, params={'file_id': file_id})

def oparl_file_meeting_data(params):
  invitation_data = db.get_meeting(meeting_list = True,
                                   search_params = {'invitation': DBRef('file', ObjectId(params['file_id']))},
                                   add_prefix = "%s/oparl/meeting/" % app.config['api_url'],
                                   add_postfix = generate_postfix(params))
  auxiliaryFile_data = db.get_meeting(meeting_list = True,
                                      search_params = {'auxiliaryFile': DBRef('file', ObjectId(params['file_id']))},
                                      add_prefix = "%s/oparl/meeting/" % app.config['api_url'],
                                      add_postfix = generate_postfix(params))
  resultsProtocol_data = db.get_meeting(meeting_list = True,
                                        search_params = {'resultsProtocol': DBRef('file', ObjectId(params['file_id']))},
                                        add_prefix = "%s/oparl/meeting/" % app.config['api_url'],
                                        add_postfix = generate_postfix(params))
  verbatimProtocol_data = db.get_meeting(meeting_list = True,
                                        search_params = {'verbatimProtocol': DBRef('file', ObjectId(params['file_id']))},
                                        add_prefix = "%s/oparl/meeting/" % app.config['api_url'],
                                        add_postfix = generate_postfix(params))
  data = invitation_data + auxiliaryFile_data + resultsProtocol_data + verbatimProtocol_data
  return data

# file paper list
@app.route('/oparl/file/<string:file_id>/paper')
def oparl_file_paper(file_id):
  return oparl_basic(oparl_file_paper_data, params={'file_id': file_id})

def oparl_file_paper_data(params):
  mainFile_data = db.get_paper(paper_list = True,
                               search_params = {'mainFile': DBRef('file', ObjectId(params['file_id']))},
                               add_prefix = "%s/oparl/paper/" % app.config['api_url'],
                               add_postfix = generate_postfix(params))
  auxiliaryFile_data = db.get_paper(paper_list = True,
                                    search_params = {'auxiliaryFile': DBRef('file', ObjectId(params['file_id']))},
                                    add_prefix = "%s/oparl/paper/" % app.config['api_url'],
                                    add_postfix = generate_postfix(params))
  data = mainFile_data + auxiliaryFile_data
  return data
"""

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

def oparl_basic(content_fuction, params={}, direct_output=False):
  start_time = time.time()
  jsonp_callback = request.args.get('callback', None)
  request_info = {}
  html = request.args.get('html')
  html = html == '1'
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
  

def generate_sublist_url(params={}, main_type='', main_id='_id', sublist_type=''):
  return "%s/oparl/%s/%s/%s%s" % (app.config['api_url'], main_type, params[main_id], sublist_type, generate_postfix(params))

def generate_single_url(params={}, type='', id=''):
  return "%s/oparl/%s/%s%s" % (app.config['api_url'], type, id, generate_postfix(params))

def generate_single_backref_url(params={}, get='', type='', reverse_type='', id=''):
  get = getattr(db, get)
  uid = str((get(search_params={reverse_type: DBRef(reverse_type, ObjectId(id))}, values={'_id':1}))[0]['_id'])
  return "%s/oparl/%s/%s%s" % (app.config['api_url'], type, uid, generate_postfix(params))

def oparl_generate_list_search_params(params):
  search_params = {'body': DBRef('body', ObjectId(params['body_id']))}
  if 'q' in params:
    search_params['modified'] = { '$lt': datetime.datetime.strptime(params['q'].split(':<')[1], "%Y-%m-%dT%H:%M:%S.%f") }
  return search_params

def oparl_generate_list_items(params, search_params, result_count, data, type):
  result = {
    'items': data,
    'itemsPerPage': app.config['oparl_items_per_page']
  }
  if result_count > app.config['oparl_items_per_page']:
    result['nextPage'] = '%s/oparl/body/%s/%s%s' % (app.config['api_url'], params['body_id'], type, generate_postfix(params, ['q=modified:<%s' % result['items'][9]['modified'].strftime("%Y-%m-%dT%H:%M:%S.%f")]))
  if 'modified' in search_params:
    result['firstPage'] = '%s/oparl/body/%s/%s%s' % (app.config['api_url'], params['body_id'], type, generate_postfix(params))
  return result

