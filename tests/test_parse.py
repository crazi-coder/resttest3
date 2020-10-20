import unittest

from pytest import fail

from py3resttest.utils import Parser


class ParserTest(unittest.TestCase):
    """ Testing for basic REST test methods, how meta! """

    # Parsing methods
    def test_coerce_to_string(self):
        self.assertEqual(u'1', Parser.coerce_to_string(1))
        self.assertEqual(u'stuff', Parser.coerce_to_string(u'stuff'))
        self.assertEqual(u'stuff', Parser.coerce_to_string('stuff'))
        self.assertEqual(u'st😽uff', Parser.coerce_to_string(u'st😽uff'))
        self.assertRaises(TypeError, Parser.coerce_to_string, {'key': 'value'})
        self.assertRaises(TypeError, Parser.coerce_to_string, None)

    def test_coerce_http_method(self):
        self.assertEqual(u'HEAD', Parser.coerce_http_method(u'hEaD'))
        self.assertEqual(u'HEAD', Parser.coerce_http_method(b'hEaD'))
        self.assertRaises(TypeError, Parser.coerce_http_method, 5)
        self.assertRaises(TypeError, Parser.coerce_http_method, None)
        self.assertRaises(TypeError, Parser.coerce_http_method, u'')

    def test_coerce_string_to_ascii(self):
        self.assertEqual(b'stuff', Parser.coerce_string_to_ascii(u'stuff'))
        self.assertRaises(UnicodeEncodeError, Parser.coerce_string_to_ascii, u'st😽uff')
        self.assertRaises(TypeError, Parser.coerce_string_to_ascii, 1)
        self.assertRaises(TypeError, Parser.coerce_string_to_ascii, None)

    def test_coerce_list_of_ints(self):
        self.assertEqual([1], Parser.coerce_list_of_ints(1))
        self.assertEqual([2], Parser.coerce_list_of_ints('2'))
        self.assertEqual([18], Parser.coerce_list_of_ints(u'18'))
        self.assertEqual([1, 2], Parser.coerce_list_of_ints([1, 2]))
        self.assertEqual([1, 2], Parser.coerce_list_of_ints([1, '2']))

        try:
            val = Parser.coerce_list_of_ints('goober')
            fail("Shouldn't allow coercing a random string to a list of ints")
        except:
            pass


if __name__ == '__main__':
    unittest.main()
