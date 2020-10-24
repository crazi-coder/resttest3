import json
import logging
import os
import string
import traceback
from abc import abstractmethod, ABCMeta
from typing import Dict, List, Union, Optional

from py3resttest.constants import COMPARATORS, FAILURE_EXTRACTOR_EXCEPTION, FAILURE_VALIDATOR_FAILED, VALIDATOR_TESTS

logger = logging.getLogger('py3resttest.validators')

EXTRACTORS = {}
VALIDATORS = {}


class Failure:

    def __init__(self, message=None, details=None, failure_type=None, validator=None):
        self.message = message
        self.details = details
        self.validator = validator
        self.failure_type = failure_type

    def __bool__(self):
        """ Failure objects test as False, simplifies coding with them """
        return False

    def __str__(self):
        return self.message


class AbstractExtractor(metaclass=ABCMeta):
    """ Basic extractor, you only need to implement full_extract """

    def __init__(self):
        self.extractor_type = None
        self.query = None
        self._is_templated = False
        self.args = None
        self._is_body_extractor = None
        self._is_header_extractor = None

    @property
    def is_templated(self):
        return self._is_templated

    @is_templated.setter
    def is_templated(self, val):
        self._is_templated = bool(val)

    @property
    def is_body_extractor(self):
        return self._is_body_extractor

    def __str__(self):
        return "Extractor type: {0}, query: {1}, is_templated: {2}, args: {3}".format(
            self.extractor_type, self.query, self.is_templated, self.args)

    @abstractmethod
    def extract_internal(self, query=None, body=None, headers=None, args=None):
        """ Do extraction, query should be pre-templated """
        pass

    def extract(self, body=None, headers=None, context=None):
        """ Extract data """

        query = self.templated_query(context=context)
        return self.extract_internal(query=query, body=body, headers=headers, args=self.args)

    def templated_query(self, context=None):
        if context and self.is_templated:
            query = string.Template(self.query).safe_substitute(
                context.get_values())
            return query
        else:
            return self.query

    def get_readable_config(self, context=None):
        """ Print a human-readable version of the configuration """
        query = self.templated_query(context=context)
        output = 'Extractor Type: {0},  Query: "{1}", Templated?: {2}'.format(
            self.extractor_type, query, self.is_templated)
        if self.args:
            args_string = ", Args: " + str(self.args)
            output = output + args_string
        return output

    @classmethod
    def configure_base(cls, config, extractor_base):
        """ Parse config object and do basic config on an Extractor
        """

        if isinstance(config, dict):
            try:
                config = config['template']
                extractor_base.is_templated = True
                extractor_base.query = config
            except KeyError:
                raise ValueError(
                    "Cannot define a dictionary config for abstract extractor without it having template key")
        elif isinstance(config, str):
            extractor_base.query = config
            extractor_base.is_templated = False
        else:
            raise TypeError(
                "Base extractor must have a string or {template: querystring} configuration node!")
        return extractor_base


class MiniJsonExtractor(AbstractExtractor):
    """ Extractor that uses jsonpath_mini syntax
        IE key.key or array_index.key extraction
    """

    def __init__(self):
        super(MiniJsonExtractor, self).__init__()
        self.extractor_type = 'jsonpath_mini'
        self._is_body_extractor = True

    def extract_internal(self, query=None, args=None, body=None, headers=None):

        if isinstance(body, bytes):
            body = body.decode()
        try:
            body = json.loads(body)
            return self.query_dictionary(query, body)
        except ValueError:
            raise ValueError("Not legal JSON!")

    @staticmethod
    def query_dictionary(query: str, dictionary: Union[List, Dict], delimiter='.') -> Optional[Dict]:
        """ Do an xpath-like query with dictionary, using a template if relevant """
        try:
            stripped_query = query.strip(delimiter)
            if stripped_query:
                for x in stripped_query.split(delimiter):
                    try:
                        dictionary = dictionary[int(x)]
                    except ValueError:
                        dictionary = dictionary[x]
        except Exception:
            return None
        return dictionary

    @classmethod
    def parse(cls, config):
        base = MiniJsonExtractor()
        return cls.configure_base(config, base)


class HeaderExtractor(AbstractExtractor):
    """ Extractor that pulls out a named header value... or list of values if multiple values defined """

    def __init__(self):
        super(HeaderExtractor, self).__init__()
        self.extractor_type = 'header'
        self._is_header_extractor = True

    def extract_internal(self, query=None, args=None, body=None, headers=None):
        low = query.lower()
        # Value for all matching key names
        extracted = [y[1] for y in filter(lambda x: x[0] == low, headers)]
        if len(extracted) == 0:
            raise ValueError("Invalid header name {0}".format(query))
        elif len(extracted) == 1:
            return extracted[0]
        else:
            return extracted

    @classmethod
    def parse(cls, config):
        base = HeaderExtractor()
        return cls.configure_base(config, base)


class RawBodyExtractor(AbstractExtractor):
    """ Extractor that returns the full request body """

    def __init__(self):
        super(RawBodyExtractor, self).__init__()
        self.extractor_type = 'raw_body'
        self._is_header_extractor = False
        self._is_body_extractor = True

    def extract_internal(self, query=None, args=None, body=None, headers=None):
        return body

    @classmethod
    def parse(cls, _):
        base = RawBodyExtractor()
        return base


def _get_extractor(config_dict):
    """ Utility function, get an extract function for a single valid extractor name in config
        and error if more than one or none """
    for key, value in config_dict.items():
        if key in EXTRACTORS:
            return parse_extractor(key, value)
    else:  # No valid extractor
        raise Exception(
            'No valid extractor name to use in input: {0}'.format(config_dict))


class AbstractValidator(metaclass=ABCMeta):
    """ Encapsulates basic validator handling """

    def __init__(self):
        self.name = None
        self.config = None
        self.expected = None
        self.extractor = None
        self.comparator = None
        self.comparator_name = None
        self.is_template_expected = None

    @abstractmethod
    def validate(self, body=None, headers=None, context=None):
        """ Run the validation function, return true or a Failure """
        pass


class ComparatorValidator(AbstractValidator):
    """ Does extract and compare from request body   """

    def __init__(self):
        super(ComparatorValidator, self).__init__()
        self.name = 'ComparatorValidator'

    def get_readable_config(self, context=None):
        """ Get a human-readable config string """
        frag_list = ["Extractor: %s" % self.extractor.get_readable_config(context=context)]

        if isinstance(self.expected, AbstractExtractor):
            frag_list.append("Expected value extractor: %s" % self.expected.get_readable_config(context=context))
        elif self.is_template_expected:
            frag_list.append('Expected is templated, raw value: {0}'.format(self.expected))
        return os.linesep.join(frag_list)

    def validate(self, body=None, headers=None, context=None):
        try:
            extracted_val = self.extractor.extract(
                body=body, headers=headers, context=context)
        except Exception:
            trace = traceback.format_exc()
            return Failure(message="Extractor threw exception", details=trace, validator=self,
                           failure_type=FAILURE_EXTRACTOR_EXCEPTION)

        if isinstance(self.expected, AbstractExtractor):
            try:
                expected_val = self.expected.extract(body=body, headers=headers, context=context)
            except Exception:
                trace = traceback.format_exc()
                return Failure(message="Expected value extractor threw exception", details=trace, validator=self,
                               failure_type=FAILURE_EXTRACTOR_EXCEPTION)
        elif self.is_template_expected and context:
            expected_val = string.Template(
                self.expected).safe_substitute(context.get_values())
        else:
            expected_val = self.expected

        # Handle a bytes-based body and a unicode expected value seamlessly
        if isinstance(extracted_val, bytes) and isinstance(expected_val, str):
            expected_val = expected_val.encode('utf-8')
        comparison = self.comparator(extracted_val, expected_val)

        if not comparison:
            failure = Failure(validator=self)
            if self.comparator_name in ("count_eq", "length_eq"):  # Thanks @KellyBennett

                failure.message = "Comparison failed, evaluating {0}({1}, {2}) returned False".format(
                    self.comparator_name, extracted_val, len(expected_val))
            else:
                failure.message = "Comparison failed, evaluating {0}({1}, {2}) returned False".format(
                    self.comparator_name, extracted_val, expected_val)
            failure.details = self.get_readable_config(context=context)
            failure.failure_type = FAILURE_VALIDATOR_FAILED
            return failure
        else:
            return True

    @staticmethod
    def parse(config):
        """ Create a validator that does an extract from body and applies a comparator,
            Then does comparison vs expected value
            Syntax sample:
              { jsonpath_mini: 'node.child',
                operator: 'eq',
                expected: 'myValue'
              }
        """
        from py3resttest.utils import Parser
        output = ComparatorValidator()
        config = Parser.lowercase_keys(Parser.flatten_dictionaries(config))
        output.config = config

        output.extractor = _get_extractor(config)

        if output.extractor is None:
            raise ValueError(
                "Extract function for comparison is not valid or not found!")

        if 'comparator' not in config:  # Equals comparator if unspecified
            output.comparator_name = 'eq'
        else:
            output.comparator_name = config['comparator'].lower()
        try:
            output.comparator = COMPARATORS[output.comparator_name]
        except KeyError:
            raise ValueError("Invalid comparator given! %s  "
                             "available options are %s" % (output.comparator_name, COMPARATORS.keys()))
        if not output.comparator:
            raise ValueError("Invalid comparator given!")

        try:
            expected = config['expected']
        except KeyError:
            raise ValueError(
                "No expected value found in comparator validator config, one must be!")

        # Expected value can be another extractor query, or a single value, or
        # a templated value

        if isinstance(expected, str) or isinstance(expected, (int, float, complex)):
            output.expected = expected
        elif isinstance(expected, dict):

            expected = Parser.lowercase_keys(expected)
            template = expected.get('template')
            if template:  # Templated string
                if not isinstance(template, str):
                    raise ValueError(
                        "Can't template a comparator-validator unless template value is a string")
                output.is_template_expected = True
                output.expected = template
            else:  # Extractor to compare against
                output.expected = _get_extractor(expected)
                if not output.expected:
                    raise ValueError(
                        "Can't supply a non-template, non-extract dictionary to comparator-validator")

        return output


class ExtractTestValidator(AbstractValidator):
    """ Does extract and test from request body """
    def __init__(self):
        super(ExtractTestValidator, self).__init__()
        self.name = 'ExtractTestValidator'
        self.test_fn = None
        self.test_name = None

    def get_readable_config(self, context=None):
        """ Get a human-readable config string """
        return "Extractor: " + self.extractor.get_readable_config(context=context)

    @staticmethod
    def parse(config):
        from py3resttest.utils import Parser
        output = ExtractTestValidator()
        config = Parser.lowercase_keys(Parser.flatten_dictionaries(config))
        output.config = config
        extractor = _get_extractor(config)
        output.extractor = extractor

        test_name = config['test']
        output.test_name = test_name
        test_fn = VALIDATOR_TESTS[test_name]
        output.test_fn = test_fn
        return output

    def validate(self, body=None, headers=None, context=None):
        try:
            extracted = self.extractor.extract(
                body=body, headers=headers, context=context)
        except Exception:
            trace = traceback.format_exc()
            return Failure(message="Exception thrown while running extraction from body", details=trace, validator=self,
                           failure_type=FAILURE_EXTRACTOR_EXCEPTION)

        tested = self.test_fn(extracted)
        if tested:
            return True
        else:
            failure = Failure(details=self.get_readable_config(
                context=context), validator=self, failure_type=FAILURE_VALIDATOR_FAILED)
            failure.message = "Extract and test validator failed on test: {0}({1})".format(
                self.test_name, extracted)
            # TODO can we do better with details?
            return failure


def parse_extractor(extractor_type, config):
    """ Convert extractor type and config to an extractor instance
        Uses registered parse function for that extractor type
        Parse functions may return either:
            - An extraction function (wrapped in an Extractor instance with configs and returned)
            - OR a a full Extractor instance (configured)
    """
    parse = EXTRACTORS.get(extractor_type.lower())
    if not parse:
        raise ValueError(
            "Extractor {0} is not a valid extractor type".format(extractor_type))
    parsed = parse(config)

    if isinstance(parsed, AbstractExtractor):  # Parser gave a full extractor
        return parsed

    # Look for matching attributes... simple inheritance has issues because of
    # cross-module loading
    items = AbstractExtractor().__dict__
    if set(parsed.__dict__.keys()).issuperset(set(items.keys())):
        return parsed
    else:
        raise TypeError(
            "Parsing functions for extractors must return an AbstractExtractor instance!")


def parse_validator(name, config_node):
    '''Parse a validator from configuration and use it '''
    name = name.lower()
    if name not in VALIDATORS:
        raise ValueError(
            "Name {0} is not a named validator type!".format(name))
    valid = VALIDATORS[name](config_node)

    if valid.name is None:  # Carry over validator name if none set in parser
        valid.name = name
    if valid.config is None:  # Store config info if absent
        valid.config = config_node
    return valid


def register_validator(name, parse_function):
    ''' Registers a validator for use by this library
        Name is the string name for validator

        Parse function does parse(config_node) and returns a Validator object
        Validator functions have signature:
            validate(response_body, context=None) - context is a bindings.Context object

        Validators return true or false and optionally can return a Failure instead of false
        This allows for passing more details
    '''

    name = name.lower()
    if name in VALIDATORS:
        raise Exception("Validator exists with this name: {0}".format(name))

    VALIDATORS[name] = parse_function


def register_extractor(extractor_name, parse_function):
    """ Register a new body extraction function """
    if not isinstance(extractor_name, str):
        raise TypeError("Cannot register a non-string extractor name")
    if extractor_name.lower() == 'comparator':
        raise ValueError(
            "Cannot register extractors called 'comparator', that is a reserved name")
    elif extractor_name.lower() == 'test':
        raise ValueError(
            "Cannot register extractors called 'test', that is a reserved name")
    elif extractor_name.lower() == 'expected':
        raise ValueError(
            "Cannot register extractors called 'expected', that is a reserved name")
    elif extractor_name in EXTRACTORS:
        raise ValueError(
            "Cannot register an extractor name that already exists: {0}".format(extractor_name))
    EXTRACTORS[extractor_name] = parse_function


def register_test(test_name, test_function):
    """ Register a new one-argument test function """
    if not isinstance(test_name, str):
        raise TypeError("Cannot register a non-string test name")
    elif test_name in VALIDATOR_TESTS:
        raise ValueError(
            "Cannot register a test name that already exists: {0}".format(test_name))
    VALIDATOR_TESTS[test_name] = test_function


def register_comparator(comparator_name, comparator_function):
    """ Register a new twpo-argument comparator function returning true or false """
    if not isinstance(comparator_name, str):
        raise TypeError("Cannot register a non-string comparator name")
    elif comparator_name in COMPARATORS:
        raise ValueError(
            "Cannot register a comparator name that already exists: {0}".format(comparator_name))
    COMPARATORS[comparator_name] = comparator_function


# --- REGISTRY OF EXTRACTORS AND VALIDATORS ---
register_extractor('jsonpath_mini', MiniJsonExtractor.parse)
register_extractor('header', HeaderExtractor.parse)
register_extractor('raw_body', RawBodyExtractor.parse)
register_validator('comparator', ComparatorValidator.parse)
register_validator('compare', ComparatorValidator.parse)
register_validator('assertEqual', ComparatorValidator.parse)
register_validator('extract_test', ExtractTestValidator.parse)
register_validator('assertTrue', ExtractTestValidator.parse)
