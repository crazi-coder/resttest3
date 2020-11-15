"""JMESPathExtractor file"""
import json

import jmespath

from resttest3.validators import AbstractExtractor


class JMESPathExtractor(AbstractExtractor):
    """ Extractor that uses JMESPath syntax
        See http://jmespath.org/specification.html for details
    """
    extractor_type = 'jmespath'
    is_body_extractor = True

    def extract_internal(self, query=None, body=None, headers=None, args=None):
        if isinstance(body, bytes):
            body = body.decode('utf-8')

        try:
            res = jmespath.search(query, json.loads(body))
            return res
        except Exception as Exe:
            raise ValueError("Invalid query: " + query + " : " + str(Exe)) from Exe

    @classmethod
    def parse(cls, config):
        """Parse the JMESPathExtractor config dict"""
        base = JMESPathExtractor()
        return cls.configure_base(config, base)


EXTRACTORS = {'jmespath': JMESPathExtractor.parse}
