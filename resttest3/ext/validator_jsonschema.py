import json
import traceback

import jsonschema
import yaml

from resttest3.constants import FAILURE_VALIDATOR_EXCEPTION
from resttest3.contenthandling import ContentHandler
from resttest3.utils import Parser
from resttest3.validators import AbstractValidator, Failure


class JsonSchemaValidator(AbstractValidator):
    """ Json schema validator using the jsonschema library """

    def __init__(self):
        super(JsonSchemaValidator, self).__init__()
        self.schema_context = None

    def validate(self, body=None, headers=None, context=None):
        schema_text = self.schema_context.get_content(context=context)
        schema = yaml.safe_load(schema_text)
        try:
            if isinstance(body, bytes):
                body = body.decode()
            jsonschema.validate(json.loads(body), schema)
            return True
        except jsonschema.exceptions.ValidationError:
            return self.__failed("JSON Schema Validation Failed")
        except json.decoder.JSONDecodeError:
            trace = traceback.format_exc()
            return self.__failed("Invalid response json body")

    def __failed(self, message):
        trace = traceback.format_exc()
        return Failure(message=message, details=trace, validator=self,
                       failure_type=FAILURE_VALIDATOR_EXCEPTION)

    @staticmethod
    def get_readable_config(context=None):
        return "JSON schema validation"

    @classmethod
    def parse(cls, config):
        validator = JsonSchemaValidator()
        config = Parser.lowercase_keys(config)
        if 'schema' not in config:
            raise ValueError(
                "Cannot create schema validator without a 'schema' configuration element!")
        validator.schema_context = ContentHandler.parse_content(config['schema'])

        return validator


VALIDATORS = {'json_schema': JsonSchemaValidator.parse}
