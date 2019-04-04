#!/bin/bash

set -e

BOOTSTRAP_VERSION='4.2.1'
FONT_AWESOME_VERSION='4.7.0'
D3_JS_VERSION='4.13.0'
D3_JS_VERSIONv5='5.9.2'

if [ ! -d static/css ]; then
  mkdir static/css
fi
if [ ! -d static/js ]; then
  mkdir static/js
fi
if [ ! -d static/json ]; then
  mkdir static/json
fi

rm -rf temp
mkdir temp

mkdir temp/d3v5/

wget https://github.com/twbs/bootstrap/releases/download/v${BOOTSTRAP_VERSION}/bootstrap-${BOOTSTRAP_VERSION}-dist.zip -O temp/bootstrap${BOOTSTRAP_VERSION}.zip

wget https://github.com/FortAwesome/Font-Awesome/archive/v${FONT_AWESOME_VERSION}.zip -O temp/FONT_AWESOME_${FONT_AWESOME_VERSION}.zip
wget https://github.com/d3/d3/releases/download/v${D3_JS_VERSION}/d3.zip -O  temp/d3_${D3_JS_VERSION}.zip
wget https://github.com/d3/d3/releases/download/v${D3_JS_VERSIONv5}/d3.zip -O  temp/d3v5/d3_${D3_JS_VERSIONv5}.zip
wget https://github.com/FezVrasta/popper.js/archive/v1.14.3.zip -O temp/popper.zip

# dateRangePicker
wget https://github.com/moment/moment/archive/2.22.2.zip -O temp/moment_2.22.2.zip
wget https://github.com/longbill/jquery-date-range-picker/archive/v0.18.0.zip -O temp/daterangepicker_v0.18.0.zip


unzip temp/bootstrap${BOOTSTRAP_VERSION}.zip -d temp/
unzip temp/FONT_AWESOME_${FONT_AWESOME_VERSION}.zip -d temp/
unzip temp/d3_${D3_JS_VERSION}.zip -d temp/
unzip temp/d3v5/d3_${D3_JS_VERSIONv5}.zip -d temp/d3v5/
unzip temp/popper.zip -d temp/

unzip temp/moment_2.22.2.zip -d temp/
unzip temp/daterangepicker_v0.18.0.zip -d temp/

mv temp/bootstrap-${BOOTSTRAP_VERSION}-dist/js/bootstrap.min.js ./static/js/
mv temp/bootstrap-${BOOTSTRAP_VERSION}-dist/css/bootstrap.min.css ./static/css/
mv temp/bootstrap-${BOOTSTRAP_VERSION}-dist/css/bootstrap.min.css.map ./static/css/

mv temp/popper.js-1.14.3/dist/umd/popper.min.js ./static/js/
mv temp/popper.js-1.14.3/dist/umd/popper.min.js.map ./static/js/

mv temp/Font-Awesome-${FONT_AWESOME_VERSION} temp/font-awesome

rm -rf ./static/fonts/ ./static/font-awesome/
mv temp/font-awesome/ ./static/

mv temp/jquery-date-range-picker-0.18.0/dist/daterangepicker.min.css ./static/css/

mv temp/d3.min.js ./static/js/
cp temp/d3v5/d3.min.js ./static/js/d3v5.min.js

mv temp/moment-2.22.2/min/moment.min.js ./static/js/
mv temp/jquery-date-range-picker-0.18.0/dist/jquery.daterangepicker.min.js ./static/js/

rm -rf temp

JQVERSION="3.3.1"
wget http://code.jquery.com/jquery-${JQVERSION}.min.js -O ./static/js/jquery.js

#Ressources for dataTable
wget https://cdn.datatables.net/1.10.18/css/dataTables.bootstrap4.min.css -O ./static/css/dataTables.bootstrap.min.css
wget https://cdn.datatables.net/1.10.18/js/dataTables.bootstrap4.min.js -O ./static/js/dataTables.bootstrap.min.js
wget https://cdn.datatables.net/1.10.18/js/jquery.dataTables.min.js -O ./static/js/jquery.dataTables.min.js

#Update json
wget https://raw.githubusercontent.com/D4-project/architecture/master/format/type.json -O ./static/json/type.json

rm -rf temp
