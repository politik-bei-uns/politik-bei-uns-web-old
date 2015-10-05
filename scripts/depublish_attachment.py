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
from pymongo import MongoClient
import gridfs
import bson
import gridfs
import datetime
import shutil
from generate_thumbs import subfolders_for_file


ALLOWED_CODES = [
  'COPYRIGHT',
  'COPYRIGHT_RISK',
  'NONPUBLIC_DOCUMENT',
  'PRIVACY'
]

def get_config(db):
  """
  Returns Config JSON
  """
  config = db.config.find_one()
  if '_id' in config:
    del config['_id']
  return config


def depublish(config, fs, file_id, code, message):
  aid = bson.ObjectId(file_id)
  if not file_exists(aid):
    sys.stderr.write("No file found with _id='%s'\n" %
      file_id)
    return
  body_id = modify_file(fs, aid, code, message)
  remove_thumbnails(config, body_id, file_id)


def file_exists(file_id):
  """
  Return True if file exists, False otherwise
  """
  find = db.file.find_one(file_id)
  if find is not None:
    return True
  return False


def modify_file(fs, file_id, code, message):
  """
  Write depublish info,
  remove fulltext and thumbnails,
  remove file from GridFS
  """
  doc = db.file.find_one(file_id)
  # Delete file from gridfs
  if 'file' in doc:
    fs.delete(doc['file'].id)
  # Modify file document
  db.file.update(
    {'_id': file_id},
    {
      '$set': {
        'depublication': {
          'date': datetime.datetime.utcnow(),
          'code': code,
          'comment': message
        }
      },
      '$unset': {
        'fulltext': 1,
        'thumbnails': 1,
        'file': 1
      }
    })
  return str(doc['body'].id)


def remove_thumbnails(config, body_id, file_id):
  """
  Deletes the thumbnail folder for this file
  """
  path = (config['thumbs_path'] + os.sep + body_id + os.sep + subfolders_for_file(file_id))
  shutil.rmtree(path)


if __name__ == '__main__':
  import argparse
  parser = argparse.ArgumentParser(description='Depublish an file')
  parser.add_argument('-id', '--fileid', dest='id', metavar='ID',
    type=str,
    help='ID of the file entry, e.g. 515f2d34c9791e3320c0eea2')
  parser.add_argument('-c', '--code', dest='code', metavar='CODE', type=str,
    help='One of COPYRIGHT, COPYRIGHT_RISK, NONPUBLIC_DOCUMENT, PRIVACY')
  parser.add_argument('-m', '--message', dest='message',
    type=str, metavar='MESSAGE', help='Additional explanation')

  args = parser.parse_args()

  error = False

  if args.id is None:
    sys.stderr.write("No file ID given.\n")
    error = True

  if args.code is None:
    sys.stderr.write("No reason CODE given.\n")
    error = True
  else:
    if args.code not in ALLOWED_CODES:
      sys.stderr.write("Given CODE is invalid.\n")
      error = True

  if args.message is None:
    sys.stderr.write("No MESSAGE given.\n")
    error = True

  if error:
    sys.stderr.write("\n")
    parser.print_help()
    sys.exit(1)

  connection = MongoClient(sysconfig.MONGO_HOST, sysconfig.MONGO_PORT)
  db = connection[sysconfig.MONGO_DBNAME]
  fs = gridfs.GridFS(db)
  config = get_config(db)
  
  depublish(config, fs, args.id, args.code, args.message)
