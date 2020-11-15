__version__ = '1.0.0-dev'
__author__ = 'Abhilash Joseph C'

from resttest3.utils import register_extensions

register_extensions('resttest3.ext.validator_jsonschema')
register_extensions('resttest3.ext.extractor_jmespath')
