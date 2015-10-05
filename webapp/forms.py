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

from flask.ext.wtf import Form
from wtforms import validators
from wtforms import SubmitField, TextField, SelectField, FileField, TextAreaField, HiddenField, BooleanField, DecimalField, FloatField, IntegerField
from webapp import app, db

class ConfigForm(Form):
  config = TextAreaField(
    label=u'Konfiguration als JSON',
    validators=[validators.Required(), validators.Length(max=32000)],
    description='')
  submit = SubmitField(
    label=u'Daten speichern')
  
class BodyForm(Form):
  config = TextAreaField(
    label=u'Konfiguration als JSON',
    validators=[validators.Required(), validators.Length(max=32000)],
    description='')
  submit = SubmitField(
    label=u'Daten speichern')
  
class RegionForm(Form):
  name = TextField(
    label=u'Name',
    validators=[validators.Required(), validators.Length(max=32000)],
    description='')
  type = IntegerField(
    label=u'Typus (im OSM Sinne). Stadt = 1, Region = 2',
    validators=[validators.Required(), validators.NumberRange(min=1, max=2)],
    description='',
    default=0)
  bodies = TextAreaField(
    label=u'Bodies, pro Zeile eine ID',
    validators=[validators.Required(), validators.Length(max=32000)],
    description='')
  keywords = TextAreaField(
    label=u'Keywords, pro Zeile ein String',
    validators=[validators.Required(), validators.Length(max=32000)],
    description='')
  lat = FloatField(
    label=u'Lat',
    validators=[validators.Required(), validators.NumberRange(min=47.2, max=55.0)],
    description='',
    default=0.0)
  lon = FloatField(
    label=u'Lon',
    validators=[validators.Required(), validators.NumberRange(min=5.5, max=15.1)],
    description='',
    default=0.0)
  zoom = IntegerField(
    label=u'Zoom',
    validators=[validators.Required(), validators.NumberRange(min=1, max=18)],
    description='',
    default=0)
  submit = SubmitField(
    label=u'Daten speichern')