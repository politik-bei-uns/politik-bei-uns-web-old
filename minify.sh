#!/bin/bash

# css
/usr/bin/yui-compressor /srv/www/ris-web/webapp/static/css/style.css -o /srv/www/ris-web/webapp/static/css/style.min.css
/usr/bin/yui-compressor /srv/www/ris-web/webapp/static/css/leaflet.css -o /srv/www/ris-web/webapp/static/css/leaflet.min.css

# js
/usr/bin/yui-compressor /srv/www/ris-web/webapp/static/js/ajaxq.js -o /srv/www/ris-web/webapp/static/js/ajaxq.min.js
/usr/bin/yui-compressor /srv/www/ris-web/webapp/static/js/file_details.js -o /srv/www/ris-web/webapp/static/js/file_details.min.js
/usr/bin/yui-compressor /srv/www/ris-web/webapp/static/js/map.js -o /srv/www/ris-web/webapp/static/js/map.min.js
/usr/bin/yui-compressor /srv/www/ris-web/webapp/static/js/paper_details.js -o /srv/www/ris-web/webapp/static/js/paper_details.min.js
/usr/bin/yui-compressor /srv/www/ris-web/webapp/static/js/region.js -o /srv/www/ris-web/webapp/static/js/region.min.js
/usr/bin/yui-compressor /srv/www/ris-web/webapp/static/js/script.js -o /srv/www/ris-web/webapp/static/js/script.min.js
/usr/bin/yui-compressor /srv/www/ris-web/webapp/static/js/search.js -o /srv/www/ris-web/webapp/static/js/search.min.js

