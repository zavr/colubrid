# -*- coding: utf-8 -*-
"""
    colubrid.utils
    ~~~~~~~~~~~~~~

    :copyright: 2006 by Armin Ronacher.
    :license: BSD License
"""

from __future__ import generators
from urllib import quote
from cStringIO import StringIO
import posixpath


def get_version():
    """return the colubrid and python version."""
    from colubrid import __version__
    from sys import version
    return '%s - Python %s' % (__version__, version.split('\n')[0].strip())


class MultiDict(dict):
    #adopted from django

    def __init__(self, key_to_list_mapping=()):
        dict.__init__(self, key_to_list_mapping)

    def __getitem__(self, key):
        """
        Return the last data value for this key, or [] if it's an empty list;
        raises KeyError if not found.
        """
        list_ = dict.__getitem__(self, key)
        try:
            return list_[-1]
        except IndexError:
            return []

    def _setitem_list(self, key, value):
        dict.__setitem__(self, key, [value])
    __setitem__ = _setitem_list

    def get(self, key, default=None):
        """Return the default value if the requested data doesn't exist"""
        try:
            val = self[key]
        except KeyError:
            return default
        if val == []:
            return default
        return val

    def getlist(self, key):
        """Return an empty list if the requested data doesn't exist"""
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            return []

    def setlist(self, key, list_):
        dict.__setitem__(self, key, list_)

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

    def setlistdefault(self, key, default_list=()):
        if key not in self:
            self.setlist(key, default_list)
        return self.getlist(key)

    def appendlist(self, key, value):
        """Append an item to the internal list associated with key."""
        self.setlistdefault(key, [])
        dict.__setitem__(self, key, self.getlist(key) + [value])

    def items(self):
        """
        Return a list of (key, value) pairs, where value is the last item in
        the list associated with the key.
        """
        return [(key, self[key]) for key in self.keys()]

    def lists(self):
        """Return a list of (key, list) pairs."""
        return dict.items(self)

    def values(self):
        """Returns a list of the last value on every key list."""
        return [self[key] for key in self.keys()]

    def copy(self):
        """Returns a copy of this object."""
        import copy
        MultiDict.__setitem__ = dict.__setitem__
        cp = copy.deepcopy(self)
        MultiDict.__setitem__ = MultiDict._setitem_list
        return cp

    def update(self, other_dict):
        """update() extends rather than replaces existing key lists."""
        if isinstance(other_dict, MultiDict):
            for key, value_list in other_dict.lists():
                self.setlistdefault(key, []).extend(value_list)
        else:
            for key, value in other_dict.items():
                self.setlistdefault(key, []).append(value)


class MergedMultiDict(object):
    """
    A simple class for creating new "virtual" dictionaries that actualy look
    up values in more than one MultiDict dictionary, passed in the constructor.
    """
    def __init__(self, *dicts):
        self._dicts = dicts

    def __getitem__(self, key):
        for d in self._dicts:
            try:
                return d[key]
            except KeyError:
                pass
        raise KeyError

    def __repr__(self):
        tmp = {}
        for dict_ in self._dicts:
            tmp.update(dict_)
        return repr(tmp)

    def __iter__(self):
        return self.iterkeys()

    def copy(self):
        return dict(self.iteritems())

    def iterkeys(self):
        for d in self._dicts:
            for key in d:
                yield key

    def itervalues(self):
        for d in self._dicts:
            for value in d.itervalues():
                yield value

    def iteritems(self):
        for d in self._dicts:
            for item in d.iteritems():
                yield item

    def get(self, key, default):
        try:
            return self[key]
        except KeyError:
            return default

    def getlist(self, key):
        for d in self._dicts:
            try:
                return d.getlist(key)
            except KeyError:
                pass
        raise KeyError

    def items(self):
        return list(self.iteritems())

    def __contains__(self, key):
        for d in self._dicts:
            if d.has_key(key):
                return True
        return False

    def has_key(self, key):
        return self.__contains__(key)


class FieldStorage(object):

    def __init__(self, name, filename, ftype, data):
        self.name = name
        self.type = ftype
        self.filename = filename
        self.data = data

    def read(self, *args):
        if not hasattr(self, '_cached_buffer'):
            self._cached_buffer = StringIO(self.data)
        return self._cached_buffer.read(*args)

    def readline(self, *args):
        if not hasattr(self, '_cached_buffer'):
            self._cached_buffer = StringIO(self.data)
        return self._cached_buffer.readline(*args)

    def readlines(self):
        result = []
        while True:
            row = self.readline()
            if not row:
                break
            result.append(row)
        return result

    def __iter__(self):
        while True:
            row = self.readline()
            if not row:
                return
            yield row

    def __repr__(self):
        return '%s (%s)' % (self.filename, self.type)

    def __str__(self):
        return self.__repr__()


class HttpHeaders(object):

    def __init__(self, defaults=None):
        if defaults is None:
            self._defaults = []
        elif isinstance(defaults, dict):
            self._defaults = dict.items()
        elif isinstance(defaults, list):
            self._defaults = defaults[:]
        else:
            raise TypeError('invalid default value')
        self.reset()

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.set(key, value)

    def __delitem__(self, key):
        self.remove(key)

    def __contains__(self, key):
        if not isinstance(key, basestring):
            raise TypeError('keys have to be string')
        key = key.lower()
        for k, v in self.data:
            if k.lower() == key:
                return True
        return False

    def add(self, key, value):
        """add a new header tuple to the list"""
        self.data.append((key, value))

    def remove(self, key, count=-1):
        """removes count header tuples from the list
        where key matches
        """
        removed = 0
        data = []
        for _key, _value in self.data:
            if _key.lower() != key.lower():
                if count > -1:
                    if removed >= count:
                        break
                    else:
                        removed += 1
                data.append((_key, _value))
        self.data = data

    def reset(self):
        """Reset to default headers."""
        self.data = self._defaults

    def clear(self):
        """clears all headers"""
        self.data = []

    def set(self, key, value):
        """remove all header tuples for key and add
        a new one
        """
        self.remove(key)
        self.add(key, value)

    def get(self, key=False, httpformat=False):
        """returns matching headers as list

        if httpformat is set the result is a HTTP
        header formatted list.
        """
        if not key:
            result = self.data
        elif not isinstance(key, basestring):
            raise TypeError('keys have to be strings')
        else:
            result = []
            for k, v in self.data:
                if k.lower() == key.lower():
                    result.append((str(k), str(v)))
        if httpformat:
            return '\n'.join(['%s: %s' % item for item in result])
        return result

    def getfirst(self, key, default=None):
        """Return the first valuefor key."""
        if not isinstance(key, basestring):
            raise TypeError('keys have to be strings')
        for k, v in self.data:
            if k.lower() == key.lower():
                return v
        return default


def get_full_url(environ, append=None):
    """Get the full URL of the requested page, including query string
       if any. If append is given, use it as the pathname after the
       host name."""

    if 'REQUEST_URI' in environ and append is None:
        return environ['REQUEST_URI']

    url = environ['wsgi.url_scheme']+'://'
    if environ.get('HTTP_HOST'):
        url += environ['HTTP_HOST']
    else:
        url += environ['SERVER_NAME']
        if environ['wsgi.url_scheme'] == 'https':
            if environ['SERVER_PORT'] != '443':
                url += ':' + environ['SERVER_PORT']
        else:
            if environ['SERVER_PORT'] != '80':
                url += ':' + environ['SERVER_PORT']

    if append is None:
        url += quote(environ.get('SCRIPT_NAME', ''))
        url += quote(environ.get('PATH_INFO', ''))
        if environ.get('QUERY_STRING'):
            url += '?' + environ['QUERY_STRING']
    else:
        url += append
    return url


def splitpath(p):
    return [s for s in (posixpath.normpath(posixpath.join('/', p)) +
            (p and p[-1] == '/' and '/' or '')).split('/') if s]


def fix_slash(environ, wantslash):
    """
    Fixes the trailing slash in an url.
    If the user requests an container object without an slash it
    will appends one.
    Requested an non container object with an traling slash will
    result in an redirect to the same url without it.
    the QUERY_STRING won't get lost but post data would. So don't
    forget the slash problem in your form actions ;-)
    """
    from colubrid.exceptions import HttpMoved
    #FIXME
    #  argh. never did something that supid
    #  find a better solution for that problem.
    url = quote(environ.get('SCRIPT_NAME', ''))
    url += quote(environ.get('PATH_INFO', ''))
    query = environ.get('QUERY_STRING', '')
    oldurl = query and ('%s?%s' % (url, query)) or url

    if oldurl and oldurl != '/':
        if url.endswith('/'):
            if not wantslash:
                url = url[:-1]
        else:
            if wantslash:
                url += '/'

        newurl = query and ('%s?%s' % (url, query)) or url
        if oldurl != newurl:
            raise HttpMoved(newurl)
