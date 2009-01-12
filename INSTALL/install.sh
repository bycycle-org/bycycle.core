#!/bin/bash
#
# Install byCycle dependencies from source.
# 2007-03-10
#
# Download source distributions and unpack them; configure, make, and
# install; perform post-install configuration.


echo
echo 'Starting installation of byCycle dependencies (from source)...'
echo


echo 'Warning! This script has the potential to do very destructive things!'
echo -n 'Continue? [yes/N] '
read go
if [ "$go" != "yes" ]; then 
	echo 'Aborted.'
	exit
fi
echo


USR=bycycle
BASE_DIR=/home/${USR}
SRC_DIR=${BASE_DIR}/src
INSTALL_BIN_DIR=${BASE_DIR}/INSTALL
PREFIX=/usr/local
CPREFIX="--prefix=${PREFIX}"
udo="sudo -u ${USR}"
udopg="sudo -u postgres"
uconfigure="$udo ./configure ${CPREFIX}"
umake="$udo make"
ugmake="$udo gmake"
py="$PREFIX/bin/python2.5"
echo USR $USR
echo BASE_DIR $BASE_DIR
echo SRC_DIR $SRC_DIR
echo INSTALL_BIN_DIR $INSTALL_BIN_DIR
echo PREFIX $PREFIX
echo CPREFIX $CPREFIX
echo udo $udo
echo udopg $udopg
echo uconfigure $uconfigure
echo umake $umake
echo ugmake $ugmake
echo py $py
echo -n 'OK? [yes/N] '
read ok
if [ "$ok" != "yes" ]; then exit; fi
echo


echo Moving to source directory, ${SRC_DIR}.
cd ${SRC_DIR}
echo


echo -n 'Remove source directories? [yes/N] '
read remove_dirs
if [ "$remove_dirs" = "yes" ]; then
	echo Removing source directories...
	for file in *; do
		if [ -d $file ]; then
			rm -rf $file
			echo Removed $file
		fi
	done
	echo Done removing source directories.
else
	echo Not removing source directories.
	chown -R ${USR}:${USR} ${SRC_DIR}
fi
echo


$udo ${INSTALL_BIN_DIR}/fetch.sh


export PATH=${PREFIX}:$PATH:/sbin:/usr/sbin
/sbin/ldconfig ${PREFIX}/lib


## Apache 2.2.4
echo
echo ===== Installing Apache...
cd httpd-2.2.4
# These rmS get around the APR ./configure error 
# [Which of these are actually necessary?]
rm -rf ${PREFIX}/apache2/bin
rm -rf ${PREFIX}/apache2/build
rm -rf ${PREFIX}/apache2/include
rm -rf ${PREFIX}/apache2/lib
${uconfigure}/apache2 --enable-mods-shared='dav rewrite speling proxy' \
                      --with-berkeley-db=/usr/local/BerkeleyDB.4.5 \
                      || exit 1
$umake || exit 1
make install || exit 1
# post-install config
export PATH=$PATH:${PREFIX}/apache2/bin
ldconfig ${PREFIX}/apache2/lib
useradd -M -d ${PREFIX}/apache2 www
chown -R www:www ${PREFIX}/apache2
${PREFIX}/apache2/bin/apachectl stop
${PREFIX}/apache2/bin/apachectl start
cd ..
echo Done with Apache.
echo


## PostgreSQL 8.2.3
echo
echo ===== Installing PostgreSQL...
cd postgresql-8.2.3
${uconfigure}/pgsql --with-perl || exit 1
$ugmake || exit 1
gmake install || exit 1
# post-install config
export PATH=$PATH:${PREFIX}/pgsql/bin
ldconfig ${PREFIX}/pgsql/lib
useradd -M -d ${PREFIX}/pgsql postgres
mkdir ${PREFIX}/pgsql/data
chown -R postgres:postgres ${PREFIX}/pgsql
$udopg ${PREFIX}/pgsql/bin/initdb -D ${PREFIX}/pgsql/data
$udopg ${PREFIX}/pgsql/bin/pg_ctl \
        -D ${PREFIX}/pgsql/data \
        -l ${PREFIX}/pgsql/data/logfile stop
$udopg ${PREFIX}/pgsql/bin/pg_ctl \
	-D ${PREFIX}/pgsql/data \
	-l ${PREFIX}/pgsql/data/logfile start
$udopg ${PREFIX}/pgsql/bin/createuser -S -d -R ${USR}
$udopg ${PREFIX}/pgsql/bin/createdb -O ${USR} ${USR}
$udopg ${PREFIX}/pgsql/bin/createlang plpgsql ${USR} 
cd ..
echo Done with PostgreSQL.
echo


## GEOS 2.2.3
echo
echo ===== Installing GEOS...
cd geos-2.2.3
$uconfigure || exit 1
$umake || exit 1
make install || exit 1
cd ..
echo Done with GEOS.
echo


## Proj 4.5.0
echo
echo ===== Installing Proj...
cd proj-4.5.0
$uconfigure || exit 1
$umake || exit 1
make install || exit 1
cd ..
echo Done with Proj.
echo


## PostGIS 1.2.1
# Depends on Proj and GEOS for some operations
echo
echo ===== Installing PostGIS...
cd postgis-1.2.1
./configure \
	--with-pgsql=${PREFIX}/pgsql/bin/pg_config \
	--with-geos=${PREFIX}/bin/geos-config \
	--with-proj=${PREFIX} --with-proj-libdir=${PREFIX}/lib \
	|| exit 1
$umake || exit 1
make install || exit 1
cd ${PREFIX}/pgsql/share
$udopg ${PREFIX}/pgsql/bin/psql -d ${USR} -f lwpostgis.sql
$udopg ${PREFIX}/pgsql/bin/psql -d ${USR} -f spatial_ref_sys.sql
cd ${SRC_DIR}
echo Done with PostGIS.
echo


## Python 2.5
echo
echo ===== Installing Python...
cd Python-2.5
$uconfigure --enable-unicode=ucs4 || exit 1
$umake || exit 1
make install || exit 1
cd ..
echo Done with Python.
echo


## setuptools <http://peak.telecommunity.com/DevCenter/setuptools>
echo
echo ===== Installing setuptools...
$py ez_setup.py || exit 1
echo Done with setuptools.
echo


## Python Cartographic Library (PCL) - Core 0.11.0
# Depends on Proj and GEOS for some operations
# Depends on zope.interface (but not during installation)
echo
echo ===== Installing PCL-Core...
cd PCL-0.11.0/PCL-Core
$udo $py setup.py build_ext || exit 1
$udo $py setup.py build || exit 1
$py setup.py install || exit 1
cd ..
echo Done with PCL-Core.
echo

echo Done with installation.
echo

