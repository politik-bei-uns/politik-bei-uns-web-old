/*
Copyright (c) 2012 - 2015, Marian Steinbach, Ernesto Ruge
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

$(document).ready(function() {
	OpenRIS.region.id = region_data['id'];
	OpenRIS.region.name = region_data['name'];
	OpenRIS.region.type = region_data['type'];
	OpenRIS.region.lat = region_data['lat'];
	OpenRIS.region.lon = region_data['lon'];
  OpenRIS.regionLoad();
  
  if (typeof openris_search_settings != undefined) {
    OpenRIS.search_params = OpenRIS.deepCopy(openris_search_settings);
    OpenRIS.search_params['output'] = 'facets';
    runSearch();
  }
  
  function runSearch() {
    // modify URL
    url = Array();
    $.each( OpenRIS.search_params, function( key, value ) {
      if (value)
		url.push(key + '=' + String(value).replace(/&#34;/g, "\""));
    });
    window.history.pushState(String(Date.now()), document.title, "/suche?" + url.join('&'));
    // run search
    $('#search .result').empty();
    $('#search .result').append('<div class="loading big outer"><div class="loading big inner">Suche...</div></div>');
    OpenRIS.search(
      OpenRIS.search_params,
      function(data) {
        $('#search .result').empty();
        $('#facets').remove();
        if (data.status == 0) {
          if (typeof data.response.facets != 'undefined') {
            $('#search-form').after('<div id="facets" class="content middle"></div>');
            displaySearchResultFacets(data.response.facets, data.request, '#facets');
          }
          displaySearchResult(data);
          displayPagerWidget(data.response.numhits, openris_search_settings.ppp, data.response.start, '#search .result');
          if (data.response.numhits > 1) {
            displaySortWidget(data.request, '#search .result h3');
          }
        } else {
          displaySearchErrorMessage();
        }
      }
    );
  }
  
  $('#search-submit').click(function(evt){
    evt.preventDefault();
    OpenRIS.search_params['start'] = 0;
    OpenRIS.search_params['q'] = $('#qinput').val();
    runSearch();
  });
  
  $('#searchform').submit(function(evt) {
    evt.preventDefault();
    OpenRIS.search_params['start'] = 0;
    OpenRIS.search_params['q'] = $('#qinput').val();
    runSearch();
  });
  
  // register post region change actions
  OpenRIS.post_region_change = function() {
    OpenRIS.search_params['r'] = OpenRIS.region.id;
    OpenRIS.search_params['start'] = 0;
    OpenRIS.search_params['q'] = $('#qinput').val();
    runSearch();
  }
  
  /*
  $('#qinput').makeAutocompleteSearchField({
		formSelector: '#searchform',
		inputSelector: '#qinput',
	});
  */
  
  /**
   * Sort a facet object {key: value, ...}
   *
   * @param   data  Object to sort
   * @param   String  Either "key" or "value"
   */
  function sortFacet(data, field) {
    var newlist = [];
    for (var i in data)
      newlist.push({key: i, value: data[i]});
    if (field == 'key')
      newlist.sort(sortCompareByKey);
    else if (field == 'value')
      newlist.sort(sortCompareByValue);
    return newlist;
  }
  
  function sortCompareByKey(a, b) {
	  return b.key - a.key;
  }
  
  function sortCompareByValue(a, b) {
	  return b.value - a.value;
  }
  
  function displaySearchResultFacets(facets, query, targetSelector) {
    if (typeof facets != 'undefined') {
      //create obj of string
      fq = query.fq
      var rest = true
      x = 0
      result = new Object();
      while (rest) {
        y = fq.indexOf(":", x);
        if (y == -1)
          break
        temp = fq.substring(x, y);
        x = y + 1
        if (fq.substring(x, x+5) == "&#34;") {
          y = fq.indexOf("&#34;", x+5);
          if (y == -1)
            break
          result[temp] = fq.substring(x+5, y)
          x = y + 6;
          if (x > fq.length)
            break
        }
        else {
          y = fq.indexOf(";", x);
          if (y == -1) {
            result[temp] = fq.substring(x, fq.length);
            break
          }
          else {
            result[temp] = fq.substring(x, y);
            x = y + 1
          }
        }
      }
      
      // paperType facet
      paperType_facet = createSearchResultFacet('paperType', facets.paperType, 'Typ', 'value', result);
      $(targetSelector).append(paperType_facet);
      bodyName_facet = createSearchResultFacet('bodyName', facets.bodyName, 'Körperschaft', 'value', result);
      $(targetSelector).append(bodyName_facet);
      // gremium facet
      //organization_facet = createSearchResultFacet('organization', facets.organization, 'Gremium', 'value', result, true);
      //$(targetSelector).append(organization_facet);
      // schlagwort facet
      //term_facet = createSearchResultFacet('term', facets.term, 'Stichwort', 'value', query.fq, true);
      //$(targetSelector).append(term_facet);
      // schlagwort datum
      publishedDate_facet = createSearchResultFacet('publishedDate', facets.publishedDate, 'Erstellungsdatum', '', result, true);
      $(targetSelector).append(publishedDate_facet);
    }
  }
  
  /**
   * Creates a search result facet and returns the HTMLElement object
   *
   * @param   String  name    Name of the facet
   * @param   Object  data    facet data object, unsorted
   * @param   String  headline  Header to display
   * @param   String  sortField   'key' or 'value'
   * @param   String  fq      filter query currently applied
   * @param   Boolean filterIds   True to filter out numeric ids in front of labels, false to leave as is
   */
  function createSearchResultFacet(name, data, headline, sortField, fq, filterIds) {
    var facet_data = sortFacet(data, sortField);
    var facet = $(document.createElement('div')).attr('class', 'facet ' + name);
    var list = $(document.createElement('ul')).attr('class', 'facet');
    // currently filtered by this facet
    if (fq[name]) {
      var label = fq[name];
      if (name=='publishedDate')
        label=OpenRIS.monthstr[label.substr(5,7)] + " " + label.substr(0,4);
      if (filterIds == true) {
        label = label.replace(/^[0-9]+\s+/, '');
      }
      var sqs = ''
      for (var i in fq) {
        if (i != name) {
          if (sqs)
            sqs += ';';
          sqs += i + ':' + quoteFacetValue(fq[i]);
        }
        
      }
      if (!sqs)
        sqs = null
      // generate list element
      $('<li>').attr('class', 'current').append(
			$('<a>').attr('href', '/suche?'+ searchQueryString({fq: sqs}))
				.attr('title', 'Diese Einschränkung aufheben')
				.click({'sqs': sqs}, function(evt) {
					evt.preventDefault();
					if (evt.data.sqs)
						OpenRIS.search_params['fq'] = evt.data.sqs.replace(/\"/g, "&#34;");
					else
						OpenRIS.search_params['fq'] = null;
					runSearch();
				})
				.append($('<span>').attr('class', 'facetdel').text('✕'))
				.append($('<span>').attr('class', 'facetlabel').text(label.replace(/&#34;/g, "").replace(/\"/g, ""))))
				.appendTo(list);
    }
    else {
      for (var i in facet_data) {
        var label = facet_data[i].key;
        if (filterIds == true)
          label = label.replace(/^[0-9]+\s+/, '');
        if (name=='publishedDate')
          label=OpenRIS.monthstr[label.substr(5,7)] + " " + label.substr(0,4);
        if (!OpenRIS.search_params['fq'])
          sqs = name + ':' + quoteFacetValue(facet_data[i].key);
        else
          sqs = OpenRIS.search_params['fq'] + ';' + name + ':' + quoteFacetValue(facet_data[i].key);
				// generate list element
				list_element = $('<li>').append(
					$('<a>').attr('href', '/suche?'+ searchQueryString({fq: sqs}))
						.attr('title', 'Auswahl einschränken')
						.click({'sqs': sqs}, function(evt) {
							evt.preventDefault();
							OpenRIS.search_params['fq'] = evt.data.sqs.replace(/\"/g, "&#34;");
							runSearch();
						})
						.append($('<span>').attr('class', 'facetlabel').text(label.replace(/&#34;/g, "").replace(/\"/g, "")))
						.append(' ')
						.append($('<span>').attr('class', 'num').text(facet_data[i].value)))
				if (name=='publishedDate')
					list_element.prependTo(list);
				else
					list_element.appendTo(list);
        //list.append('<li><a href="/suche?'+ (searchQueryString({fq: sqs })) +'"><span class="facetlabel">'+ label +'</span> <span class="num">'+ facet_data[i].value +'</span></a></li>');
      }
    }
    facet.append('<div class="header">'+ headline +'</div>');
    facet.append(list);
    return facet;
  }
  
  /**
   * Packt Facetten-Werte in Anführungszeichen, wenn sie ein Leerzeichen enthalten
   */
  function quoteFacetValue(str) {
    if (str.indexOf(' ') != -1) {
      str = '"' + str + '"';
    }
    return str;
  }
  
  function displaySearchErrorMessage(){
    $('#search .result').append('<h2>Fehler bei der Suche</h2><p>Es ist ein unerwarteter Fehler aufgetreten. Bitte probier es noch einmal.</p><p>Wenn das Problem weiterhin besteht, bitte kopiere den Inhalt der Adresszeile in eine E-Mail und sende sie an <a href="kontakt@politik-bei-uns.de">kontakt@politik-bei-uns.de</a>. Vielen Dank!</p>');
  }
  
  function displaySearchResult(data) {
    var result = $('#search .result');
    
    // headline
    $('h1').text(data.response.numhits + ' gefundene Dokumente');
    if (data.response.numhits > 0) {
      var subheadline = $(document.createElement('h3'));
      subheadline.text('Seite ' + (Math.floor(data.response.start / openris_search_settings.ppp)+1) + ' von ' + (Math.ceil(data.response.numhits / openris_search_settings.ppp)));
      result.append(subheadline);
    }
    
    // results ol
    var resultlist = $(document.createElement('ol'));
    resultlist.attr('start', data.response.start + 1);
    result.append(resultlist);
    for (var i in data.response.result) {
      var item = $(document.createElement('li')).attr('class','resultitem');
      resultlist.append(item);
      var link = $(document.createElement('a')).attr('href', '/paper/' + data.response.result[i]['id']);
      item.append(link);
      var title = $(document.createElement('span')).attr('class','title').html(itemName(data.response.result[i]));
      link.append(title);
      var metainfo = $(document.createElement('span')).attr('class','metainfo');
      metainfo.text(createMetaInfoText(data.response.result[i]));
      link.append(metainfo);
      if (data.response.result[i]['fileFulltext']) {
        var snippet = $(document.createElement('p')).attr('class','snippet');
        snippet.html(createSnippet(data.response.result[i]));
        item.append(snippet);
      }
    }
  }
  
  /**
   * Generate the output title and apply, if possible, search term highlighting
   */
  function itemName(paper) {
    if (paper.name !== '') {
      if (typeof paper.highlighting != 'undefined' &&
        typeof paper.highlighting.title != 'undefined') {
        return paper.highlighting.title;
      }
      return paper.name;
    }
    else {
      return 'Dokument ohne Name';
    }
  }
  
  function createMetaInfoText(document) {
    return document.paperType + ' aus ' + document.bodyName + ' vom ' + OpenRIS.formatIsoDate(document.publishedDate)
  }
  
  function createSnippet(document) {
    return '... ' + document.fileFulltext + ' ...'
  }
  
  /**
   * @param   numhits   Number of items in search result
   * @param   rows  Number of rows per page
   * @param   start   Current offset
   */
  function displayPagerWidget(numhits, rows, start, targetSelector) {
    var pager = $(document.createElement('div'));
    pager.attr('class', 'pager');
    $(targetSelector).append(pager);
    // previous page
    if (start > 0) {
      $('<a>').attr('class', 'awesome extrawide paging back')
	.attr('href', '/suche?'+ searchQueryString({start: (start - OpenRIS.search_params['ppp'])}))
	.text('← Seite zurück')
	.click(function(evt) {
	  evt.preventDefault();
	  OpenRIS.search_params['start'] = start - OpenRIS.search_params['ppp'];
	  runSearch();
	})
	.appendTo(pager);
    }
    pager.append(' ');
    // next page
    if (numhits > (start + rows)) {
      $('<a>').attr('class', 'awesome extrawide paging next')
	.attr('href', '/suche?'+ searchQueryString({start: (start + OpenRIS.search_params['ppp'])}))
	.text('Seite weiter →')
	.click(function(evt) {
	  evt.preventDefault();
	  OpenRIS.search_params['start'] = start + OpenRIS.search_params['ppp'];
	  runSearch();
	})
	.appendTo(pager);
    }
  }
  
  /**
   * Kontrollelement zur Anzeige der aktuellen Sortierung und zum
   * Aendern der Sortierung
   *
   * @param   Object  data         Request-Parameter
   * @param   String  targetSelector   jQuery Selector zur Bestimmgung des DOM-Elements für die Ausgabe
   */
  function displaySortWidget(data, targetSelector) {
    var widget = $(document.createElement('span'));
    widget.attr('class', 'sort');
    $(targetSelector).append(widget);
    widget.append(' &ndash; sortiert nach ');
    var first = true;
    var sortOptions = {
      'score:desc': 'Relevanz',
      'publishedDate:desc': 'Datum: neuste zuerst',
      'publishedDate:asc': 'Datum: älteste zuerst'
    };
    for (var o in sortOptions) {
      if (first)
	first = false;
      else
	widget.append(' | ');
      if (data.sort == o) {
	$('<b>').text(sortOptions[o]).appendTo(widget);
      } else {
	$('<a>').attr('href', '/suche?'+ searchQueryString({start: 0, sort: o}))
	  .text(sortOptions[o])
	  .click({'o': o}, function(evt) {
	    evt.preventDefault();
	    OpenRIS.search_params['start'] = 0;
	    OpenRIS.search_params['sort'] = evt.data.o;
	    runSearch();
	  })
	.appendTo(widget);
      }
    }
  }
  
  /**
   * creates a search query string for a modified search.
   * Takes parameters from openris_search_settings and overrides parameters
   * given in
   * @param   overwrite
   */
  function searchQueryString(overwrite) {
    var settings = OpenRIS.deepCopy(OpenRIS.search_params);
    for (var item in overwrite) {
      if (overwrite[item] == null 
        || typeof overwrite[item] == 'undefined') {
        delete settings[item];
      } else {
        settings[item] = overwrite[item];
      }
      
    }
    settings = OpenRIS.processSearchParams(settings);
    var parts = []
    for (var item in settings) {
      parts.push(item + '=' + encodeURI(settings[item]));
    }
    return parts.join('&');
  }
});

/**
 * Search field autocompletion
 * Author: Marian Steinbach <marian@sendung.de>
 
(function($){
	var displayAutocompleteTerms = function(rows, options) {
		$(options.flyoutSelector).empty();
		// display autocomplete suggestions
		for (var key in rows) {
			var newrow = $('<a class="autocompleterow" href="#">' + rows[key][0] + '</a>');
			newrow.click(function(event){
				event.stopPropagation();
				event.preventDefault();
				submitSearch($(this).text());
			});
			$(options.flyoutSelector).append(newrow);
		}
	};
	$.fn.extend({
		makeAutocompleteSearchField: function(options) {
			// option defaults
			var defaults = {
				keyWaitTime: 250,
				preventEnterSubmit: false,
				inputSelector: '#queryinput',
				flyoutSelector: '#searchflyout',
				yoffset: 5,
				numAutocompleteRows: 10
			};
			var options =  $.extend(defaults, options);
			var call;
			if ($('#searchflyout').length == 0) {
				$('body').append('<div id="searchflyout"></div>');
			}
			return this.each(function() {
				var o = options;
				var obj = $(this);
				var selectedAutocomplete, selectedItem;
				handleQueryStringChange = function() {
					querystring = $(obj).val();
					if (querystring == '') {
						hideFlyout();
					} else {
						$.getJSON('/api/terms', {prefix: querystring}, function(data){
							displayAutocompleteTerms(data, options);
							showFlyout();
						});
					}
					selectedAutocomplete = undefined;
					selectedItem = undefined;
				};
				showFlyout = function() {
					var x = obj.offset().left;
					var y = obj.offset().top + obj.height() + o.yoffset;
					var w = obj.width();
					$(o.flyoutSelector).css({top: y, left: x, 'min-width': w});
					$(o.flyoutSelector).show();
					$('html').click(function() {
						hideFlyout();
					});
				};
				submitSearch = function(term) {
					hideFlyout();
					updateSearchField(term);
					$(obj).focus();
					$(o.formSelector).submit();
				};
				hideFlyout = function() {
					$(o.flyoutSelector).hide();
				};
				setSelection = function(delta) {
					if (delta > 0) {
						if (typeof selectedAutocomplete == 'undefined') {
							selectedAutocomplete = 0;
						} else {
							selectedAutocomplete = Math.min(selectedAutocomplete + 1, o.numAutocompleteRows - 1);
						}
					} else {
						if (selectedAutocomplete == 0) {
							selectedAutocomplete = undefined;
						} else if (typeof selectedAutocomplete != 'undefined') {
							selectedAutocomplete -= 1;
						}
					}
					$(o.flyoutSelector).find('.selected').removeClass('selected');
					if (typeof selectedAutocomplete != 'undefined') {
						$($(o.flyoutSelector).find('.autocompleterow')[selectedAutocomplete]).addClass('selected');
					}
				};
				selectCurrentItem = function() {
					// submits the search or goes to linked item
					if (typeof selectedAutocomplete != 'undefined') {
						submitSearch( $($(o.flyoutSelector).find('.selected')).text());
					}
				};
				updateSearchField = function(term){
					$(obj).val(term);
				};
				$(obj).keydown(function(event){
					if (event.keyCode == 40 // down
						|| event.keyCode == 38 // up
						) {
						event.preventDefault();
					}
				});
				$(obj).keyup(function(event){
					event.preventDefault();
					if (event.keyCode == 40) {
						// arrow down
						setSelection(1);
						return false;
					} else if (event.keyCode == 38) {
						// arrow up
						setSelection(-1);
						return false;
					} else if (event.keyCode == 13) {
						// return or space key
						window.clearTimeout(call);
						selectCurrentItem();
					} else 	if (event.keyCode == 27) {
						// esc
						hideFlyout();
					} else if (
						event.keyCode == 91 // cmd left
						|| event.keyCode == 93 // cmd right
						|| event.keyCode == 18 // alt
						|| event.keyCode == 16 // shift
						|| event.keyCode == 20 // shift lock
						|| event.keyCode == 37 // arrow left
						|| event.keyCode == 39 // arrow right
						) {
						// do nothing!
					} else {
						window.clearTimeout(call);
						call = window.setTimeout(handleQueryStringChange, o.keyWaitTime);
					}
				});
				$(o.formSelector).submit(function(){
					hideFlyout();
				});
			});
		}
	});
})(jQuery);
*/