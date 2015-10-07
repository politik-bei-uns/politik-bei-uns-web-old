/*
Copyright (c) 2012 - 2015, Marian Steinbach, Ernesto Ruge
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/
var OpenRIS = {
  
  a: 6378137,
  b: (6378137 * 297.257223563) / 298.257223563,
  
  region: {},
  search_params: {},
  start_method_queue: new Array(),
  
  monthstr: {
    '01': 'Januar',
    '02': 'Februar',
    '03': 'März',
    '04': 'April',
    '05': 'Mai',
    '06': 'Juni',
    '07': 'Juli',
    '08': 'August',
    '09': 'September',
    '10': 'Oktober',
    '11': 'November',
    '12': 'Dezember'
  },
  
  /**
   * returns a list of streets for a given position
   * which are in a given rdius
   */
  streetsForPosition: function(region_id, lat, lon, radius, callback) {
    $.getJSON('/api/streets', {'region': region_id, 'lat': lat, 'lon': lon, 'radius': radius}, callback);
  },
  
  /**
   * Fetch details for a document
   */
  paperDetails: function(id, callback) {
    options = {
      reference: id,
      output: 'meetings,files,thumbnails'}
    $.getJSON('/api/paper', options, callback);
  },
  
  regionLoad: function() {
    // copy region_data in region object
    this.region = region_data;
    // region click
    $('#change-region').click(function(){
      $.getJSON('/api/regions', function(data) {
        $.each(data, function(region_id, region){
          $('#region-question').css({'display': 'none'});
          $('<span/>')
            .text(region['name'])
            .attr({'class': 'awesome extrawide'})
            .click(
              {'region': region},
              function(event) {
                OpenRIS.region = {
                  'id': event.data.region.id,
                  'name': event.data.region.name,
                  'lat': event.data.region.lat,
                  'lon': event.data.region.lon,
                  'zoom': event.data.region.zoom,
                  'type': event.data.region.type,
                  'keyword': event.data.region.keyword
                }
                $('#region-choice').html('');
                $('#region-question').css({'display': 'block'});
                // update region name
                $('#region-current').text(OpenRIS.region.name);
                sessionParams = {
                  'region_id': OpenRIS.region.id
                };
                OpenRIS.session(sessionParams, function() {});
                if (typeof(OpenRIS.post_region_change) == 'function') {
                  OpenRIS.post_region_change();
                }
              }
            )
            .appendTo('#region-choice');
        });
      });
    });
  },
  
  /**
   * Formatiert ein ISO-Datum zum gebräuchlichen deutschen Format DD.MM.YYYY
   * @param   String   ISO-Datum (YYYY-MM-DD)
   * @return  String   Deutsches Datum
   */
  formatIsoDate: function(datestr){
    if (datestr != null && typeof datestr != "undefined") {
      var year = datestr.substr(0,4);
      var month = datestr.substr(5,2);
      var day = datestr.substr(8,2);
      return parseInt(day, 10) + '. ' + this.monthstr[month] + ' ' + year;
    }
    return datestr;
  },
  
  truncateText: function(text, size){
    if (text.length <= size) {
      return text;
    }
    list = text.split(/\s+/);
    newtext = '';
    while (newtext.length < size) {
      newtext = newtext + ' ' + list.shift();
    }
    return newtext.trim() + '&nbsp;&hellip;';
  },
  
  fileSizeString: function(bytes){
    if (bytes < (1024 * 700)) {
      return Math.round(bytes / 1024) + ' KB';
    } else if (bytes < (1024 * 1024 * 5)) {
      return (bytes / 1024 / 1024).toFixed(1).replace('.', ',') + ' MB';
    }
    return(bytes);
  },
  
  /**
   * Takes an object of standard search parameters and deletes those which are default or null
   */
  processSearchParams: function(params){
    params['r'] = OpenRIS.region.id
    if (typeof params['q'] === 'undefined'
      || params['q'] == null
      || params['q'] === ''
      || params['q'] === '*:*') {
      delete params['q'];
    }
    if (typeof params['fq'] === 'undefined'
      || params['fq'] == null
      || params['fq'] === ''
      || params['fq'] === '*:*') {
      delete params['fq'];
    }
    if (typeof params['num'] == 'undefined'
      || params['num'] == null
      || params['num'] == ''
      || params['num'] <= 10) {
      delete params['num'];
    }
    if (typeof params['start'] == 'undefined'
      || params['start'] == null
      || params['start'] == ''
      || params['start'] <= 0) {
      delete params['start'];
    }
    if (typeof params['sort'] == 'undefined'
      || params['sort'] == null
      || params['sort'] == '') {
      delete params['sort'];
    }
     if (typeof params['date'] == 'undefined'
      || params['date'] == null
      || params['date'] == '') {
      delete params['date'];
    }
   return params;
  },
  
  deepCopy: function(obj) {
    if (typeof obj !== "object") return obj;
    if (obj.constructor === RegExp) return obj;
    
    var retVal = new obj.constructor();
    for (var key in obj) {
      if (!obj.hasOwnProperty(key)) continue;
      retVal[key] = OpenRIS.deepCopy(obj[key]);
    }
    return retVal;
  },
  
  search: function(params, callback){
    var cleanParams = OpenRIS.processSearchParams(params);
    $.getJSON('/api/papers', cleanParams, callback);
  },
  
  session: function(params, callback){
    $.getJSON('/api/session', params, callback);
  },
  
  /**
   * Verarbeitet das Placefinder Suchergebnis und sortiert
   * Einträge, die nicht zur Auswahl angezeigt werden sollen,
   * aus.
   */
  filterGeocodingChoices: function(results){
    results = OpenRIS.deepCopy(results);
    // Alle Einträge bekommen eigenen Qualitäts-Koeffizienten
    for (var n in results) {
      results[n].okquality = 1.0;
      // verdreifache wenn neighborhood gesetzt
      if (results[n].address.suburb != '') {
        results[n].okquality *= 3.0;
      }
      // verdopple wenn PLZ gesetzt
      if (results[n].address.postcode != '') {
        results[n].okquality *= 3.0;
      }
      // keine Straße gesetzt: Punktzahl durch 10
      if (typeof(results[n].address.road) === 'undefined') {
        results[n].okquality *= 0.1;
      }
    }
    // Sortieren nach 'okquality' abwärts
    results.sort(OpenRIS.qualitySort);
    var resultByPostCode = {};
    var n;
    for (n in results) {
        if (typeof(resultByPostCode[results[n].address.postcode]) === 'undefined') {
          resultByPostCode[results[n].address.postcode] = results[n];
        }
    }
    ret = [];
    for (n in resultByPostCode) {
        ret.push(resultByPostCode[n]);
    }
    // Sortieren nach Längengrad
    ret.sort(OpenRIS.longitudeSort);
    return ret;
  },
  
  qualitySort: function(a, b) {
    return b.okquality - a.okquality
  },

  longitudeSort: function(a, b) {
        return parseFloat(a.lon) - parseFloat(b.lon)
    },
  
  cylindrics: function(phi) {
    var	u = this.a * Math.cos(phi),
      v = this.b * Math.sin(phi),
      w = Math.sqrt(u * u + v * v),
      r = this.a * u / w,
      z = this.b * v / w,
      R = Math.sqrt(r * r + z * z);
    return { r : r, z : z, R : R };
  },

  /**
   * Anstand zwischen zwei Geo-Koordinaten
   * @param    phi1     Float    Länge Punkt 1
   * @param    lon1     Float    Breite Punkt 1
   * @param    phi2     Float    Länge Punkt 2
   * @param    lon2     Float    Breite Punkt 3
   * @param    small    Boolean  True für kleine Distanzen
   */
  geo_distance: function(phi1, lon1, phi2, lon2, small) {
    var dLambda = lon1 - lon2;
    with (cylindrics(phi1)) {
      var	r1 = r,
        z1 = z,
        R1 = R;
    }
    with (cylindrics(phi2)) {
      var	r2 = r,
        z2 = z,
        R2 = R;
    }
    var	cos_dLambda = Math.cos(dLambda),
      scalar_xy = r1 * r2 * cos_dLambda,
      cos_alpha = (scalar_xy + z1 * z2) / (R1 * R2);
  
    if (small) {
      var	dr2 = r1 * r1 + r2 * r2 - 2 * scalar_xy,
        dz2 = (z1 - z2) * (z1 - z2),
        R = Math.sqrt((dr2 + dz2) / (2 * (1 - cos_alpha)));
    }
    else
      R = Math.pow(a * a * b, 1/3);
      return R * Math.acos(cos_alpha);
  },

  /**
   * returns true if the string ends with given suffix
   */
  endsWith: function(str, suffix) {
    return str.indexOf(suffix, str.length - suffix.length) !== -1;
  },
  
  send_response: function(id) {
    alert(id);
    return false;
  },
  
  loadGeoLiveSearch: function() {

    $.geosearchbox = {}
    
    $.extend(true, $.geosearchbox, {
      settings: {
        url: '/search',
        param: 'query',
        dom_id: '#results',
        delay: 100,
        loading_css: '#loading',
        show_results: function(data) {
          $($.geosearchbox.settings.dom_id).html(data)
        }
      },
      
      loading: function() {
        $($.geosearchbox.settings.loading_css).show()
      },
      
      resetTimer: function(timer) {
        if (timer) clearTimeout(timer)
      },
      
      idle: function() {
        $($.geosearchbox.settings.loading_css).hide()
      },
      
      process: function(terms) {
        var path = $.geosearchbox.settings.url.split('?'),
          query = [$.geosearchbox.settings.param, '=', terms].join(''),
          base = path[0], params = path[1], query_string = query
        
        if (params) query_string = [params.replace('&amp;', '&'), query].join('&')
        
        $.get([base, '?', query_string].join(''), function(data) {
          $.geosearchbox.settings.show_results(data);
        })
      },
      
      start: function() {
        $(document).trigger('before.searchbox')
        $.geosearchbox.loading()
      },
      
      stop: function() {
        $.geosearchbox.idle()
        $(document).trigger('after.searchbox')
      }
    })
    
    $.fn.geosearchbox = function(config) {
      var settings = $.extend(true, $.geosearchbox.settings, config || {})
      
      $(document).trigger('init.searchbox')
      $.geosearchbox.idle()
      
      return this.each(function() {
        var $input = $(this)
        
        $input
        .ajaxStart(function() { $.geosearchbox.start() })
        .ajaxStop(function() { $.geosearchbox.stop() })
        .keyup(function() {
          if ($input.val() != this.previousValue) {
            $.geosearchbox.resetTimer(this.timer)
            
            this.timer = setTimeout(function() {  
              $.geosearchbox.process($input.val())
            }, $.geosearchbox.settings.delay)
            
            this.previousValue = $input.val()
          }
        })
      })
    }
  },
  
  loadPaperLiveSearch: function() {

    $.papersearchbox = {}
    
    $.extend(true, $.papersearchbox, {
      settings: {
        url: '/search',
        param: 'query',
        dom_id: '#results',
        delay: 100,
        loading_css: '#loading',
        show_results: function(data) {
          $($.papersearchbox.settings.dom_id).html(data)
        }
      },
      
      loading: function() {
        $($.papersearchbox.settings.loading_css).show()
      },
      
      resetTimer: function(timer) {
        if (timer) clearTimeout(timer)
      },
      
      idle: function() {
        $($.papersearchbox.settings.loading_css).hide()
      },
      
      process: function(terms) {
        var path = $.papersearchbox.settings.url.split('?'),
          query = [$.papersearchbox.settings.param, '=', terms].join(''),
          base = path[0], params = path[1], query_string = query
        
        if (params) query_string = [params.replace('&amp;', '&'), query].join('&')
        
        $.get([base, '?', query_string].join(''), function(data) {
          $.papersearchbox.settings.show_results(data);
        })
      },
      
      start: function() {
        $(document).trigger('before.searchbox')
        $.papersearchbox.loading()
      },
      
      stop: function() {
        $.papersearchbox.idle()
        $(document).trigger('after.searchbox')
      }
    })
    
    $.fn.papersearchbox = function(config) {
      var settings = $.extend(true, $.papersearchbox.settings, config || {})
      
      $(document).trigger('init.searchbox')
      $.papersearchbox.idle()
      
      return this.each(function() {
        var $input = $(this)
        
        $input
        .ajaxStart(function() { $.papersearchbox.start() })
        .ajaxStop(function() { $.papersearchbox.stop() })
        .keyup(function() {
          if ($input.val() != this.previousValue) {
            $.papersearchbox.resetTimer(this.timer)
            
            this.timer = setTimeout(function() {  
              $.papersearchbox.process($input.val())
            }, $.papersearchbox.settings.delay)
            
            this.previousValue = $input.val()
          }
        })
      })
    }
  }
};


  

