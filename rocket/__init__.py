# -*- coding: utf-8 -*-

__version__ = (0, 0, 'pre-alpha')
__authors__ = ['Markus Döllinger']


def get_version():
    """
    :return: Returns the version as a nicely formatted string
    """
    return "%d.%d%s" % (__version__[0], __version__[1],
            (" %s" % __version__[2]) if len(__version__) > 1 else "")


def get_authors():
    """
    :return: Returns the list of authors
    """
    return ", ".join(__authors__)


