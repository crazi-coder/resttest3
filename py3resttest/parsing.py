import string


def encode_unicode_bytes(my_string):
    """ Shim function, converts Unicode to UTF-8 encoded bytes regardless of the source format
        Intended for python 3 compatibility mode, and b/c PyCurl only takes raw bytes
    """
    if isinstance(my_string, (bytearray, bytes)):
        return my_string
    else:
        my_string = str(my_string)
    if isinstance(my_string, str):
        my_string = my_string.encode('utf-8')

    return my_string


# TODO create a full class that extends string.Template
def safe_substitute_unicode_template(templated_string, variable_map):
    """ Perform string.Template safe_substitute on unicode input with unicode variable values by using escapes
        Catch: cannot accept unicode variable names, just values
        Returns a Unicode type output, if you want UTF-8 bytes, do encode_unicode_bytes on it
    """
    return string.Template(templated_string).safe_substitute(variable_map)


def safe_to_json(in_obj):
    """ Safely get dict from object if present for json dumping """
    if isinstance(in_obj, bytearray):
        return str(in_obj)
    if hasattr(in_obj, '__dict__'):
        return {k: v for k, v in in_obj.__dict__.items() if not k.startswith("___")}
    try:
        return str(in_obj)
    except Exception:
        return repr(in_obj)


def flatten_dictionaries(input_val):
    """ Flatten a list of dictionaries into a single dictionary, to allow flexible YAML use
      Dictionary comprehensions can do this, but would like to allow for pre-Python 2.7 use
      If input isn't a list, just return it.... """
    output = dict()
    if isinstance(input_val, list):
        for _dict in input_val:
            output.update(_dict)
    else:  # Not a list of dictionaries
        output = input_val
    return output


def lowercase_keys(input_dict):
    """ Take input and if a dictionary, return version with keys all lowercase and cast to str """
    if not isinstance(input_dict, dict):
        return input_dict
    safe = dict()
    for key, value in input_dict.items():
        safe[str(key).lower()] = value
    return safe


def safe_to_bool(input_val):
    """ Safely convert user input to a boolean, throwing exception if not boolean or boolean-appropriate string
      For flexibility, we allow case insensitive string matching to false/true values
      If it's not a boolean or string that matches 'false' or 'true' when ignoring case, throws an exception """
    if isinstance(input_val, bool):
        return input_val
    elif isinstance(input_val, str) and input_val.lower() == 'false':
        return False
    elif isinstance(input_val, str) and input_val.lower() == 'true':
        return True
    else:
        raise TypeError(
            'Input Object is not a boolean or string form of boolean!')
