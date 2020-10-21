__version__ = '1.0.0-dev'
__author__ = 'Abhilash Joseph C'

from py3resttest.utils import register_extensions

register_extensions('py3resttest.ext.validator_jsonschema')
register_extensions('py3resttest.ext.extractor_jmespath')
