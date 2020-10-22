import logging
import os
import string
import threading
from email import message_from_string
from functools import reduce
from pathlib import Path
from typing import Dict, Union, List

import yaml

from py3resttest.generators import register_generator
from py3resttest.validators import register_test, register_comparator, register_extractor
from py3resttest.validators import register_validator

logger = logging.getLogger('py3resttest')


class ChangeDir:
    """Context manager for changing the current working directory"""
    DIR_LOCK = threading.RLock()  # Guards operations changing the working directory

    def __init__(self, new_path):
        self.new_path = str(Path(new_path).resolve())
        self.saved_path = None

    def __enter__(self):
        if self.new_path:  # Don't CD to nothingness
            ChangeDir.DIR_LOCK.acquire()
            self.saved_path = os.getcwd()
            os.chdir(self.new_path)
        return self

    def __exit__(self, etype, value, traceback):
        if self.new_path:  # Don't CD to nothingness
            os.chdir(self.saved_path)
            ChangeDir.DIR_LOCK.release()


def read_testcase_file(path):
    with open(path, "r") as f:
        testcase = yaml.safe_load(f.read())
    return testcase


class Parser:

    @staticmethod
    def encode_unicode_bytes(my_string):
        """ Shim function, converts Unicode to UTF-8 encoded bytes regardless of the source format
            Intended for python 3 compatibility mode, and b/c PyCurl only takes raw bytes
        """
        if isinstance(my_string, (bytearray, bytes)):
            return my_string
        else:
            my_string = str(my_string)
            my_string = my_string.encode('utf-8')

        return my_string

    @staticmethod
    def safe_substitute_unicode_template(templated_string, variable_map):
        """ Perform string.Template safe_substitute on unicode input with unicode variable values by using escapes
            Catch: cannot accept unicode variable names, just values
            Returns a Unicode type output, if you want UTF-8 bytes, do encode_unicode_bytes on it
        """
        return string.Template(templated_string).safe_substitute(variable_map)

    @staticmethod
    def safe_to_json(in_obj):
        """ Safely get dict from object if present for json dumping """
        if isinstance(in_obj, bytes):
            return in_obj.decode('utf-8')
        elif hasattr(in_obj, '__dict__'):
            return {k: v for k, v in in_obj.__dict__.items() if not k.startswith('__')}
        elif isinstance(in_obj, str):
            return in_obj
        else:
            return repr(in_obj)

    @staticmethod
    def flatten_dictionaries(input_dict: Union[Dict, List[Dict]]):
        """ Flatten a list of dictionaries into a single dictionary, to allow flexible YAML use
          Dictionary comprehensions can do this, but would like to allow for pre-Python 2.7 use
          If input isn't a list, just return it.... """

        if isinstance(input_dict, list):
            output = reduce(lambda d, src: d.update(src) or d, input_dict, {})
        else:
            output = input_dict
        return output

    @staticmethod
    def lowercase_keys(input_dict):
        """ Take input and if a dictionary, return version with keys all lowercase and cast to str """
        if not isinstance(input_dict, dict):
            return input_dict
        return {str(k).lower(): v for k, v in input_dict.items()}

    @staticmethod
    def flatten_lowercase_keys_dict(input_dict: Union[Dict, List[Dict]]):
        """ Take input and if a dictionary, return version with keys all lowercase and cast to str """
        if isinstance(input_dict, list):
            output_dict = Parser.flatten_dictionaries(input_dict)
            output_dict = Parser.lowercase_keys(output_dict)
        elif not isinstance(input_dict, dict):
            return input_dict
        else:
            output_dict = Parser.lowercase_keys(input_dict)
        return output_dict

    @staticmethod
    def safe_to_bool(vaule):
        """ Safely convert user input to a boolean, throwing exception if not boolean or boolean-appropriate string
          For flexibility, we allow case insensitive string matching to false/true values
          If it's not a boolean or string that matches 'false' or 'true' when ignoring case, throws an exception """
        if isinstance(vaule, bool):
            return vaule
        elif isinstance(vaule, str) and vaule.lower() == 'false':
            return False
        elif isinstance(vaule, str) and vaule.lower() == 'true':
            return True
        else:
            raise TypeError(
                'Input Object is not a boolean or string form of boolean!')

    @staticmethod
    def coerce_to_string(val):
        if isinstance(val, str):
            return val
        elif isinstance(val, int):
            return str(val)
        elif isinstance(val, (bytes, bytearray)):
            return val.decode('utf-8')
        else:
            raise TypeError("Input {0} is not a string or integer, and it needs to be!".format(val))

    @staticmethod
    def coerce_string_to_ascii(val):
        if isinstance(val, str):
            return val.encode('ascii')
        elif isinstance(val, bytes):
            return val.decode('utf-8').encode('ascii')
        else:
            raise TypeError("Input {0} is not a string, string expected".format(val))

    @staticmethod
    def coerce_http_method(val):
        try:
            val = val.decode()
        except (UnicodeDecodeError, AttributeError):
            pass
        if not isinstance(val, str) or len(val) == 0:
            raise TypeError("Invalid HTTP method name: input {0} is not a string or has 0 length".format(val))

        return val.upper()

    @staticmethod
    def coerce_list_of_ints(val):
        """ If single value, try to parse as integer, else try to parse as list of integer """
        if isinstance(val, list):
            return [int(x) for x in val]
        else:
            return [int(val)]

    @staticmethod
    def parse_headers(header_string):
        """ Parse a header-string into individual headers
            Implementation based on: http://stackoverflow.com/a/5955949/95122
            Note that headers are a list of (key, value) since duplicate headers are allowed
            NEW NOTE: keys & values are unicode strings, but can only contain ISO-8859-1 characters
        """
        if isinstance(header_string, bytes):
            header_string = header_string.decode()
        # First line is request line, strip it out
        if not header_string:
            return list()
        request, headers = header_string.split('\r\n', 1)
        if not headers:
            return list()

        header_msg = message_from_string(headers)
        # Note: HTTP headers are *case-insensitive* per RFC 2616
        return [(k.lower(), v) for k, v in header_msg.items()]







def register_extensions(modules):
    """ Import the modules and register their respective extensions """
    if isinstance(modules, str):  # Catch supplying just a string arg
        modules = [modules]
    for ext in modules:
        # Get the package prefix and final module name
        segments = ext.split('.')
        module = segments.pop()
        package = '.'.join(segments)
        # Necessary to get the root module back
        module = __import__(ext, globals(), locals(), package)

        # Extensions are registered by applying a register function to sets of
        # registry name/function pairs inside an object
        extension_applies = {
            'VALIDATORS': register_validator,
            'COMPARATORS': register_comparator,
            'VALIDATOR_TESTS': register_test,
            'EXTRACTORS': register_extractor,
            'GENERATORS': register_generator
        }

        has_registry = False
        for registry_name, register_function in extension_applies.items():
            if hasattr(module, registry_name):
                registry = getattr(module, registry_name)
                for key, val in registry.items():
                    register_function(key, val)
                if registry:
                    has_registry = True

        if not has_registry:
            raise ImportError(
                "Extension to register did not contain any registries: {0}".format(ext))
