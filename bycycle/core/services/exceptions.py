################################################################################
# $Id$
# Created 2005-??-??.
#
# byCycle Exceptions.
#
# Copyright (C) 2006 Wyatt Baldwin, byCycle.org <wyatt@bycycle.org>.
# All rights reserved.
#
# For terms of use and warranty details, please see the LICENSE file included
# in the top level of this distribution. This software is provided AS IS with
# NO WARRANTY OF ANY KIND.
################################################################################
"""byCycle `Exception`s."""


class ByCycleError(Exception):
    """Root class for byCycle `Exception`s.

    Attributes
    ----------
    
    ``title``
        A short title for the error, as might be displayed in a heading.
    
    ``description``
        A string that briefly describes the exception/error.
    
    ``explanation``
        A more long winded explanation of an error.
    
    """

    title = 'Error'
    description = 'An unspecified byCycle error occurred.'
    explanation = None

    def __init__(self, description=None):
        if description is not None:
            self.description = description
        Exception.__init__(self)

    def __str__(self):
        return str(': '.join((self.title, self.description)))


class InputError(ByCycleError):

    title = 'Not Understood'
    description = 'Sorry, we could not understand your request.'
    
    def __init__(self, description=None, explanation=None):
        """
        
        ``description``
            Either a single error description or a list of such descriptions.
        
        """
        if isinstance(description, basestring):
            description = [description]
        if description is not None:
            # save the original error list
            self.errors = description
            description = '\n'.join([str(d) for d in description])
        if explanation is not None:
            self.explanation = explanation
        ByCycleError.__init__(self, description)


class NotFoundError(ByCycleError):

    title = 'Not Found'
    description = 'Sorry, we could not find what you were looking for.'

    def __init__(self, description=None):
        ByCycleError.__init__(self, description)


class IdentifyError(ByCycleError):

    title = 'Unidentified'
    description = 'Sorry, we were unable to identify that.'

    def __init__(self, description=None):
        ByCycleError.__init__(self, description)
