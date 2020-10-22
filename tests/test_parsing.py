# -*- coding: utf-8 -*-
import unittest

from py3resttest.utils import Parser


class TestParsing(unittest.TestCase):
    """ Tests for parsing utility functions """

    def test_encode_unicode_bytes(self):
        val = 8
        unicoded = u'指事字'
        byteform = b'\xe6\x8c\x87\xe4\xba\x8b\xe5\xad\x97'
        num = 156

        self.assertEqual(byteform, Parser.encode_unicode_bytes(unicoded))
        self.assertEqual(byteform, Parser.encode_unicode_bytes(byteform))
        self.assertEqual(b'156', Parser.encode_unicode_bytes(num))

    def test_unicode_templating(self):
        # Unicode template and unicode substitution
        unicode_template_string = u'my name is 指 and my value is $var'
        unicode_variables = {'var': u'漢'}
        normal_variables = {'var': u'bob'}
        substituted = Parser.safe_substitute_unicode_template(unicode_template_string, unicode_variables)
        self.assertEqual(u'my name is 指 and my value is 漢', substituted)

        # Normal template and unicode substitution
        normal_template_string = 'my normal name is blah and my unicode name is $var'
        substituted = Parser.safe_substitute_unicode_template(normal_template_string, unicode_variables)
        self.assertEqual(u'my normal name is blah and my unicode name is 漢', substituted)

        # Unicode template and normal substitution
        substituted = Parser.safe_substitute_unicode_template(unicode_template_string, normal_variables)
        self.assertEqual(u'my name is 指 and my value is bob', substituted)

    def test_flatten(self):
        """ Test flattening of lists of dictionaries to single dictionaries """

        # Test happy path: list of single-item dictionaries in
        array = [{"url": "/cheese"}, {"method": "POST"}]
        expected = {"url": "/cheese", "method": "POST"}
        output = Parser.flatten_dictionaries(array)
        self.assertTrue(isinstance(output, dict))
        # Test that expected output matches actual
        self.assertFalse(len(set(output.items()) ^ set(expected.items())))

        # Test dictionary input
        array = {"url": "/cheese", "method": "POST"}
        expected = {"url": "/cheese", "method": "POST"}
        output = Parser.flatten_dictionaries(array)
        self.assertTrue(isinstance(output, dict))
        # Test that expected output matches actual
        self.assertTrue(len(set(output.items()) ^ set(expected.items())) == 0)

        # Test empty list input
        array = []
        expected = {}
        output = Parser.flatten_dictionaries(array)
        self.assertTrue(isinstance(output, dict))
        # Test that expected output matches actual
        self.assertFalse(len(set(output.items()) ^ set(expected.items())))

        # Test empty dictionary input
        array = {}
        expected = {}
        output = Parser.flatten_dictionaries(array)
        self.assertTrue(isinstance(output, dict))
        # Test that expected output matches actual
        self.assertFalse(len(set(output.items()) ^ set(expected.items())))

        # Test mixed-size input dictionaries
        array = [{"url": "/cheese"}, {"method": "POST", "foo": "bar"}]
        expected = {"url": "/cheese", "method": "POST", "foo": "bar"}
        output = Parser.flatten_dictionaries(array)
        self.assertTrue(isinstance(output, dict))
        # Test that expected output matches actual
        self.assertFalse(len(set(output.items()) ^ set(expected.items())))

    def test_safe_boolean(self):
        """ Test safe conversion to boolean """
        self.assertFalse(Parser.safe_to_bool(False))
        self.assertTrue(Parser.safe_to_bool(True))
        self.assertTrue(Parser.safe_to_bool('True'))
        self.assertTrue(Parser.safe_to_bool('true'))
        self.assertTrue(Parser.safe_to_bool('truE'))
        self.assertFalse(Parser.safe_to_bool('false'))

        # Try things that should throw exceptions
        try:
            boolean = Parser.safe_to_bool('fail')
            raise AssertionError('Failed to throw type error that should have')
        except TypeError:
            pass  # Good

        try:
            boolean = Parser.safe_to_bool([])
            raise AssertionError('Failed to throw type error that should have')
        except TypeError:
            pass  # Good

        try:
            boolean = Parser.safe_to_bool(None)
            raise AssertionError('Failed to throw type error that should have')
        except TypeError:
            pass  # Good

    def test_safe_to_json(self):

        self.assertEqual(u'adj12321nv', Parser.safe_to_json(u'adj12321nv'))

        self.assertEqual(u'5.2', Parser.safe_to_json(5.2))

        class Special(object):
            bal = 5.3
            test = 'stuffing'

            def __init__(self):
                self.newval = 'cherries'

        self.assertEqual({'newval': 'cherries'}, Parser.safe_to_json(Special()))


if __name__ == '__main__':
    unittest.main()
