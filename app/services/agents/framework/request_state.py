"""Isolate mutable singleton-agent fields between concurrent requests."""

from contextvars import ContextVar


class RequestValue:
    """A lazily allocated ContextVar per agent instance and attribute."""

    def __init__(self, default=None):
        self.default = default

    def __set_name__(self, owner, name):
        self.name = name
        self.storage_name = f"_request_value_{name}"

    def _variable(self, instance):
        variable = instance.__dict__.get(self.storage_name)
        if variable is None:
            variable = ContextVar(f"mapit_{id(instance)}_{self.name}", default=self.default)
            instance.__dict__[self.storage_name] = variable
        return variable

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return self._variable(instance).get()

    def __set__(self, instance, value):
        self._variable(instance).set(value)
