import re
import sys
from functools import update_wrapper
from django.http import HttpResponse
import simplejson


uncamel_patterns = (
    re.compile('(.)([A-Z][a-z]+)'),
    re.compile('([a-z0-9])([A-Z])'),
    )


class HttpJSONResponse(HttpResponse):
    """
    A convenient response class for json serializable data.
    """
    def __init__(self, content='', content_type=None, **kwargs):
        content = simplejson.dumps(content)
        content_type = content_type or 'application/json'
        super(HttpJSONResponse, self).__init__(
            content=content, content_type=content_type, **kwargs
            )


def uncamel(s):
    """
    Make camelcase lowercase and use underscores.

        >>> uncamel('CamelCase')
        'camel_case'
        >>> uncamel('CamelCamelCase')
        'camel_camel_case'
        >>> uncamel('Camel2Camel2Case')
        'camel2_camel2_case'
        >>> uncamel('getHTTPResponseCode')
        'get_http_response_code'
        >>> uncamel('get2HTTPResponseCode')
        'get2_http_response_code'
        >>> uncamel('HTTPResponseCode')
        'http_response_code'
        >>> uncamel('HTTPResponseCodeXYZ')
        'http_response_code_xyz'
    """
    for pat in uncamel_patterns:
        s = pat.sub(r'\1_\2', s)
    return s.lower()


class _Missing(object):
    def __repr__(self):
        return 'no value'

    def __reduce__(self):
        return '_missing'

_missing = _Missing()


def import_string(import_name, silent=False):
    """Imports an object based on a string.  This is useful if you want to
    use import paths as endpoints or something similar.  An import path can
    be specified either in dotted notation (``xml.sax.saxutils.escape``)
    or with a colon as object delimiter (``xml.sax.saxutils:escape``).

    If `silent` is True the return value will be `None` if the import fails.

    :param import_name: the dotted name for the object to import.
    :param silent: if set to `True` import errors are ignored and
                   `None` is returned instead.
    :return: imported object
    """
    # force the import name to automatically convert to strings
    if isinstance(import_name, unicode):
        import_name = str(import_name)
    try:
        if ':' in import_name:
            module, obj = import_name.split(':', 1)
        elif '.' in import_name:
            module, obj = import_name.rsplit('.', 1)
        else:
            return __import__(import_name)
        # __import__ is not able to handle unicode strings in the fromlist
        # if the module is a package
        if isinstance(obj, unicode):
            obj = obj.encode('utf-8')
        try:
            return getattr(__import__(module, None, None, [obj]), obj)
        except (ImportError, AttributeError):
            # support importing modules not yet set up by the parent module
            # (or package for that matter)
            modname = module + '.' + obj
            try:
                __import__(modname)
            except ImportError, e:
                raise ImportError('Failed to import %s: %s' % (modname, e))
            return sys.modules[modname]
    except ImportError:
        if not silent:
            raise


class cached_property(object):
    """A decorator that converts a function into a lazy property. The
    function wrapped is called the first time to retrieve the result
    and then that calculated result is used the next time you access
    the value::

        class Foo(object):

            @cached_property
            def foo(self):
                # calculate something important here
                return 42

    The class has to have a `__dict__` in order for this property to
    work.
    """

    # implementation detail: this property is implemented as non-data
    # descriptor. non-data descriptors are only invoked if there is
    # no entry with the same name in the instance's __dict__.
    # this allows us to completely get rid of the access function call
    # overhead. If one choses to invoke __get__ by hand the property
    # will still work as expected because the lookup logic is replicated
    # in __get__ for manual invocation.

    def __init__(self, func):
        self.func = func
        update_wrapper(self, func)

    def __get__(self, obj, owner):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value


