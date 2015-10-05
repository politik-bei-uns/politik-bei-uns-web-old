# encoding: utf-8

# Copyright 2012-2015 Marian Steinbach, Ernesto Ruge. All rights reserved.
# Use of this source code is governed by BSD 3-Clause license that can be
# found in the LICENSE.txt file.

import sys
sys.path.append('./')

from pymongo import MongoClient
import config
import os
import inspect
import argparse

cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile( inspect.currentframe() ))[0],"../city")))
if cmd_subfolder not in sys.path:
    sys.path.insert(0, cmd_subfolder)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate Fulltext for given City Conf File')
    parser.add_argument(dest='city', help=("e.g. bochum"))
    options = parser.parse_args()
    city = options.city
    cityconfig = __import__(city)
    connection = MongoClient(config.DB_HOST, config.DB_PORT)
    db = connection[config.DB_NAME]
    query = {'thumbnails': {'$exists': True}, "rs" : cityconfig.RS}
    modification = {
        '$unset': {
            'thumbnails': 1,
            'thumbnails_created': 1
        }
    }
    for doc in db.attachments.find(query):
        db.attachments.update({'_id': doc['_id']}, modification)
