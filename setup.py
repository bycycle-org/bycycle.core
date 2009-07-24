###############################################################################
# $Id$
# Created 2006-09-07
#
# Project setup for byCycle Core.
#
# Copyright (C) 2006, 2007 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
from setuptools import setup, find_packages


setup(
    name='bycycle.core',
    version='0.5',
    description='byCycle Core Services',
    long_description='byCycle model, routing, and GIS related services.',
    license='GNU General Public License (GPL)',
    author='Wyatt L Baldwin, byCycle.org',
    author_email='wyatt@bycycle.org',
    keywords='bicycle bike cycyle trip planner route finder',
    url='http://bycycle.org/',
    download_url='http://guest:guest@code.bycycle.org/Core/trunk#egg=byCycleCore-dev',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Topic :: Education',
        'Topic :: Scientific/Engineering :: GIS',
        ],
    packages=find_packages(),
    zip_safe=False,
    install_requires=(
        'Shapely>=1.0.11',
        'pyproj>=1.8.5',
        'GeoJSON>=1.0.1',
        'psycopg2>=2.0.11',
        'SQLAlchemy>=0.5.5',
        'Dijkstar>=1.0',
        'nose>=0.11.1',
        'simplejson>=2.0.9',
        'Restler==dev,>=0.3dev-r92',
    ),
)
