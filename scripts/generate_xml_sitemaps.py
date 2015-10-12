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

import config
import os
import inspect
import argparse
import datetime
import subprocess
from pymongo import MongoClient
import urllib
import config
from bson import DBRef


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

def generate_sitemaps(config):
  limit = 50000
  sitemaps = []
  urls = []
  bodies = []
  
  # tidy up
  for the_file in os.listdir(config['sitemap_folder']):
    file_path = os.path.join(config['sitemap_folder'], the_file)
    try:
      os.unlink(file_path)
    except Exception, e:
      print e
  
  # gather bodies
  for body in db.body.find({}):
    bodies.append(body['_id'])
  
    # gather file URLs
  for body in bodies:
    print "Generating file sitemap for body %s" % body
    for file in db.file.find({'body': DBRef('body', body), 'depublication': {'$exists': False}}):
      if 'file' in file:
        fileentry = db.fs.files.find_one(file['file'].id)
        thisfile = {
          'path': "%s/file/%s" % (config['base_url'], file['_id']),
          'lastmod': fileentry['uploadDate']
        }
        urls.append(thisfile)

    # create sitemap(s) with individual file URLs
    sitemap_count = 1
    while len(urls) > 0:
      shortlist = []
      while len(shortlist) < limit and len(urls) > 0:
        shortlist.append(urls.pop(0))
      sitemap_name = 'files_%s_%d' % (body, sitemap_count)
      generate_sitemap(shortlist, sitemap_name)
      sitemaps.append(sitemap_name)
      sitemap_count += 1

  urls = []
  for body in bodies:
    print "Generating paper sitemap for body %s" % body
    # gather paper URLs
    for paper in db.paper.find({'body': DBRef('body', body)}):
      thisfile = {
        'path': "%s/paper/%s" % (config['base_url'], paper['_id']),
        'lastmod': paper['modified']
      }
      urls.append(thisfile)

    # create sitemap(s) with individual attachment URLs
    sitemap_count = 1
    while len(urls) > 0:
      shortlist = []
      while len(shortlist) < limit and len(urls) > 0:
        shortlist.append(urls.pop(0))
      sitemap_name = 'papers_%s_%d' % (body, sitemap_count)
      generate_sitemap(shortlist, sitemap_name)
      sitemaps.append(sitemap_name)
      sitemap_count += 1


  # Create meta-sitemap
  meta_sitemap_path = config['sitemap_folder'] + os.sep + 'sitemap.xml'
  f = open(meta_sitemap_path, 'w')
  f.write("""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">""")
  for sitemap_name in sitemaps:
    f.write("""\n  <sitemap>
      <loc>%s/static/sitemap/%s.xml.gz</loc>
  </sitemap>""" % (config['base_url'], sitemap_name))
  f.write("\n</sitemapindex>\n")
  f.close()


def generate_sitemap(files, name):
  sitemap_path = (config['sitemap_folder'] + os.sep + name + '.xml')
  f = open(sitemap_path, 'w')
  f.write("""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">""")
  for entry in files:
    f.write("""\n  <url>
    <loc>%s</loc>
    <lastmod>%s</lastmod>
  </url>""" % (entry['path'], entry['lastmod'].strftime('%Y-%m-%d')))
  f.write("</urlset>\n")
  f.close()
  cmd = "gzip %s" % sitemap_path
  execute(cmd)


if __name__ == '__main__':
  connection = MongoClient(config.MONGO_HOST, config.MONGO_PORT)
  db = connection[config.MONGO_DBNAME]
  config = get_config(db)
  generate_sitemaps(config)
