# encoding: utf-8

from flask.ext.script import Manager

from webapp import app
from webapp import util

manager = Manager(app)

@manager.command
def verify_created_modified():
  util.verify_created_modified()

if __name__ == "__main__":
  manager.run()