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
import argparse
import config
import subprocess
import datetime
import shutil
import config
from pymongo import MongoClient

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


def execute(cmd):
  output, error = subprocess.Popen(
    cmd.split(' '), stdout=subprocess.PIPE,
    stderr=subprocess.PIPE).communicate()
  if error is not None and error.strip() != '':
    print >> sys.stderr, "Command: " + cmd
    print >> sys.stderr, "Error: " + error


def create_dump(extconfig, folder, body_id):
  """
  Drops dumps in folder/config.DB_NAME
  """
  cmd = (extconfig['mongodump_cmd'] + ' --host ' + config.MONGO_HOST + ' --db ' + config.MONGO_DBNAME +
      ' --out ' + folder + " --query {'body':DBRef('body',ObjectId('" + body_id + "'))}")
  
  for collection in extconfig['data_dump_tables']:
    thiscmd = cmd + ' --collection ' + collection
    execute(thiscmd)


def compress_folder(extconfig, folder, body_id):
  filename = str(body_id) + '.tar.bz2'
  execute('rm -f ' + extconfig['data_dump_folder'] + os.sep + filename)
  cmd = ('tar -cjf ' + extconfig['data_dump_folder'] + os.sep + filename + ' -C ' + folder +
      os.sep + config.MONGO_DBNAME + os.sep + ' .')
  execute(cmd)
  execute('rm -rf %s' % folder)


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Generate a database dump')
  parser.add_argument('-b', dest='body_id', default=None)
  options = parser.parse_args()
  body_id = options.body_id
  
  connection = MongoClient(config.MONGO_HOST, config.MONGO_PORT)
  db = connection[config.MONGO_DBNAME]
  extconfig = get_config(db)
  
  if body_id:
    folder = extconfig['data_dump_folder'] + os.sep + body_id + os.sep
    if not os.path.exists(folder):
      os.makedirs(folder)
    create_dump(extconfig, folder, body_id)
    compress_folder(extconfig, folder, body_id)
  else:
    for body in db.body.find():
      folder = extconfig['data_dump_folder'] + os.sep + str(body['_id'])
      if not os.path.exists(folder):
        os.makedirs(folder)
      create_dump(extconfig, folder, str(body['_id']))
      compress_folder(extconfig, folder, str(body['_id']))
