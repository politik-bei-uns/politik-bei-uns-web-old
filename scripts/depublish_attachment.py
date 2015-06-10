# encoding: utf-8

"""
Depubliziert einen Dateianhang (attachment)

- Ergänzt Metadaten zur Löschung
- Entfernt Volltext aus Attachment-Eintrag
- Entfernt Datei aus DB (GridFS)
- Entfernt Thumbnails

TODO:
- Dokument in ElasticSearch aktualisieren

Copyright (c) 2012 Marian Steinbach

Hiermit wird unentgeltlich jeder Person, die eine Kopie der Software und
der zugehörigen Dokumentationen (die "Software") erhält, die Erlaubnis
erteilt, sie uneingeschränkt zu benutzen, inklusive und ohne Ausnahme, dem
Recht, sie zu verwenden, kopieren, ändern, fusionieren, verlegen,
verbreiten, unterlizenzieren und/oder zu verkaufen, und Personen, die diese
Software erhalten, diese Rechte zu geben, unter den folgenden Bedingungen:

Der obige Urheberrechtsvermerk und dieser Erlaubnisvermerk sind in allen
Kopien oder Teilkopien der Software beizulegen.

Die Software wird ohne jede ausdrückliche oder implizierte Garantie
bereitgestellt, einschließlich der Garantie zur Benutzung für den
vorgesehenen oder einen bestimmten Zweck sowie jeglicher Rechtsverletzung,
jedoch nicht darauf beschränkt. In keinem Fall sind die Autoren oder
Copyrightinhaber für jeglichen Schaden oder sonstige Ansprüche haftbar zu
machen, ob infolge der Erfüllung eines Vertrages, eines Delikts oder anders
im Zusammenhang mit der Software oder sonstiger Verwendung der Software
entstanden.
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
