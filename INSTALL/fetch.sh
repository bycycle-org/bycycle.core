#!/bin/bash

echo Fetching source packages...
for url in \
	ftp://ftp.oregonstate.edu/pub/apache/httpd/httpd-2.2.4.tar.bz2 \
	http://wwwmaster.postgresql.org/redir?ftp%3A%2F%2Fftp5.us.postgresql.org%2Fpub%2FPostgreSQL%2Fsource%2Fv8.2.3%2Fpostgresql-8.2.3.tar.bz2 \
	http://geos.refractions.net/geos-2.2.3.tar.bz2 \
	ftp://ftp.remotesensing.org/proj/proj-4.5.0.tar.gz \
	http://postgis.refractions.net/download/postgis-1.2.1.tar.gz \
	http://www.python.org/ftp/python/2.5/Python-2.5.tar.bz2 \
	http://peak.telecommunity.com/dist/ez_setup.py \
	http://gispython.org/downloads/gispy/PCL-0.11.0.tar.gz 
do
	wget --no-clobber $url
	if [ $? = 1 ]
	then 
		echo Failed downloading $url. Aborting.
		exit
	fi
done
echo Done fetching.
echo


echo Decompressing and unpacking packages...
for file in *.tar.gz
do
	echo $file
	tar xzf $file
done
for file in *.tar.bz2
do
	echo $file
	tar xjf $file
done
echo Done decompressing and unpacking.
echo

