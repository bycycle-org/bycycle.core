"""$Id$

Description goes here.

Copyright (C) 2006 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>

All rights reserved.

TERMS AND CONDITIONS FOR USE, MODIFICATION, DISTRIBUTION

1. The software may be used and modified by individuals for noncommercial,
private use.

2. The software may not be used for any commercial purpose.

3. The software may not be made available as a service to the public or within
any organization.

4. The software may not be redistributed.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
# shp2sql.py
#  Milwaukee, WI, shp/dbf import
#
# AUTHOR
#  Wyatt Baldwin <wyatt@bycycle.org>
# DATE
#  January 27, 2006
#  March 30, 2006 [Switched from SQLite to MySQL]
#  April 4, 2006 [Converted to single-DB, shared with other regions]
# VERSION
#  0.1
# PURPOSE
#  Script to import line geometry and associated attributes from a street layer
#  shapefile into a normalized database
# USAGE
#  python shp2sql.py
# LICENSE
#  GNU Public License (GPL)
#  See LICENSE in top-level package directory
# WARRANTY
#  This program comes with NO warranty, real or implied.
# TODO
#  Turn this into a derived class; create a base class that all regions can use
import sys, os
from bycycle.core.util import gis, meter


region = 'milwaukeewi'


# Fields we want from the DBF
dbf_fields = ('FNODE',
              'TNODE',
              'FRADDL',
              'TOADDL',
              'FRADDR',
              'TOADDR',
              'FEDIRP',
              'FENAME',
              'FETYPE',
              'FEDIRS',
              'CITYL',
              'CITYR',
              'ZIPL',
              'ZIPR',
              'TLID',
              'CFCC',
              'Bike_facil',
              'GRADE',
              'LANES',
              'ADT',
              'SPD',
              'one_way')

# Fields in raw table to be transferred to street layer table.
# The items in this list must correspond to the fields in the street layer
# table definition (i.e., must be in the right order).
db_fields = ('geo',
             'fnode',
             'tnode',
             'addr_f',
             'addr_t',
             'even_side',
             'street_name_id',
             'city_l_id',
             'city_r_id',
             'state_l_id',
             'state_r_id',
             'zipl',
             'zipr',
             'one_way',
             'cfcc',
             'bike_facil',
             'lanes',
             'adt',
             'spd')

# Command-line args
start = -1
no_prompt = False
only = False

# DB handle
db = None

raw = '%s_raw' % region

timer = None


def shpToRawSql():
    datasource = 'route_roads84psrenode'
    layer = 'route_roads84psrenode'
    path = os.path.join(os.getcwd(), datasource)
    # Drop existing raw table
    Q = 'DROP TABLE IF EXISTS %s' % raw
    if not _wait(Q):
        _execute(Q)
    # Extract SQL from Shapefile
    cmd = 'mysqlgisimport -t %s -o %s.sql %s' % \
          (raw, raw, os.path.join(path, layer))
    if not _wait('Extract SQL from Shapefile'):
        _system(cmd)
    # Load SQL into DB
    cmd = 'mysql -u root --password="" bycycle-1 < %s.sql' % raw
    if not _wait('Load SQL into DB'):
        _system(cmd)

def addColumns():
    # Add missing...
    # INTEGER columns
    Q = 'ALTER TABLE %s ADD COLUMN %%s %%s NOT NULL' % raw
    cols = ('addr_f', 'addr_t', 'street_name_id', 'city_l_id', 'city_r_id')
    for col in cols:
        _execute(Q % (col, 'INTEGER'))
    # CHAR(s) columns
    cols = ('state_l_id', 'state_r_id')
    for col in cols:
        _execute(Q % (col, 'CHAR(2)'))
    # ENUM columns
    _execute(Q % ('even_side', 'ENUM("l", "r")'))

def fixRaw():
    # Abbreviate bike modes
    Q = 'UPDATE %s SET bike_facil="%%s" WHERE bike_facil="%%s"' % raw
    bm = (("t", "bike trail"),
          ("r", "bike route"),
          ("l", "bike lane"),
          ("p", "preferred street"),
          )
    for m in bm:
        _execute(Q % (m[0], m[1]))
    # Fix CFCC for bike trails
    _execute('UPDATE %s SET cfcc="a71" WHERE bike_facil="t"' % raw)
    # Fix one_way (0 => 'n', 1 => 'ft', 2 => 'tf', 3 => '')
    Q = 'UPDATE %s SET one_way="%s" WHERE one_way="%s"'
    M = {'0': 'n', '1': 'ft', '2': 'tf', '3': ''}
    for m in M:
        _execute(Q % (raw, M[m], m))

def createSchema():
    tables = ('layer_street', 'layer_node', 'street_name', 'city', 'state')
    for table in tables:
        _execute('DROP TABLE IF EXISTS %s_%s' % (region, table))
    cmd = 'mysql -u root --password="" < ./schema.sql'
    _system(cmd)

def unifyAddressRanges():
    """Combine left and right side address number into a single value."""
    QF = 'UPDATE %s ' \
        'SET addr_f = (ROUND(fradd%s / 10.0) * 10) + 1 ' \
        'WHERE fradd%s != 0'
    QT = 'UPDATE %s ' \
        'SET addr_t = (ROUND(toadd%s / 10.0) * 10) ' \
        'WHERE toadd%s != 0'
    for side in ('l', 'r'):
        _execute(QF % (raw, side, side))
        _execute(QT % (raw, side, side))
    # Set even side
    QEL = 'UPDATE %s SET even_side = "l" ' \
          'WHERE (fraddl != 0 AND fraddl %% 2 = 0) OR ' \
          ' (toaddl != 0 AND toaddl %% 2 = 0)'
    QER = 'UPDATE %s SET even_side = "r" ' \
          'WHERE (fraddr != 0 AND fraddr %% 2 = 0) OR ' \
          ' (toaddr != 0 AND toaddr %% 2 = 0)'
    _execute(QEL % raw)
    _execute(QER % raw)

def transferStreetNames():
    """Transfer street names to their own table."""
    Q = 'INSERT INTO %s_street_name (prefix, name, type, suffix) '\
        'SELECT DISTINCT fedirp, fename, fetype, fedirs FROM %s'
    _execute(Q % (region, raw))

def updateRawStreetNameIds():
    """Set the street name ID of each raw record."""
    # Get all the distinct street names NEW
    Q = 'SELECT DISTINCT fedirp, fename, fetype, fedirs FROM %s' % raw
    _execute(Q)
    rows = db.fetchAll()
    # Index each street name ID by its street name
    # {(stname)=>street_name_id}
    stnames = {}
    Q = 'SELECT id, prefix, name, type, suffix FROM %s_street_name' % region
    _execute(Q)
    for row in db.fetchAll():
        stnames[(row[1],row[2],row[3],row[4])] = row[0]
    # Index raw row IDs by their street name ID {street_name_id=>[row IDs]}
    stid_rawids = {}
    Q  = 'SELECT id, fedirp, fename, fetype, fedirs FROM %s' % raw
    _execute(Q)
    for row in db.fetchAll():
        stid = stnames[(row[1],row[2],row[3],row[4])]
        if stid in stid_rawids:
            stid_rawids[stid].append(row[0])
        else:
            stid_rawids[stid] = [row[0]]
    # Iterate over street name IDs and set street name IDs of raw records
    Q = 'UPDATE %s SET street_name_id=%%s WHERE id IN %%s' % raw
    met = meter.Meter()
    met.setNumberOfItems(len(stid_rawids))
    met.startTimer()
    record_number = 1
    for stid in stid_rawids:
        ixs = stid_rawids[stid]
        if len(ixs) == 1:
            in_data = '(%s)' % int(ixs[0])
        else:
            in_data = tuple([int(ix) for ix in ixs])
        _execute(Q % (stid, in_data), False)
        met.update(record_number)
        record_number+=1
    print  # newline after the progress meter

def transferCityNames():
    """Transfer city names to their own table."""
    Q = 'INSERT INTO %s_city (city) ' \
        'SELECT DISTINCT cityl FROM %s' % (region, raw)
    _execute(Q)
    Q = 'INSERT INTO %s_city (city) ' \
        'SELECT DISTINCT cityr FROM %s WHERE cityr NOT IN ' \
        '(SELECT city FROM %s_city)' % (region, raw, region)
    _execute(Q)

def updateRawCityIds():
    """Set the city ID of each raw record."""
    Q0 = 'SELECT DISTINCT id, city FROM %s_city' % region
    for side in ('l', 'r'):
        Q1 = 'UPDATE %s SET city_%s_id=%s WHERE city%s="%s"' % \
             (raw, side, '%s', side, '%s')
        # Get all the distinct city names
        _execute(Q0)
        rows = db.fetchAll()
        # Iterate over city rows and set city IDs of raw records
        for row in rows:
            _execute(Q1 % (row[0], row[1]))

def updateRawStateIds():
    """Set the state ID of each raw record."""
    Q = 'INSERT INTO %s_state VALUES ("wi", "wisconsin")' % region
    _execute(Q)
    Q = 'UPDATE %s SET state_l_id="wi", state_r_id="wi"' % raw
    _execute(Q)

def createNodes():
    Q = 'INSERT INTO %s_layer_node ' \
        '(SELECT DISTINCT fnode, startpoint(geo)' \
        ' FROM %s)' % (region, raw)
    _execute(Q)
    Q = 'INSERT INTO %s_layer_node ' \
        '(SELECT DISTINCT tnode, endpoint(geo)' \
        ' FROM %s' \
        ' WHERE tnode NOT IN (SELECT DISTINCT id FROM %s_layer_node))' % \
        (region, raw, region)
    _execute(Q)

def transferAttrs():
    """Transfer fields from raw table to street layer table."""
    fields = ', '.join(db_fields)
    Q = 'INSERT INTO %s_layer_street SELECT NULL, %s FROM %s' % \
        (region, fields, raw)
    _execute(Q)


## --

def _system(cmd):
    print cmd
    exit_code = os.system(cmd)
    if exit_code:
        sys.exit()

def _wait(msg='Continue or skip'):
    if no_prompt:
        return False
    timer.pause()
    resp = raw_input(msg + '? ')
    timer.unpause()
    return resp

def _openDB():
    """Set up DB connection."""
    global db
    path = 'bycycle.core.model.%s' % region
    db = __import__(path, globals(), locals(), ['']).Mode()

def _execute(Q, show=True):
    """Execute a SQL query."""
    if db is None:
        _openDB()
    try:
        if show:
            print 'Executing: "%s"' % Q
        db.execute(Q)
    except Exception, e:
        print 'Execution failed: %s' % e
        sys.exit()

def run():
    global start, only, no_prompt, timer

    overall_timer = meter.Timer()
    overall_timer.start()

    # Reset for each function
    timer = meter.Timer()
    timer.start()

    pairs = [('Convert shapefile to monolithic SQL table',
              shpToRawSql),

             ('Add columns to raw',
              addColumns),

             ('Fix raw table: Remove NULLs, add columns, etc',
              fixRaw),

             ('Create byCycle schema tables',
              createSchema),

             ('Unify address ranges',
              unifyAddressRanges),

             ('Transfer street names',
              transferStreetNames),

             ('Update street name IDs in raw table',
              updateRawStreetNameIds),

             ('Transfer city names',
              transferCityNames),

             ('Update city IDs in raw table',
              updateRawCityIds),

             ('Update state IDs in raw table',
              updateRawStateIds),

             ('Create nodes',
              createNodes),

             ('Transfer attributes',
              transferAttrs),
             ]

    # Process command-line arguments
    try:
        arg1 = sys.argv[1]
    except IndexError:
      pass
    else:
        try:
            start = int(arg1)
        except ValueError:
            no_prompt = arg1 == 'no_prompt'
        else:
            try:
                arg2 = sys.argv[2]
            except IndexError:
                pass
            else:
                only = arg2 == 'only'
                no_prompt = arg2 == 'no_prompt'

    print 'Transferring data into byCycle schema...\n' \
          '----------------------------------------' \
          '----------------------------------------'
    prompt = '====>'
    if only:
        # Do one function without prompting
        pair = pairs[start]
        msg, func = pair[0], pair[1]
        print '%s %s' % (prompt, msg)
        # Get function arguments
        try:
            args = pair[2]
        except IndexError:
            args = ()
        # Do function
        timer.start()
        apply(func, args)
        print timer.stop()
    else:
        # Do all functions, starting from specified
        for i, p in enumerate(pairs):
            msg, func = p[0], p[1]
            if i < start:
                # Skip functions before specified starting point
                print '%s Skipping %s %s? ' % (i, prompt, msg)
                continue
            # Get function arguments
            try:
                args = p[2]
            except IndexError:
                args = ()
            # Show prompt and function message
            sys.stdout.write('%s %s %s'% (i, prompt, msg))
            if not no_prompt:
                # Prompt user to continue
                overall_timer.pause()
                resp = raw_input('? ').strip().lower()
                overall_timer.unpause()
            else:
                # Don't prompt user to continue
                print
            if  no_prompt or resp in ('', 'y'):
                # Do function
                timer.start()
                apply(func, args)
                print timer.stop()
            elif resp in ('q', 'quit', 'exit'):
                print 'Aborted at %s' % i
                sys.exit()

    print '----------------------------------------' \
          '----------------------------------------\n' \
          'Done. %s total.' % overall_timer.stop()

if __name__ == '__main__':
    run()
