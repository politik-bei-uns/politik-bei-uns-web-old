$(document).ready(function(){
  
  var thumbs_data; // speichert Details zu den Thumbs aller Attachments

  /**
   * Zoomt die Thumbnail-Darstellung von Höhe 300 auf 800
   */
  function zoomThumbsClick(evt) {
    //console.log('zoomThumbs', evt.data);
    evt.preventDefault();
    // alle img src-Attribute umschreiben
    var full_width = 0;
    $('#filepreview-' + evt.data.file_id + ' img').each(function(index){
      var img = $(this);
      var target_height = 800;
      var target_width = img.data('width800');
      full_width += target_width + 10;
      img.animate({width: target_width, height: target_height}, {duration: 400, easing: 'swing'});
      img.attr('src', img.attr('src').replace('/300/', '/800/'));
      img.parent('a').replaceWith(img);
    });
    // Breite des Thumbs-Containers zuerst setzen, ohne Animation
    $('#filepreview-' + evt.data.file_id + ' .thumbsinner').css({width: full_width});
    // Animation zur Vergroesserung des Thumbnails-Containers
    $('#filepreview-' + evt.data.file_id + ' .thumbs').animate({height: '825px'}, {duration: 300, easing: 'swing'});
    $('#filepreview-' + evt.data.file_id + ' .thumbsinner').animate({height: '810px'}, {duration: 300, easing: 'swing'});
  }

  /**
   * Erweitert die Vorschaubilder-Anzeige, so dass bei Klick die nächst
   * groessere Stufe angezeigt wird.
   */
  function enhanceThumbnails() {
    $('img.thumb').each(function(i, item){
      var url_parts = $(item).attr('src').split('/');
      var filename = url_parts[(url_parts.length - 1)];
      var page = filename.split('.')[0];
      var height = url_parts[(url_parts.length - 2)];
      var file_id = url_parts[(url_parts.length - 3)];
      $(this).wrap('<a href="#"></a>');
      $(this).parent().click({
        file_id: file_id,
        height: height,
        index: (page - 1)
      }, zoomThumbsClick);
    });
  }

  enhanceThumbnails();
});
    


