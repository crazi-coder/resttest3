# -*- coding: utf-8 -*-

import unittest

from py3resttest.exception import BindError, HttpMethodError, ValidatorError
from py3resttest.validators import ComparatorValidator, ExtractTestValidator
from pytest import fail

from py3resttest import generators
from py3resttest.binding import Context
from py3resttest.testcase import TestCase


class TestsTest(unittest.TestCase):
    """ Testing for basic REST test methods, how meta! """

    # def test_parse_curloption(self):
    #     """ Verify issue with curloption handling from https://github.com/svanoort/pyresttest/issues/138 """
    #     testdefinition = {"url": "/ping", "curl_option_timeout": 14, 'curl_Option_interface': 'doesnotexist'}
    #     test = Test.parse_test('', testdefinition)
    #     self.assertTrue('TIMEOUT' in test.curl_options)
    #     self.assertTrue('INTERFACE' in test.curl_options)
    #     self.assertEqual(14, test.curl_options['TIMEOUT'])
    #     self.assertEqual('doesnotexist', test.curl_options['INTERFACE'])

    # def test_parse_illegalcurloption(self):
    #     testdefinition = {"url": "/ping", 'curl_Option_special': 'value'}
    #     try:
    #         test = Test.parse_test('', testdefinition)
    #         fail("Error: test parsing should fail when given illegal curl option")
    #     except ValueError:
    #         pass

    def test_parse_test(self):
        """ Test basic ways of creating test objects from input object structure """
        # Most basic case
        _input_dict = {
            "url": "/ping", "method": "DELETE", "NAME": "foo", "group": "bar",
            "body": "<xml>input</xml>", "headers": {"Accept": "Application/json"}
        }
        test = TestCase('', None, None)
        test.parse(_input_dict)
        self.assertEqual(test.url, _input_dict['url'])
        self.assertEqual(test.http_method, _input_dict['method'])
        self.assertEqual(test.name, _input_dict['NAME'])
        self.assertEqual(test.group, _input_dict['group'])
        self.assertEqual(test.body, _input_dict['body'])
        # Test headers match
        self.assertFalse(set(test.headers.values()) ^ set(_input_dict['headers'].values()))

    def test_parse_test_case_sensitivity(self):
        # Happy path, only gotcha is that it's a POST, so must accept 200 or
        # 204 response code
        my_input = {"url": "/ping", "meThod": "POST"}
        test = TestCase('', None, None)
        test.parse(my_input)
        self.assertEqual(test.url, my_input['url'])
        self.assertEqual(test.http_method, my_input['meThod'])

    def test_parse_test_expected_http_status_code(self):
        my_input = {"url": "/ping", "method": "POST"}
        test = TestCase('', None, None)
        test.parse(my_input)
        self.assertEqual(test.expected_http_status_code_list, [200, 201, 204])

    def test_parse_test_auth(self):
        # Authentication
        my_input = {"url": "/ping", "method": "GET",
                    "auth_username": "foo", "auth_password": "bar"}
        test = TestCase('', None, None)
        test.parse(my_input)
        self.assertEqual('foo', my_input['auth_username'])
        self.assertEqual('bar', my_input['auth_password'])
        self.assertEqual(test.expected_http_status_code_list, [200])

    def test_parse_test_basic_header(self):
        # Test that headers propagate
        my_input = {"url": "/ping", "method": "GET",
                    "headers": [{"Accept": "application/json"}, {"Accept-Encoding": "gzip"}]}
        test = TestCase('', None, None)
        test.parse(my_input)
        expected_headers = {"Accept": "application/json",
                            "Accept-Encoding": "gzip"}

        self.assertEqual(test.url, my_input['url'])
        self.assertEqual(test.http_method, 'GET')
        self.assertEqual(test.expected_http_status_code_list, [200])
        self.assertTrue(isinstance(test.headers, dict))

        # Test no header mappings differ
        self.assertFalse(set(test.headers.values()) ^ set(expected_headers.values()))

    def test_parse_test_http_statuscode_with_mixed_type(self):
        # Test expected status propagates and handles conversion to integer
        my_input = [{"url": "/ping"}, {"name": "cheese"},
                    {"expected_status": ["200", 204, "202"]}]
        test = TestCase('', None, None)
        test.parse(my_input)
        self.assertEqual(test.name, "cheese")
        self.assertEqual(test.expected_http_status_code_list, [200, 204, 202])

    def test_parse_nonstandard_http_method(self):
        my_input = {"url": "/ping", "method": "PATCH", "NAME": "foo", "group": "bar",
                   "body": "<xml>input</xml>", "headers": {"Accept": "Application/json"}}
        test = TestCase('', None, None)
        test.parse(my_input)
        self.assertEqual("PATCH", test.http_method)

        try:
            my_input['method'] = 1
            test.parse(my_input)
            fail("Should fail to pass a nonstring HTTP method")
        except AttributeError:
            pass

        try:
            my_input['method'] = ''
            test.parse(my_input)
            fail("Should fail to pass a nonstring HTTP method")
        except HttpMethodError:
            pass

    def test_parse_custom_curl(self):
        raise unittest.SkipTest("Skipping test of CURL configuration")



    # We can't use version specific skipIf decorator b/c python 2.6 unittest lacks it
    def test_use_custom_curl(self):
        """ Test that test method really does configure correctly """

        # In python 3, use of mocks for the curl setopt version (or via setattr)
        # Will not modify the actual curl object... so test fails
        raise unittest.SkipTest("Skipping test of CURL configuration for redirects because the mocks fail")

    def test_basic_auth(self):
        """ Test that basic auth configures correctly """
        # In python 3, use of mocks for the curl setopt version (or via setattr)
        # Will not modify the actual curl object... so test fails
        print("Skipping test of CURL configuration for basic auth because the mocks fail in Py3")
        return

    def test_parse_test_templated_headers(self):
        """ Test parsing with templated headers """

        heads = {"Accept": "Application/json", "$AuthHeader": "$AuthString"}
        templated_heads = {"Accept": "Application/json",
                           "apikey": "magic_passWord"}
        context = Context()
        context.bind_variables(
            {'AuthHeader': 'apikey', 'AuthString': 'magic_passWord'})

        # If this doesn't throw errors we have silent failures
        input_invalid = {"url": "/ping", "method": "DELETE", "NAME": "foo",
                         "group": "bar", "body": "<xml>input</xml>", "headers": 'goat'}
        try:
            test = TestCase('', None, context)
            test.parse(input_invalid)
            fail("Expected error not thrown")
        except ValidatorError:
            pass



    def test_parse_test_validators(self):
        """ Test that for a test it can parse the validators section correctly """
        input = {"url": '/test', 'validators': [
            {'comparator': {
                'jsonpath_mini': 'key.val',
                'comparator': 'eq',
                'expected': 3
            }},
            {'extract_test': {'jsonpath_mini': 'key.val', 'test': 'exists'}}
        ]}

        test = TestCase('', None, None)
        test.parse(input)
        self.assertTrue(test.validators)
        self.assertEqual(2, len(test.validators))
        self.assertTrue(isinstance(
            test.validators[0], ComparatorValidator))
        self.assertTrue(isinstance(
            test.validators[1], ExtractTestValidator))

        # Check the validators really work
        self.assertTrue(test.validators[0].validate(
            '{"id": 3, "key": {"val": 3}}'))

    def test_parse_validators_fail(self):
        """ Test an invalid validator syntax throws exception """
        input = {"url": '/test', 'validators': ['comparator']}
        try:
            test = TestCase('', None, None)
            test.parse(input)
            self.fail(
                "Should throw exception if not giving a dictionary-type comparator")
        except ValidatorError:
            pass

    def test_parse_extractor_bind(self):
        """ Test parsing of extractors """
        test_config = {
            "url": '/api',
            'extract_binds': {
                'id': {'jsonpath_mini': 'idfield'},
                'name': {'jsonpath_mini': 'firstname'}
            }
        }
        context = Context()
        test = TestCase('', None, None, context)
        test.parse(test_config)
        test.pre_update(context)
        # self.assertTrue(test.extract_binds)
        # self.assertEqual(2, len(test.extract_binds))
        # self.assertTrue('id' in test.extract_binds)
        # self.assertTrue('name' in test.extract_binds)
        #
        # # Test extractors config'd correctly for extraction
        # myjson = '{"idfield": 3, "firstname": "bob"}'
        # extracted = test.extract_binds['id'].extract(myjson)
        # self.assertEqual(3, extracted)
        #
        # extracted = test.extract_binds['name'].extract(myjson)
        # self.assertEqual('bob', extracted)

    def test_parse_extractor_errors(self):
        """ Test that expected errors are thrown on parsing """
        test_config = {
            "url": '/api',
            'extract_binds': {'id': {}}
        }
        try:
            test = TestCase('', None, None)
            test.parse(test_config)
            self.fail("Should throw an error when doing empty mapping")
        except BindError:
            pass

        test_config['extract_binds']['id'] = {
            'jsonpath_mini': 'query',
            'test': 'anotherquery'
        }
        try:
            test = TestCase('', None, None)
            test.parse(test_config)
            self.fail("Should throw an error when given multiple extractors")
        except BindError as te:
            pass

    def test_parse_validator_comparator(self):
        """ Test parsing a comparator validator """
        test_config = {
            'name': 'Default',
            'url': '/api',
            'validators': [
                {'comparator': {'jsonpath_mini': 'id',
                                'comparator': 'eq',
                                'expected': {'template': '$id'}}}
            ]
        }
        test = TestCase('', None, None)
        test.parse(test_config)
        self.assertTrue(test.validators)
        self.assertEqual(1, len(test.validators))

        context = Context()
        context.bind_variable('id', 3)

        myjson = '{"id": "3"}'
        failure = test.validators[0].validate(myjson, context=context)
        self.assertTrue(test.validators[0].validate(myjson, context=context))
        self.assertFalse(test.validators[0].validate(myjson))

    def test_parse_validator_extract_test(self):
        """ Tests parsing extract-test validator """
        test_config = {
            'name': 'Default',
            'url': '/api',
            'validators': [
                {'extract_test': {'jsonpath_mini': 'login',
                                  'test': 'exists'}}
            ]
        }
        test = TestCase('', None, None)
        test.parse(test_config)
        self.assertTrue(test.validators)
        self.assertEqual(1, len(test.validators))

        myjson = '{"login": "testval"}'
        self.assertTrue(test.validators[0].validate(myjson))

    def test_variable_binding(self):
        """ Test that tests successfully bind variables """
        element = 3
        test_config = [{"url": "/ping"}, {"name": "cheese"},
                 {"expected_status": ["200", 204, "202"]}]
        test_config.append({"variable_binds": {'var': 'value'}})
        context = Context()
        test = TestCase('', None, context)
        test.parse(test_config)
        binds = test.variable_binds
        self.assertEqual(1, len(binds))
        self.assertEqual('value', binds['var'])

        # Test that updates context correctly

        test.pre_update(context)
        self.assertEqual('value', context.get_value('var'))


    # def test_test_url_templating(self):
    #     test = Test()
    #     test.set_url('$cheese', isTemplate=True)
    #     self.assertTrue(test.is_dynamic())
    #     self.assertEqual('$cheese', test.get_url())
    #     self.assertTrue(test.templates['url'])
    #
    #     context = Context()
    #     context.bind_variable('cheese', 'stilton')
    #     self.assertEqual('stilton', test.get_url(context=context))
    #
    #     realized = test.realize(context)
    #     self.assertEqual('stilton', realized.url)

    # def test_test_content_templating(self):
    #     test = Test()
    #     handler = ContentHandler()
    #     handler.is_template_content = True
    #     handler.content = '{"first_name": "Gaius","id": "$id","last_name": "Baltar","login": "$login"}'
    #     context = Context()
    #     context.bind_variables({'id': 9, 'login': 'kvothe'})
    #     test.set_body(handler)
    #
    #     templated = test.realize(context=context)
    #     self.assertEqual(string.Template(handler.content).safe_substitute(context.get_values()),
    #                      templated.body)

    # def test_header_templating(self):
    #     test = Test()
    #     head_templated = {'$key': "$val"}
    #     context = Context()
    #     context.bind_variables({'key': 'cheese', 'val': 'gouda'})
    #
    #     # No templating applied
    #     test.headers = head_templated
    #     head = test.get_headers()
    #     self.assertEqual(1, len(head))
    #     self.assertEqual('$val', head['$key'])
    #
    #     test.set_headers(head_templated, is_template=True)
    #     self.assertTrue(test.templates)
    #     self.assertTrue(test.NAME_HEADERS in test.templates)
    #
    #     # No context, no templating
    #     head = test.headers
    #     self.assertEqual(1, len(head))
    #     self.assertEqual('$val', head['$key'])
    #
    #     # Templated with context
    #     head = test.get_headers(context=context)
    #     self.assertEqual(1, len(head))
    #     self.assertEqual('gouda', head['cheese'])

    def test_update_context_variables(self):
        variable_binds = {'foo': 'correct', 'test': 'value'}
        context = Context()
        test = TestCase('', None, variable_binds, context=context)
        context.bind_variable('foo', 'broken')
        test.pre_update(context)
        self.assertEqual('correct', context.get_value('foo'))
        self.assertEqual('value', context.get_value('test'))

    def test_update_context_generators(self):
        """ Test updating context variables using generator """
        variable_binds = {'foo': 'initial_value'}
        generator_binds = {'foo': 'gen'}
        context = Context()
        test = TestCase('', None, variable_binds, context=context)
        test.generator_binds = generator_binds
        context.bind_variable('foo', 'broken')
        context.add_generator('gen', generators.generator_basic_ids())
        context.bind_generator_next('foo', 'gen')
        self.assertEqual(1, context.get_value('foo'))
        context.bind_generator_next('foo', 'gen')
        self.assertEqual(2, context.get_value('foo'))


if __name__ == '__main__':
    unittest.main()
