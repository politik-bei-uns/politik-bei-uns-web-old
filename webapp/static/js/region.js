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
              region_data = {
                'id': event.data.region.id,
                'name': event.data.region.name,
                'lat': event.data.region.lat,
                'lon': event.data.region.lon,
                'zoom': event.data.region.zoom
              }
              OpenRIS.region = event.data.region;
              $('#region-choice').html('');
              $('#region-question').css({'display': 'block'});
              update_region();
              if (typeof(OpenRIS.post_region_change) == 'function') {
                OpenRIS.post_region_change();
              }
            }
          )
          .appendTo('#region-choice');
      });
    });
  });
});

function update_region() {
  // update region name
  $('#region-current').text(OpenRIS.region.name);
  // update street description
  if (OpenRIS.region.type == 1)
    $('#address-label').text('Straße:');
  else
    $('#address-label').text('Straße und Stadt:');
  // update search examples
  if ($('#search-examples')) {
    $('#search-examples').html('');
    $('#search-examples').append(document.createTextNode('Beispiele: '));
    $.each(OpenRIS.region.keyword, function(id, keyword){
      $('<a/>')
        .text(keyword)
        .attr({'href': '/suche/?q=' + encodeURI(keyword)})
        .appendTo('#search-examples');
      if (OpenRIS.region.keyword.length > id + 1)
        $('#search-examples').append(document.createTextNode(', '));
    });
  }
}