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

import os
import json
import util
import db
import datetime
import time
import urllib
import sys
from bson import ObjectId, DBRef
from lxml import etree
import dateutil.parser

from flask import abort
from flask import render_template
from flask import make_response
from flask import request
from flask import redirect
from flask import Response
from flask import Markup
from flask import session
from flask.ext.basicauth import BasicAuth
from flask.ext.pymongo import PyMongo

from webapp import app, mongo, basic_auth, cache
from forms import *
from oparl import oparl_file_accessUrl



@app.route("/")
def index():
  # Set region to get value
  region_id_get = request.args.get('r', False)
  if region_id_get:
    session['region_id'] =region_id_get
  # Set location to get value
  location_string_get = request.args.get('l', False)
  if region_id_get and location_string_get:
    session['address'] = location_string_get.replace("\"", "")
  # Delete location when location is set + region is not set:
  if not region_id_get and location_string_get:
    session['address'] = ''
  html = render_template('index.html', session=session)
  response = make_response(html, 200)
  response.headers['Last-Modified'] = datetime.datetime.now()
  response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
  response.headers['Pragma'] = 'no-cache'
  response.headers['Expires'] = '-1'
  return response


@app.route("/api")
def api_home():
  return render_template('api.html')


@app.route("/hilfe")
@cache.cached(timeout=14400)
def hilfe():
  return render_template('hilfe.html')

@app.route("/ueber")
@cache.cached(timeout=14400)
def ueber():
  return render_template('ueber.html')

@app.route("/impressum")
@cache.cached(timeout=14400)
def impressum():
  return render_template('impressum.html')

@app.route("/datenschutz")
@cache.cached(timeout=14400)
def datenschutz():
  return render_template('datenschutz.html')

@app.route("/daten")
@cache.cached(timeout=14400)
def daten():
  """
  Anzeige der /daten Seite mit Auflistung der
  Download-Dateien
  """
  body_list = db.get_body()
  body_dict = {}
  for body in body_list:
    body_dict[str(body['_id'])] = body['name']
  data_list = []
  for file in os.listdir(app.config['data_dump_folder']):
    if file.endswith(".tar.bz2"):
      stat = os.lstat(app.config['data_dump_folder'] + os.sep + file)
      data_list.append({
        'id': file.split('.')[0],
        'name': body_dict[file.split('.')[0]],
        'size': "%d" % (stat.st_size / 1024.0 / 1024.0)
      })
  file_list = []
  for file in os.listdir(app.config['files_dump_folder']):
    if file.endswith(".tar.bz2"):
      stat = os.lstat(app.config['files_dump_folder'] + os.sep + file)
      file_list.append({
        'id': file.split('.')[0],
        'name': body_dict[file.split('.')[0]],
        'size': "%d" % (stat.st_size / 1024.0 / 1024.0 / 1024.0)
      })
  statistics = []
  for body in db.get_body(sort=['name', 1]):
    statistics.append({
      'name': body['name'],
      'organization': db.get_organization_count({'body': DBRef('body', body['_id'])}),
      'person': db.get_person_count({'body': DBRef('body', body['_id'])}),
      'meeting': db.get_meeting_count({'body': DBRef('body', body['_id'])}),
      'agendaItem': db.get_agendaItem_count({'body': DBRef('body', body['_id'])}),
      'paper': db.get_paper_count({'body': DBRef('body', body['_id'])}),
      'file': db.get_file_count({'body': DBRef('body', body['_id'])})
    })
  statistics_all = {
      'organization': db.get_organization_count(),
      'person': db.get_person_count(),
      'meeting': db.get_meeting_count(),
      'agendaItem': db.get_agendaItem_count(),
      'paper': db.get_paper_count(),
      'file': db.get_file_count()
    }
  return render_template('daten.html', data_list=data_list, file_list=file_list, statistics=statistics, statistics_all=statistics_all)


@app.route("/disclaimer")
@cache.cached(timeout=14400)
def disclaimer():
  return render_template('disclaimer.html')


@app.route("/favicon.ico")
def favicon():
  return ""

@app.route("/robots.txt")
@cache.cached(timeout=14400)
def robots_txt():
  return render_template('robots.txt')

# Backward compatibility
@app.route("/anhang/<string:file_id>")
def file_show_redirect(file_id):
  return redirect('/file/%s' % file_id, code=301)


@app.route("/file/<string:file_id>")
@cache.memoize(timeout=14400)
def file_show(file_id):
  """
  Anzeigen eines Files
  """
  result = db.get_file(search_params = {'_id': ObjectId(file_id)},
                        deref = {'values': ['body']})
  if len(result) == 0:
    abort(404)
  # add meeting
  usage = []
  meeting_invitation = db.get_meeting(search_params = {'invitation': DBRef('file', ObjectId(file_id))})
  for item in meeting_invitation:
    usage.append({ 'data': item, 'type': 'meeting', 'function': 'invitation'})
  meeting_resultsProtocol = db.get_meeting(search_params = {'resultsProtocol': DBRef('file', ObjectId(file_id))})
  for item in meeting_resultsProtocol:
    usage.append({ 'data': item, 'type': 'meeting', 'function': 'resultsProtocol'})
  meeting_verbatimProtocol = db.get_meeting(search_params = {'verbatimProtocol': DBRef('file', ObjectId(file_id))})
  for item in meeting_verbatimProtocol:
    usage.append({ 'data': item, 'type': 'meeting', 'function': 'verbatimProtocol'})
  meeting_auxiliaryFile =  db.get_meeting(search_params = {'auxiliaryFile': DBRef('file', ObjectId(file_id))})
  for item in meeting_auxiliaryFile:
    usage.append({ 'data': item, 'type': 'meeting', 'function': 'auxiliaryFile'})
  
  # add agendaItem
  agendaItem_resolutionFile = db.get_agendaItem(search_params = {'resolutionFile': DBRef('file', ObjectId(file_id))})
  for item in agendaItem_resolutionFile:
    usage.append({ 'data': item, 'type': 'agendaItem', 'function': 'resolutionFile'})
  agendaItem_auxiliaryFile = db.get_agendaItem(search_params = {'auxiliaryFile': DBRef('file', ObjectId(file_id))})
  for item in agendaItem_auxiliaryFile:
    usage.append({ 'data': item, 'type': 'agendaItem', 'function': 'auxiliaryFile'})
  
  # add paper
  paper_mainFile = db.get_paper(search_params = {'mainFile': DBRef('file', ObjectId(file_id))})
  for item in paper_mainFile:
    usage.append({ 'data': item, 'type': 'paper', 'function': 'mainFile'})
  paper_auxiliaryFile = db.get_paper(search_params = {'auxiliaryFile': DBRef('file', ObjectId(file_id))})
  for item in paper_auxiliaryFile:
    usage.append({ 'data': item, 'type': 'paper', 'function': 'auxiliaryFile'})
  
  if len(usage):
    result[0]['usage'] = usage
  return render_template('file_details.html', file=result[0])


@app.route("/file/<string:file_id>/download")
def file_download(file_id):
  """
  Download eines Files
  """
  return oparl_file_accessUrl(file_id)


@app.route("/suche")
def suche():
  """
  URL-Parameter:
  q: Suchanfrage, nutzer-formuliert
  fq: Filter query (Lucene Syntax)
  sort: Sortierung, z.B. "id asc"
  start: Offset im Suchergebnis
  num: Anzahl der Treffer pro Seite
  date: Datumsbereich als String
  """
  search_settings = {}
  search_settings['r'] = request.form.get('r')
  if not search_settings['r']:
    search_settings['r'] = request.args.get('r', app.config['region_default'])
  search_settings['q'] = request.args.get('q', '')
  search_settings['fq'] = request.args.get('fq', '')
  search_settings['sort'] = request.args.get('sort', '')
  search_settings['start'] = int(request.args.get('start', '0'))
  search_settings['ppp'] = int(request.args.get('ppp', '10'))
  search_settings['ppp'] = min(search_settings['ppp'], 100)  # max 100 items
  search_settings['date'] = request.args.get('date', '')
  html = render_template('suche.html', search_settings=search_settings)
  response = make_response(html, 200)
  response.headers['Last-Modified'] = datetime.datetime.now()
  response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
  response.headers['Pragma'] = 'no-cache'
  response.headers['Expires'] = '-1'
  return response

@app.route("/suche/feed")
def suche_feed():
  start_time = time.time()
  jsonp_callback = request.args.get('callback', None)
  q = request.args.get('q', '*:*')
  fq = request.args.get('fq', '')
  date_param = request.args.get('date', '')
  region = request.args.get('r', app.config['region_default'])
  
  # Suche wird durchgeführt
  query = db.query_paper(region=region, q=q, fq=fq, sort='publishedDate:desc', start=0,
             papers_per_page=50, facets=False)
  
  # Generate Root and Metainfos
  search_url = "%s/suche/?r=%s&q=%s&fq=%s" % (app.config['base_url'], region, q, fq)
  feed_url = "%s/suche/feed/?r=%s&q=%s&fq=%s" % (app.config['base_url'], region, q, fq)
  root = etree.Element("rss", version="2.0", nsmap={'atom': 'http://www.w3.org/2005/Atom'})
  channel = etree.SubElement(root, "channel")
  etree.SubElement(channel, "title").text = 'Offenes Ratsinformationssystem: Paper-Feed'
  etree.SubElement(channel, "link").text = search_url
  etree.SubElement(channel, "language").text = 'de-de'
  description = u"Neue oder geänderte Dokumente mit dem Suchbegriff %s in %s" % (q, app.config['regions'][region]['name'])
  # TODO: Einschränkungen mit in die Description
  if fq:
    description += ''
  etree.SubElement(channel, "description").text = description
  etree.SubElement(channel, '{http://www.w3.org/2005/Atom}link', href=feed_url, rel="self", type="application/rss+xml")
  
  # Generate Result Items
  for paper in query['result']:
    item = etree.SubElement(channel, "item")
    paper_link = "%s/paper/%s" % (app.config['base_url'], paper['id'])
    description = 'Link: ' + paper_link + '</br>'
    if 'paperType' in paper:
      description = 'Art des Papers: ' + paper['paperType'] + '<br />'
    if 'publishedDate' in paper:
      description += u"Erstellt am: %s<br />" % dateutil.parser.parse(paper['publishedDate']).strftime('%d.%m.%Y')
    if 'modified' in paper:
      description += u"Zuletzt geändert am: %s<br />" % dateutil.parser.parse(paper['modified']).strftime('%d.%m.%Y')
    
    etree.SubElement(item, "pubDate").text = util.rfc1123date(paper['modified'] if 'modified' in paper else datetime.datetime.now())
    etree.SubElement(item, "title").text = paper['name'] if 'name' in paper else 'Kein Titel'
    etree.SubElement(item, "description").text = description
    etree.SubElement(item, "link").text = paper_link
    etree.SubElement(item, "guid").text = paper_link
  
  response = make_response(etree.tostring(root, pretty_print=True), 200)
  response.mimetype = 'application/rss+xml'
  response.headers['Expires'] = util.expires_date(hours=24)
  response.headers['Cache-Control'] = util.cache_max_age(hours=24)
  return response

@app.route("/paper/<string:id>")
#@cache.memoize(timeout=14400)
def view_paper(id):
  """
  Gibt Dokumenten-Detailseite aus
  """
  result = db.get_paper(search_params = {'_id': ObjectId(id)},
                        deref = {'values': ['body', 'mainFile', 'auxiliaryFile', 'relatedPaper', 'subordinatedPaper', 'superordinatedPaper']})
  if len(result) == 0:
    abort(404)
  result = result[0]
  result['numberOfFiles'] = 0
  if 'mainFile' in result:
    result['numberOfFiles'] += 1
  if 'auxiliaryFile' in result:
    result['numberOfFiles'] += len(result['auxiliaryFile'])
  result['consultation'] = db.get_consultation(search_params = {'paper': DBRef('paper', ObjectId(id))})
  for consultation_id in range(len(result['consultation'])):
    agendaItem_result = db.get_agendaItem(search_params = {'consultation': DBRef('consultation', result['consultation'][consultation_id]['_id'])})
    if len(agendaItem_result):
      result['consultation'][consultation_id]['agendaItem'] = agendaItem_result[0]
      meeting_result = db.get_meeting(search_params = {'agendaItem': DBRef('agendaItem', result['consultation'][consultation_id]['agendaItem']['_id'])})
      if len(meeting_result):
        result['consultation'][consultation_id]['agendaItem']['meeting'] = meeting_result[0]
  return render_template('paper_details.html', paper=result)

#@app.route("/admin")
#@app.route("/admin/<string:funct>")
#@basic_auth.required
#def admin(funct):
#  if funct == 'responses':
#    responses=db.get_responses()
#    for response in responses:
#      response['response_type'] = app.config['RESPONSE_IDS'][response['response_type']]
#    return render_template('admin_response.html', responses=responses)
#  return render_template('admin.html')

@app.route('/admin/config', methods=['GET', 'POST'])
@basic_auth.required
def admin_config():
  if request.method == 'POST':
    config_form = ConfigForm(request.form)
    config_form.config.data = json.dumps(json.loads(config_form.config.data), cls=util.MyEncoder, sort_keys=True, indent=2, ensure_ascii=False)
  else:
    config = []
    for value in mongo.db.config.find():
      if '_id' in value:
        del value['_id']
      config.append(value)
    if len(config) == 1:
      config = config[0]
    else:
      config = {}
    config = json.dumps(config, cls=util.MyEncoder, sort_keys=True, indent=2, ensure_ascii=False)
    config_form = ConfigForm(config=config)
  if request.method == 'POST' and config_form.validate():
    config = json.loads(config_form.config.data)
    mongo.db.config.remove({})
    mongo.db.config.insert(config)
  return render_template('admin_config.html', config_form=config_form)

@app.route('/admin/regions', methods=['GET', 'POST'])
@basic_auth.required
def admin_regions():
  return render_template('admin_regions.html', regions=mongo.db.region.find().sort('_id', 1))

@app.route('/admin/region/new', methods=['GET', 'POST'])
@basic_auth.required
def admin_region_new():
  if request.method == 'POST':
    region_form = RegionForm(request.form)
  else:
    region_form = RegionForm()
  if request.method == 'POST' and region_form.validate():
    new_region_bodies = region_form.bodies.data.replace("\r", "").split("\n")
    new_region_keywords = region_form.keywords.data.replace("\r", "").split("\n")
    save_region_bodies = []
    for current_body in new_region_bodies:
      save_region_bodies.append(DBRef('body', current_body))
    mongo.db.region.insert({'name': region_form.name.data,
                            'type': region_form.type.data,
                            'active': region_form.active.data,
                            'lat': region_form.lat.data,
                            'lon': region_form.lon.data,
                            'zoom': region_form.zoom.data,
                            'body': save_region_bodies,
                            'keyword': new_region_keywords})
    return redirect('/admin/regions')
  return render_template('admin_region_new.html', region_form=region_form)

@app.route('/admin/region/edit', methods=['GET', 'POST'])
@basic_auth.required
def admin_region_edit():
  if request.method == 'POST':
    region_form = RegionForm(request.form)
  else:
    config = []
    for value in mongo.db.region.find({'_id': ObjectId(request.args.get('id'))}):
      config.append(value)
    if len(config) == 1:
      bodies = []
      for body in config[0]['body']:
        bodies.append(str(body.id))
      region_form = RegionForm(name = config[0]['name'],
                               type = int(config[0]['type']) if 'type' in config[0] else 0,
                               active = int(config[0]['active']) if 'active' in config[0] else 0,
                               lat = config[0]['lat'] if 'lat' in config[0] else 0.0,
                               lon = config[0]['lon'] if 'lon' in config[0] else 0.0,
                               zoom = config[0]['zoom'] if 'zoom' in config[0] else 0.0,
                               bodies = "\n".join(bodies),
                               keywords = "\n".join(config[0]['keyword']) if 'keyword' in config[0] else '')
    else:
      abort(500)
  if request.method == 'POST' and region_form.validate():
    region_bodies = region_form.bodies.data.replace("\r", "").split("\n")
    save_region_keywords = region_form.keywords.data.replace("\r", "").split("\n")
    save_region_bodies = []
    for current_body in region_bodies:
      save_region_bodies.append(DBRef('body', current_body))
    mongo.db.region.update({'_id': ObjectId(request.args.get('id'))}, {'name': region_form.name.data,
                                                                       'type': region_form.type.data,
                                                                       'active': region_form.active.data,
                                                                       'lat': region_form.lat.data,
                                                                       'lon': region_form.lon.data,
                                                                       'zoom': region_form.zoom.data,
                                                                       'body': save_region_bodies,
                                                                       'keyword': save_region_keywords})
    return redirect('/admin/regions')
  return render_template('admin_region_edit.html', region_form=region_form)

@app.route('/admin/bodies', methods=['GET', 'POST'])
@basic_auth.required
def admin_bodies():
  
  return render_template('admin_bodies.html', bodies=mongo.db.body.find().sort('_id', 1))

@app.route('/admin/body/new', methods=['GET', 'POST'])
@basic_auth.required
def admin_body_new():
  if request.method == 'POST':
    body_form = BodyForm(request.form)
  else:
    body_form = BodyForm()
  if request.method == 'POST' and body_form.validate():
    new_body = json.loads(body_form.config.data)
    mongo.db.body.insert(new_body)
    return redirect('/admin/bodies')
  return render_template('admin_body_new.html', body_form=body_form)


@app.route('/admin/body/edit', methods=['GET', 'POST'])
@basic_auth.required
def admin_body_edit():
  if request.method == 'POST':
    body_form = BodyForm(request.form)
    body_form.config.data = json.dumps(json.loads(body_form.config.data), cls=util.MyEncoder, sort_keys=True, indent=2, ensure_ascii=False)
  else:
    config = []
    for value in mongo.db.body.find({'_id': ObjectId(request.args.get('id'))}):
      if '_id' in value:
        del value['_id']
      config.append(value)
    if len(config) == 1:
      config = config[0]
    else:
      abort(500)
    config = json.dumps(config, cls=util.MyEncoder, sort_keys=True, indent=2, ensure_ascii=False)
    body_form = BodyForm(config=config)
  if request.method == 'POST' and body_form.validate():
    updated_body = json.loads(body_form.config.data)
    if '_id' in updated_body:
      del updated_body['_id']
    mongo.db.body.update({'_id': ObjectId(request.args.get('id'))}, updated_body)
    return redirect('/admin/bodies')
  return render_template('admin_body_edit.html', body_form=body_form)


@app.template_filter('urlencode')
def urlencode_filter(s):
  if type(s) == Markup:
    s = s.unescape()
    s = s.encode('utf8')
    s = urllib.quote_plus(s)
    return Markup(s)


@app.template_filter('debug')
def debug_filter(s):
  return s


def generate_file_thumbnail_url(body_id, file_id, resulution, number):
    return "%s/%s/%s/%s/%s/%s/%s.jpg" % (app.config["thumbs_url"], body_id, str(file_id)[-1:], str(file_id)[-2:-1], file_id, resulution, number)
app.jinja_env.globals.update(generate_file_thumbnail_url=generate_file_thumbnail_url)

