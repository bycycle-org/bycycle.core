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
import os

from setuptools import setup, find_packages


pcl_core_svn_url = 'http://svn.gispython.org/svn/gispy/PCL/tags/rel-0.11.0/PCL-Core/'
os.system('easy_install -U %s' % pcl_core_svn_url)


setup(
    name='byCycleCore',
    version='0.4a0',
    description='byCycle Core Services',
    long_description='Address normalization, geocoding, routing and other GIS-related services.',
    license='GPLv3',
    author='Wyatt L Baldwin, byCycle.org',
    author_email='wyatt@byCycle.org',
    keywords='bicycle bike cycyle trip planner route finder',
    url='http://bycycle.org/',
    # This, in effect, creates an alias to the latest 0.4 dev version
    download_url='http://guest:guest@code.bycycle.org/core/trunk#egg=byCycleCore-dev',
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
        'Dijkstar==1.0',
        'Elixir==0.3.0',
        'nose==0.10.4',
        #'PCL-Core==0.11.0',
        'psycopg2==2.0.8',
        'simplejson==2.0.7',
        'SQLAlchemy==0.3.7',
        'zope.interface==3.3.0.1',
    ),
)

