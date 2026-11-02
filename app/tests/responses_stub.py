"""Substituto mínimo de requests.Session para os testes do cliente."""

import json

import requests


class SessionStub:
    def __init__(self):
        self._response = None
        self._error = None
        self.last_params = None

    def reply(self, status, body):
        response = requests.Response()
        response.status_code = status
        response._content = (body if isinstance(body, str) else json.dumps(body)).encode()
        self._response = response

    def fail(self, error):
        self._error = error

    def get(self, url, params=None, timeout=None):
        self.last_params = params
        if self._error:
            raise self._error
        return self._response
