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

import os
import inspect
import config
import tempfile
import subprocess
from pymongo import MongoClient
import gridfs
import datetime
import time
import argparse
from bson import ObjectId, DBRef
import types

STATS = {
  'attachments_without_fulltext': 0,
  'attachments_with_outdated_fulltext': 0,
  'fulltext_created': 0,
  'fulltext_not_created': 0,
  'wrong_mimetype': 0
}

def get_config(db, body_id):
  """
  Returns Config JSON
  """
  config = db.config.find_one()
  if '_id' in config:
    del config['_id']
  local_config = db.body.find_one({'_id': ObjectId(body_id)})
  if 'config' in local_config:
    config = merge_dict(config, local_config['config'])
    del local_config['config']
  config['city'] = local_config
  return config

def merge_dict(x, y):
  merged = dict(x,**y)
  xkeys = x.keys()
  for key in xkeys:
    if type(x[key]) is types.DictType and y.has_key(key):
      merged[key] = merge_dict(x[key],y[key])
  return merged

def generate_fulltext(db, config, body_id):
  """Generiert Volltexte für die gesamte file-Collection"""

  # Files mit veralteten Volltexten
  query = {'fulltextGenerated': {'$exists': True}, 'depublication': {'$exists': False}, 'body': DBRef('body', ObjectId(body_id))}
  for single_file in db.file.find(query):
    # Dateiinfo abholen
    file_data = db.fs.files.find_one({'_id': single_file['file'].id})
    if file_data['uploadDate'] > single_file['fulltextGenerated']:
      # Volltext muss erneuert werden
      STATS['attachments_with_outdated_fulltext'] += 1
      generate_fulltext_for_file(db, config, single_file)

  # Files ohne Volltext
  query = {'fulltextGenerated': {'$exists': False}, 'body': DBRef('body', ObjectId(body_id))}
  for single_file in db.file.find(query):
    STATS['attachments_without_fulltext'] += 1
    generate_fulltext_for_file(db, config, single_file)


def store_tempfile(file_id, db):
  file = db.file.find_one({'_id': file_id})
  file_data = fs.get(file['file'].id)
  temppath = tempdir + os.sep + str(file_data._id)
  tempf = open(temppath, 'wb')
  tempf.write(file_data.read())
  tempf.close()
  return temppath


def generate_fulltext_for_file(db, config, single_file):
  """
  Generiert Text-Export fuer ein bestimmtes Attachment
  """
  # temporaere Datei des Attachments anlegen
  print "Processing file_id=%s" % (single_file['_id'])
  if 'file' not in single_file:
    print "Fatal Error: file missing in file object"
  else:
    path = store_tempfile(single_file['_id'], db)
    
    if single_file['mimetype'] == 'application/pdf':
      cmd = config['pdf_to_text_cmd'] + ' -nopgbrk -enc UTF-8 ' + path + ' -'
    elif single_file['mimetype'] == 'application/msword':
      cmd = config['abiword_cmd'] + ' --to=txt --to-name=fd://1 ' + path
    else:
      cmd = None
      STATS['wrong_mimetype'] += 1
    
    if cmd:
      text = execute(cmd)
      if text is not None:
        text = text.strip()
        text = text.decode('utf-8')
        text = text.replace(u"\u00a0", " ")
  
    # delete temp file
    os.unlink(path)
    now = datetime.datetime.utcnow()
    update = {
      '$set': {
        'fulltextGenerated': now,
        'modified': now
      }
    }
    if cmd:
      if text is None or text == '':
        STATS['fulltext_not_created'] += 1
      else:
        update['$set']['fulltext'] = text
        STATS['fulltext_created'] += 1
      db.file.update({'_id': single_file['_id']}, update)


def execute(cmd):
  new_env = os.environ.copy()
  new_env['XDG_RUNTIME_DIR'] = '/tmp/'
  output, error = subprocess.Popen(
    cmd.split(' '), stdout=subprocess.PIPE,
    stderr=subprocess.PIPE, env=new_env).communicate()
  if error is not None and error.strip() != '' and 'WARNING **: clutter failed 0, get a life.' not in error:
    print >> sys.stderr, "Command: " + cmd
    print >> sys.stderr, "Error: " + error
  return output


def milliseconds():
  """Return current time as milliseconds int"""
  return int(round(time.time() * 1000))


def print_stats():
  for key in STATS.keys():
    print "%s: %d" % (key, STATS[key])

if __name__ == '__main__':
  parser = argparse.ArgumentParser(
    description='Generate Fulltext for given Body ID')
  parser.add_argument(dest='body_id', help=("e.g. 54626a479bcda406fb531236"))
  options = parser.parse_args()
  body_id = options.body_id
  connection = MongoClient(config.MONGO_HOST, config.MONGO_PORT)
  db = connection[config.MONGO_DBNAME]
  fs = gridfs.GridFS(db)
  config = get_config(db, body_id)
  tempdir = tempfile.mkdtemp()
  generate_fulltext(db, config, body_id)
  os.rmdir(tempdir)
  print_stats()
