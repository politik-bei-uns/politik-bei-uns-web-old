/*
Copyright (c) 2012 - 2015, Marian Steinbach, Ernesto Ruge
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

$(document).ready(function(){
  
  OpenRIS.regionLoad()

  /********** REGION **********/
  
  // register post region change actions
  OpenRIS.post_region_change = function() {
    // live search box
    $.geosearchbox.settings.url = '/api/locations?r=' + OpenRIS.region.id;
    $.papersearchbox.settings.url = '/api/papers-live?r=' + OpenRIS.region.id;
    
    map.setView(new L.LatLng(OpenRIS.region.lat, OpenRIS.region.lon), OpenRIS.region.zoom).addLayer(backgroundLayer);
    window.history.pushState(String(Date.now()), document.title, "/?r=" + OpenRIS.region.id);
    
    // update search examples
    if ($('#search-examples')) {
      $('#search-examples').html('');
      $('#search-examples').append(document.createTextNode('Beispiele: '));
      $.each(OpenRIS.region.keyword, function(id, keyword){
        $('<a/>')
          .text(keyword)
          .attr({'href': '/suche?r=' + OpenRIS.region.id + '&q=' + encodeURI(keyword)})
          .appendTo('#search-examples');
        if (OpenRIS.region.keyword.length > id + 1)
          $('#search-examples').append(document.createTextNode(', '));
      });
    }
    $('#qinput-region').val(OpenRIS.region.id);
    changePositionTransform();
  }
  
  /********** MAP **********/
  
  var map = new L.Map('map', {});
  var markerLayerGroup = new L.LayerGroup();
  map.addLayer(markerLayerGroup);
  
  var backgroundLayer = new L.TileLayer(CONF.mapTileUrlSchema, {
      maxZoom: CONF.mapTileMaxZoom,
      minZoom: CONF.mapTileMinZoom,
      attribution: CONF.mapTileAttribution
    });
  
  var sessionData = {}; // user session data
  
  var lastLocationEntry = ''; // die letzte vom User eingegebene Strasse
  
  map.setView(new L.LatLng(OpenRIS.region.lat, OpenRIS.region.lon), OpenRIS.region.zoom).addLayer(backgroundLayer);
  
  
  /********** GEO SEARCH **********/
  
  if (search_data.address) {
    $('#address').val(search_data.address);
    handleLocationInput();
  }
  
  OpenRIS.loadGeoLiveSearch();
  $('<p>').attr('id', 'address-live').css({'top': $('#address').height(), 'width': $('#address').width()}).appendTo($('#address-box'));
  
  $('#address').geosearchbox({
    'url': '/api/locations?r=' + OpenRIS.region.id,
    'param': 'l',
    'show_results': function(result) {
      result = result['response'];
      result_html = '<ul>';
      if (result.length) {
        $('#address-live').css({'display': 'block'});
        for (i = 0; i < result.length; i++) {
          result_html += '<li data-point="' + result[i]['point'] + '\">' + result[i]['name'] + ', ';
          if (result[i].hasOwnProperty('postalcode'))
            result_html += result[i]['postalcode'] + ' ';
          result_html += result[i]['bodyName'] + '</li>';
        }
        result_html += '</ul>';
        $('#address-live').html(result_html);
        $('#address-live li').click(function() {
          point = $(this).attr('data-point');
          point = point.split(',');
          search_data['lat'] = point[0]
          search_data['lon'] = point[1]
          $('#address').val($(this).text());
          $('#address-live').css({'display': 'none'});
          $('#position-prompt-submit').trigger('click');
        });
      }
      else
        $('#address-live').css({'display': 'none'});
    }
  });
  
  
  var locationPrompt = $('#position-prompt');
  if (locationPrompt.length > 0) {
    $('#address').focus();
  }
  
  // handle user data input
  $('#position-prompt-submit').click(function(evt){
    evt.preventDefault();
    handleLocationInput();
  });
  
  $('#position-prompt-form').submit(function(evt){
    evt.preventDefault();
    handleLocationInput();
  });
  
  $('#address').keydown(function(evt){
    // Enter abfangen
    if (evt.keyCode == 13) {
      evt.preventDefault();
      if ($('#address-live li.highlighted').length) {
        $('#address-live li.highlighted').trigger('click');
      }
      else
        $('#position-prompt-submit').trigger('click');
    }
    // Pfeil hoch abfangen
    if (evt.keyCode == 38) {
      evt.preventDefault();
      if ($('#address-live li.highlighted').length) {
        before = $('#address-live li.highlighted').prev();
        if (before.length) {
          $('#address-live li.highlighted').removeClass('highlighted');
          before.addClass('highlighted');
        }
      }
    }
    // Pfeil runter abfangen
    if (evt.keyCode == 40) {
      evt.preventDefault();
      if ($('#address-live li.highlighted').length) {
        next = $('#address-live li.highlighted').next();
        if (next.length) {
          $('#address-live li.highlighted').removeClass('highlighted');
          next.addClass('highlighted');
        }
      }
      else
        $('#address-live li').first().addClass('highlighted');
    }
  });
  
  $('#position-prompt-form').focusout(function() {
    $('#address-live').fadeOut(250);
  });
  
  
  function handleSessionResponse(data){
    sessionData = data.response;
  }
  
  function handleLocationInput() {
    resetMap();
    $('#position-prompt-submit');
    $('#position-prompt .error').remove();
    $('#location-prompt-resultchoice').remove();
    var address = $('#address').val();
    if (!search_data['lat'] || !search_data['lon']) {
      $.get('/api/locations?l=' + address, function(data) {
        if (data['response'].length) {
          var point = data['response'][0]['point'].split(',');
          search_data['lat'] = point[0];
          search_data['lon'] = point[1];
          location_string = data['response'][0]['name'] + ', ';
          if (data['response'][0]['postalcode'])
            location_string += data['response'][0]['postalcode'] + ' ';
          location_string += data['response'][0]['bodyName'] + ' ';
          $('#address').val(location_string);
          search_data['address'] = location_string;
          setUserPosition(parseFloat(search_data['lat']), parseFloat(search_data['lon']));
          sessionParams = {
            'address': address,
            'lat': search_data['lat'],
            'lon': search_data['lon']
          };
          OpenRIS.session(sessionParams, handleSessionResponse);
        }
        else {
          //error
        }
      });
    }
    else {
      setUserPosition(parseFloat(search_data['lat']), parseFloat(search_data['lon']));
      sessionParams = {
        'address': address,
        'lat': search_data['lat'],
        'lon': search_data['lon']
      };
      OpenRIS.session(sessionParams, handleSessionResponse);
    }
  }
  
  function clearMap() {
    markerLayerGroup.clearLayers();
  }
  
  function resetMap() {
    clearMap();
    map.setView(new L.LatLng(OpenRIS.region.lat, OpenRIS.region.lon), OpenRIS.region.zoom);
  }
  
  function handleChangePositionClick(evt) {
    evt.preventDefault();
    changePositionTransform();
  }
  
  function changePositionTransform() {
    window.history.pushState(String(Date.now()), document.title, "/?r=" + OpenRIS.region.id);
    $('#map-claim').remove();
    $('#position-prompt').show();
    $('#address').focus();
    $('#address').select();
    search_data = {
      'address': null
    };
    sessionParams = {
      'address': null,
      'lat': null,
      'lon': null
    };
    OpenRIS.session(sessionParams, handleSessionResponse);
    resetMap();
  }
  
  function setUserPosition(lat, lon) {
    // Header-Element umbauen
    var streetString = $('#address').val();
    if (streetString === '') {
      streetString = sessionData.location_entry;
    }
    // Set new URL
    window.history.pushState(String(Date.now()), document.title, "/?r=" + OpenRIS.region.id + '&l=\"' + streetString + '\"');
    
    var changeLocationLink = $(document.createElement('span')).text(streetString).attr({'id': 'map-claim-street'});
    var newSearchLink = $(document.createElement('a')).text('Neue Suche').attr({'href': '#', 'class': 'awesome extrawide'}).css('margin-left', '20px').click(handleChangePositionClick);
    var article = '';
    if (OpenRIS.endsWith(streetString, 'straße') || OpenRIS.endsWith(streetString, 'gasse')) {
      article = 'die';
    }
    var mapClaim = '<div id="map-claim"><span>Das passiert rund um ' + article + ' </span></div>';
    $('#position-prompt').slideUp().after(mapClaim);
    $('#map-claim').append(changeLocationLink).append(newSearchLink);
    // Karte umbauen
    clearMap();
    var userLocation = new L.LatLng(lat, lon),
      radius = 500;
    map.setView(userLocation, 14);
    var circleOptions = {color: '#97c66b', opacity: 0.7, fill: false, draggable: true};
    var outerCircle = new L.Circle(userLocation, radius, circleOptions);
    var innerDot = new L.Circle(userLocation, 20, {fillOpacity: 0.9, fillColor: '#97c66b', stroke: false, draggable: true});
    var positionPopup = L.popup()
      .setLatLng(userLocation)
      .setContent('<p>Dies ist der Suchmittelpunkt für die Umkreissuche.</p>');
    outerCircle.on('click', function(e){
      map.openPopup(positionPopup);
    });
    outerCircle.on('drag', function(e){
      console.log(e);
    });
    innerDot.on('click', function(e){
      map.openPopup(positionPopup);
    });
    markerLayerGroup.addLayer(outerCircle);
    markerLayerGroup.addLayer(innerDot);
    var streets = [];
    // Strassen aus der Umgebung abrufen
    OpenRIS.streetsForPosition(OpenRIS.region.id, lat, lon, radius, function(data){
      $.each(data.response, function(street_name, street) {
        if (street.paper_count) {
          $.each(street.nodes, function(nodes_id, nodes){
            var points = [];
            $.each(nodes, function(node_id, node){
              points.push(new L.LatLng(
                node[1], node[0]
              ));
            });
            var markerHtml = '<p><b><a href="/suche?r=' + OpenRIS.region.id + '&q=&quot;' + street_name + '&quot;">' + street_name + ': ' + street.paper_count + ' Treffer</a></b>';
            if (street.paper_publishedDate && street.paper_name)
              markerHtml += '<br/>Der jüngste Treffer vom ' + OpenRIS.formatIsoDate(street.paper_publishedDate) + ' (' + street.paper_name + ')';
            markerHtml += '</p>';
            var polyline = L.polyline(points, {color: '#ff0909'});
            polyline.bindPopup(markerHtml);
            markerLayerGroup.addLayer(polyline);
          });
        }
      });
    });
  }
  
  /********** KEYWORD SEARCH **********/
  
  $('#qinput-submit').click(function(evt){
    evt.preventDefault();
    $('#search-form').trigger('submit');
  });
  
  OpenRIS.loadPaperLiveSearch();
  $('<p>').attr('id', 'qinput-live').css({'top': $('#qinput').height(), 'width': $('#qinput').width()}).appendTo($('#qinput-box'));
  
  $('#qinput').papersearchbox({
    'url': '/api/papers-live?r=' + OpenRIS.region.id,
    'param': 'p',
    'show_results': function(result) {
      result = result['response'];
      result_html = '<ul>';
      if (result.length) {
        $('#qinput-live').css({'display': 'block'});
        for (i = 0; i < result.length; i++) {
          result_html += '<li data-q="' + result[i]['name'] + '\">' + result[i]['name'] + ' (' + result[i]['count'] + ')</li>';
        }
        result_html += '</ul>';
        $('#qinput-live').html(result_html);
        $('#qinput-live li').click(function() {
          search_string = $(this).attr('data-q');
          $('#qinput').val(search_string);
          $('#qinput-submit').trigger('click');
        });
      }
      else
        $('#qinput-live').css({'display': 'none'});
    }
  });
  
  
  $('#qinput').keydown(function(evt){
    // Enter abfangen
    if (evt.keyCode == 13) {
      evt.preventDefault();
      if ($('#qinput-live li.highlighted').length) {
        $('#qinput-live li.highlighted').trigger('click');
      }
      else
        $('#qinput-submit').trigger('click');
    }
    // Pfeil hoch abfangen
    if (evt.keyCode == 38) {
      evt.preventDefault();
      if ($('#qinput-live li.highlighted').length) {
        before = $('#qinput-live li.highlighted').prev();
        if (before.length) {
          $('#qinput-live li.highlighted').removeClass('highlighted');
          before.addClass('highlighted');
        }
      }
    }
    // Pfeil runter abfangen
    if (evt.keyCode == 40) {
      evt.preventDefault();
      if ($('#qinput-live li.highlighted').length) {
        next = $('#qinput-live li.highlighted').next();
        if (next.length) {
          $('#qinput-live li.highlighted').removeClass('highlighted');
          next.addClass('highlighted');
        }
      }
      else
        $('#qinput-live li').first().addClass('highlighted');
    }
  });
  
});
