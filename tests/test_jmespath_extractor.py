import unittest

from resttest3.ext.extractor_jmespath import JMESPathExtractor


class MTestJMESPathExtractor(unittest.TestCase):

    def setUp(self) -> None:
        self.ext = JMESPathExtractor()

    def test_extract_internal(self):
        unicoded_body = '{"test":"指事字"}'
        b = bytes('{"test":23}', 'utf-8')

        self.ext.extract_internal('test', None, unicoded_body)
        data = self.ext.extract_internal('test', None, b)
        self.assertEqual(data, 23)
        self.assertRaises(ValueError, self.ext.extract_internal, 'test', None, 'abc')


if __name__ == '__main__':
    unittest.main()
