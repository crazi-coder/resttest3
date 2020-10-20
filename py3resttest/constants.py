from enum import Enum

import pycurl

DEFAULT_TIMEOUT = 10
HEADER_ENCODING = 'ISO-8859-1'  # Per RFC 2616


class YamlKeyWords:
    INCLUDE = 'include'
    IMPORT = 'import'
    TEST = 'test'
    URL = 'url'
    BENCHMARK = 'benchmark'
    CONFIG = 'config'


class TestCaseKeywords:
    auth_username = 'auth_username'
    auth_password = 'auth_password'
    method = 'method'
    delay = 'delay'
    group = 'group'
    name = 'name'
    expected_status = 'expected_status'
    stop_on_failure = 'stop_on_failure'
    url = 'url'
    body = 'body'
    headers = 'headers'
    extract_binds = 'extract_binds'
    variable_binds = 'variable_binds'
    generator_binds = 'generator_binds'
    validators = 'validators'
    options = 'options'


class EnumHttpMethod(Enum):
    GET = pycurl.HTTPGET
    PUT = pycurl.UPLOAD
    PATCH = pycurl.POSTFIELDS
    POST = pycurl.POST
    DELETE = pycurl.CUSTOMREQUEST
    HEAD = pycurl.CUSTOMREQUEST


class AuthType:
    BASIC = pycurl.HTTPAUTH_BASIC
    NONE = pycurl.HTTPAUTH_NONE
