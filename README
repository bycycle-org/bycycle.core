byCycle Trip Planner - ReadMe
+++++++++++++++++++++++++++++
01/28/2006


Version
=======

0.4


Changes
=======

- Migrated from MySQL to PostgreSQL
- Using SQLAlchemy to interact with the database instead of using raw SQL
- Using PostGIS for storing and operating on spatial data
- Using the PCL to manipulate geometries in Python
- Moved services into classes that have a common base
- Switched to a reStructuredText style of docstrings
- Cleaned up the route service quite a bit
- Added a unittest test suite for the route service
- Created a Route class


Introduction
============

The byCycle Trip Planner is a system for planning trips made by bicycle.
Other travel modes are possible but none have been implemented yet.

The system uses data modes and associated weighting functions to do trip
planning for different datasets (e.g., geographic regions) and travel modes.

The system is being designed so that any interface (within reason) should be
able to call the back end. To that end a RESTful web service interface has
been implemented. By default, the result is returned in JavaScript Object
Notation (JSON), which can easily be parsed in most programming languages.
Future implementations should allow users to specify a preferred format
(e.g., XML).

Note: We need to produce some docs for the web service interface.


This Version
============

This is version 0.4. 0.4 is a big jump from 0.3, or at least it will be when
it's done.


License and Warranty
====================

Please see the file LICENSE.txt for details regarding the license and warranty.


Installation
============

See the INSTALL.txt file in this directory.


More Information
================

Information about the byCycle project can be found at http://byCycle.org/.
Information about the Trip Planner in particular can be found at
http://byCycle.org/tripplanner/.


Contact
=======

You can contact us to ask questions, make comments, offer suggestions, get
help, offer help, etc at contact@bycycle.org or by going to
http://byCycle.org/contact.html and using the form there.
