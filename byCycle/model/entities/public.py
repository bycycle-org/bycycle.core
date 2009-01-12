###############################################################################
# $Id$
# Created 2006-09-14.
#
# Public (i.e., shared) entity classes.
#
# Copyright (C) 2006, 2007 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
###############################################################################
"""Entities that are shared by all regions; they live in the public SCHEMA."""
import os, marshal

from sqlalchemy import func, select

from elixir import Entity
from elixir import options_defaults, using_options, using_table_options
from elixir import has_field, belongs_to, has_many
from elixir import Integer, String, Float

from byCycle import model_path
from byCycle.model import db
from byCycle.model.entities.util import cascade_args, encodeFloat

__all__ = ['Region', 'EdgeAttr', 'Service', 'Geocode', 'Route']


metadata = db.metadata_factory('public')
options_defaults['shortnames'] = True

# A place to keep references to adjacency matrices so they don't need to be
# continually read from disk
matrix_registry = {}


class Region(Entity):
    has_field('title', String)
    has_field('slug', String)
    has_field('srid', Integer)
    has_field('units', String)
    has_field('earth_circumference', Float)
    has_field('block_length', Float)
    has_field('jog_length', Float)
    has_many('edge_attrs', of_kind='EdgeAttr', order_by='id')
    has_many('geocodes', of_kind='Geocode')
    has_many('routes', of_kind='Route')

    required_edge_attrs = [
        'length',
        'street_name_id',
        'node_f_id',
        'code',
        'bikemode'
    ]

    @property
    def data_path(self):
        return os.path.join(model_path, self.slug, 'data')

    @property
    def matrix_path(self):
        return os.path.join(self.data_path, 'matrix.pyc')

    @property
    def edge_attrs_index(self):
        """Create an index of adjacency matrix street attributes.

        In the ``matrix``, there is an (ordered) of edge attributes for each
        edge. ``edge_attrs_index`` gives us a way to access those attributes
        by name while keeping the size of the matrix smaller. We require that
        edges for all regions have at least a length, street name ID,
        from-node ID, street classification (AKA code), and bike mode.

        """
        edge_attrs = self.required_edge_attrs[:]
        # Add the region-specific edge attributes used for routing
        edge_attrs += [a.name for a in self.edge_attrs]
        edge_attrs_index = {}
        for i, attr in enumerate(edge_attrs):
            edge_attrs_index[attr] = i
        return edge_attrs_index

    def _get_adjacency_matrix(self):
        """Return matrix. Prefer 1) existing 2) disk 3) newly created."""
        matrix = matrix_registry.get(self.slug, None)
        if matrix is None:
            try:
                loadfile = open(self.matrix_path, 'rb')
            except IOError:
                matrix = self.createAdjacencyMatrix()
            else:
                try:
                    matrix = marshal.load(loadfile)
                except (EOFError, ValueError, TypeError):
                    matrix = self.createAdjacencyMatrix()
                loadfile.close()
            matrix_registry[self.slug] = matrix
        return matrix

    def _set_adjacency_matrix(self, matrix):
        matrix_registry[self.slug] = matrix
        dumpfile = open(self.matrix_path, 'wb')
        marshal.dump(matrix, dumpfile)
        dumpfile.close()

    matrix = G = property(_get_adjacency_matrix, _set_adjacency_matrix)

    def createAdjacencyMatrix(self):
        """Create the adjacency matrix for this DB's region.

        Build a matrix suitable for use with the route service. The structure
        of the matrix is defined by/in the Dijkstar package.

        return
            Adjacency matrix for this region:
                {nodes: {}, edges: {}}
                    nodes: {v: {v: e, v: e, ...}, v: {v: e, v: e, ...}, ...}
                    edges: {e: (attrs), e: (attrs), ...}

        """
        from byCycle.util.meter import Meter, Timer

        timer = Timer()

        def took():
            print 'Took %s seconds.' % timer.stop()

        timer.start()
        print 'Fetching edge attributes...'
        c = self.module.Edge.c
        cols = [c.id, c.node_f_id, c.node_t_id, c.one_way, c.street_name_id,
                c.geom, c.code, c.bikemode]
        cols += [a.name for a in self.edge_attrs]
        rows = select(cols).execute()
        num_edges = rows.rowcount
        took()

        timer.start()
        print 'Total number of edges in region: %s' % num_edges
        print 'Creating adjacency matrix...'
        matrix = {'nodes': {}, 'edges': {}}
        nodes = matrix['nodes']
        edges = matrix['edges']
        meter = Meter(num_items=num_edges, start_now=True)
        meter_i = 1
        for row in rows:
            adjustments = self._adjustEdgeRowForMatrix(row)

            ix = row.id
            node_f_id = row.node_f_id
            node_t_id = row.node_t_id
            one_way = row.one_way

            entry = [encodeFloat(row.geom.length())]
            entry += [row[attr] for attr in self.required_edge_attrs[1:]]
            entry += [row[a.name] for a in self.edge_attrs]
            for k in adjustments:
                entry[self.edge_attrs_index[k]] = adjustments[k]
            edges[ix] = tuple(entry)

            # One way values:
            # 0: no travel in either direction
            # 1: travel from => to only
            # 2: travel to => from only
            # 3: travel in both directions

            if one_way & 1:
                nodes.setdefault(node_f_id, {})[node_t_id] = ix
            if one_way & 2:
                nodes.setdefault(node_t_id, {})[node_f_id] = ix

            meter.update(meter_i)
            meter_i += 1
        rows.close()
        print
        took()

        timer.start()
        print 'Saving adjacency matrix...'
        self.matrix = matrix
        took()

    @property
    def module(self):
        module = getattr(self, '_module', None)
        if module is None:
            path = 'byCycle.model.%s' % self.slug
            module = __import__(path, locals(), globals(), [''])
            self._module = module
        return module

    def _get_entity(self, name):
        entity = getattr(self, '_%s_entity' % name, None)
        if entity is None:
            entity = getattr(self.module, name)
            setattr(self, '_%s_entity' % name, entity)
        return entity

    def _adjustEdgeRowForMatrix(self, row):
        return self.module.Edge._adjustRowForMatrix(row)

    def __str__(self):
        return '%s: %s' % (self.slug, self.title)


class EdgeAttr(Entity):
    using_options(tablename='edge_attrs')
    has_field('name', String)
    belongs_to('region', of_kind='Region', **cascade_args)
    def __repr__(self):
        return str(self.name)


class Service(Entity):
    has_field('title', String)
    belongs_to('region', of_kind='Region', inverse='geocodes', **cascade_args)


class Geocode(Entity):
    has_field('title', String)
    belongs_to('region', of_kind='Region', inverse='geocodes', **cascade_args)


class Route(Entity):
    has_field('title', String)
    belongs_to('region', of_kind='Region', **cascade_args)


