from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template.loader import select_template
from django.utils.translation import ugettext_lazy as _
from utkik.decorators import http_methods


class ViewException(Exception):
    pass


class ContextData(object):
    """
    A container for attributes to store on the template context.

    All the attributes are later collected as a dictionary via ``__dict__``.
    """


class View(object):
    """
    A minimalist View base class.

    Goals
    -----
    - Building context for rendering should be simple.

    - Source should be easy to follow and encourage this for implementing
      subclasses if possible.

    - Keep methods short and provide useful hooks for sub classing.

    - Embrace the instance and don't pass request nor context around.

    - Narrow the scope to most common use but without limiting less usual
      use-cases.
    """

    methods = ['GET', 'POST'] # allowed HTTP methods
    decorators = [] # a list of decorators
    template = None # template to render to
    ajax_template = None # template to render to for ajax calls

    def __init__(self):
        """
        Create a :class:`ContextData` instance for the view.
        """
        self.c = ContextData() # c is for context
        self.request = None

    def dispatch(self, request, *args, **kwargs):
        """
        View entry point.

        The utkik dispatcher will create a new instance of the current class
        and call this method when the Django handler makes a call to the view.
        """
        self.request = request
        return self._decorate(self.get_response)(request, *args, **kwargs)

    def _decorate(self, func):
        """
        Decorate a function with decorators from :attr:`decorators` and
        decorators based on :attr:`methods`.
        """
        for decorator in reversed(self.decorators):
            func = decorator(func)
        methods = [m for m in self.methods if hasattr(self, m.lower())]
        return http_methods(*methods)(func)

    def get_response(self, request, *args, **kwargs):
        """
        Return the response from a successful request to the view.

        Directs to a suitable handler method based on the HTTP method call.
        If this handler does not return a response, :meth:`render` is called
        and returned.

        Request is just passed in here for decorator compatibility.
        """
        return self.get_handler()(*args, **kwargs) or self.render()

    def get_handler(self):
        """
        Return the method for the current request.

        Override this to change the handler method that is used for a request,
        for example, to use an alternate handler for AJAX calls.
        """
        return getattr(self, self.request.method.lower())

    def get_context_data(self):
        """
        Return a dictionary containing the context data.

        Override this method to add to or modify the context before it is used
        to render a template.

        This is called from :meth:`get_context`.
        """
        return self.c.__dict__

    def get_context(self):
        """
        Return a RequestContext loaded with the context data.

        Override this to change the Context class that is used to render a
        template.

        This is called from :meth:`render`.
        """
        return RequestContext(self.request, self.get_context_data())

    def get_template_names(self):
        """
        Return a list of template to select from when rendering.

        If this is an AJAX request and :attr:`ajax_template` is set, just
        ``[self.ajax_template]`` will be returned.

        If :attr:`template` is set, ``[self.template]`` will be returned.

        Otherwise an empty list will be returned (which will cause the default
        :meth:`render` method to raise a :class:`ViewException`).

        Override this method to dynamically change the template(s).
        """
        if self.request.is_ajax() and self.ajax_template:
            return [self.ajax_template]
        if self.template:
            return [self.template]
        return []

    def render(self):
        """
        Select a template via :meth:`get_template_names` and render it using
        :meth:`get_context`.

        By default, this is called from :meth:`get_response` if the handler
        does not return a response.
        """
        templates = self.get_template_names()
        if not templates:
            raise ViewException(
                _('%s does not define a template to render to.') % self)
        template = select_template(templates)
        return template.render(self.get_context())
