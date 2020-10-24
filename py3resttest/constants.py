import operator
import re
from enum import Enum

import pycurl

DEFAULT_TIMEOUT = 10
HEADER_ENCODING = 'ISO-8859-1'  # Per RFC 2616


def safe_length(var):
    """ Exception-safe length check, returns -1 if no length on type or error """
    try:
        output = len(var)
    except TypeError:
        output = -1
    return output


def regex_compare(input_val, regex):
    return bool(re.search(regex, input_val))


def test_type(val, _type):
    type_list = TYPES.get(_type.lower())

    if type_list is None:
        raise TypeError(
            "Type {0} is not a valid type to test against!".format(_type.lower()))
    try:
        for type_obj in type_list:
            if isinstance(val, type_obj):
                return True
        return False
    except TypeError:
        return isinstance(val, type_list)


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
    global_env = 'global_env'


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


FAILURE_INVALID_RESPONSE = 'Invalid HTTP Response Code'
FAILURE_CURL_EXCEPTION = 'Curl Exception'
FAILURE_TEST_EXCEPTION = 'Test Execution Exception'
FAILURE_VALIDATOR_FAILED = 'Validator Failed'
FAILURE_VALIDATOR_EXCEPTION = 'Validator Exception'
FAILURE_EXTRACTOR_EXCEPTION = 'Extractor Exception'


COMPARATORS = {
    "count_eq": lambda x, y: safe_length(x) == y,
    "str_eq": lambda x, y: operator.eq(str(x), str(y)),
    "contains": lambda x, y: x and operator.contains(x, y),
    "contained_by": lambda x, y: y and operator.contains(y, x),
    "regex": lambda x, y: regex_compare(str(x), str(y)),
    "type": lambda x, y: test_type(x, y),
    "eq": operator.eq,
    "ne": operator.ne,
    "lt": operator.lt,
    "le": operator.le,
    "ge": operator.ge,
    "gt": operator.gt

}

TYPES = {
    'null': type(None),
    'none': type(None),
    'number': (int, float),
    'int': (int,),
    'float': float,
    'boolean': bool,
    'string': str,
    'array': list,
    'list': list,
    'dict': dict,
    'map': dict,
    'scalar': (bool, int, float, str, type(None)),
    'collection': (list, dict, set)
}

VALIDATOR_TESTS = {
    'exists': lambda x: x is not None,
    'not_exists': lambda x: x is None
}
