import unittest
from inspect import getframeinfo, currentframe
from pathlib import Path

import yaml

from py3resttest.binding import Context
from py3resttest.testcase import TestCaseConfig, TestSet, TestCase
from py3resttest.validators import MiniJsonExtractor

filename = getframeinfo(currentframe()).filename
current_module_path = Path(filename)


class TestTestCase(unittest.TestCase):

    def setUp(self) -> None:
        with open("%s/content-test.yaml" % current_module_path.parent, 'r') as f:
            self.test_dict_list = yaml.safe_load(f.read())

    def test_testcase_set_config(self):
        conf = TestCaseConfig()
        conf.parse(self.test_dict_list[0]['config'])
        self.assertEqual({'headername': 'Content-Type', 'headervalue': 'application/json'}, conf.variable_binds)

    def test_testset(self):
        ts = TestSet()
        ts.parse('', self.test_dict_list)
        self.assertIsInstance(ts.test_group_list_dict, dict)
        group = ts.test_group_list_dict["NO GROUP"]
        self.assertEqual(group.variable_binds, {'headername': 'Content-Type', 'headervalue': 'application/json'})

    def test_config(self):
        config_object = TestCaseConfig()
        context = Context()
        config_list = [
            {
                'variable_binds': {'content_type': 'application/json', 'pid': 5}
            }
        ]
        config_object.parse(config_list)

        test_case = TestCase('', None, None, context, config=config_object)
        self.assertEqual(test_case.variable_binds, {'content_type': 'application/json', 'pid': 5})
        testcase_list = [
            {'name': 'Create/update person 7, no template'}, {'url': '/api/person/7/'}, {'method': 'PUT'},
            {'headers': {'template': {'Content-Type': '$content_type'}}},
            {'body': '{"first_name": "Gaius","id": "7","last_name": "Romani","login": "gromani"}'}
        ]
        test_case.parse(testcase_list)
        test_case.pre_update(context)
        self.assertEqual({'Content-Type': 'application/json'}, test_case.headers)

        testcase_list = [
            {'name': 'Create/update person 7, no template'}, {'url': {'template': '/api/person/$pid/'}},
            {'method': 'PUT'},
            {'headers': {'template': {'Content-Type': '$content_type'}}},
            {'body': '{"first_name": "Gaius","id": "7","last_name": "Romani","login": "gromani"}'},
            []  # Make sure it will not through exception or error
        ]
        test_case.parse(testcase_list)
        test_case.pre_update(context)
        self.assertEqual('/api/person/5/', test_case.url)

        testcase_list = [
            {'auth_username': 'Abhilash'}, {'auth_password': '5'},
        ]
        test_case.parse(testcase_list)
        test_case.pre_update(context)
        self.assertEqual(bytes('5', 'utf-8'), test_case.auth_password)
        self.assertEqual(bytes('Abhilash', 'utf-8'), test_case.auth_username)

        _input = [
            {
                "url": '/test'},
            {'extract_binds': [
                {
                    'id': {'jsonpath_mini': 'key.val'}
                }
            ]
            }]
        test_case.parse(_input)
        test_case.pre_update(context)
        self.assertIsInstance(test_case.extract_binds['id'], MiniJsonExtractor)

        testcase_list = [
            {'name': 'Create/update person 7, no template'}, {'url': '/api/person/7/'}, {'method': 'PUT'},
            {'headers': {'Content-Type': {'template': '$content_type'}}},
            {'body': '{"first_name": "Gaius","id": "7","last_name": "Romani","login": "gromani"}'}
        ]
        test_case.parse(testcase_list)
        test_case.pre_update(context)
        self.assertEqual({'Content-Type': 'application/json'}, test_case.headers)

        testcase_list = [
            {'name': 'Create/update person 7, no template'}, {'url': '/api/person/7/'}, {'method': 'PUT'},
            {'headers': {'Content-Type': {'x': 'application/json'}}},
            {'body': '{"first_name": "Gaius","id": "7","last_name": "Romani","login": "gromani"}'}
        ]
        test_case.parse(testcase_list)
        test_case.pre_update(context)
        self.assertEqual({'Content-Type': 'application/json'}, test_case.headers)

        testcase_list = [
            {'name': 'Create/update person 7, no template'}, {'delay': '5'}, {'method': 'PUT'},

        ]
        test_case.parse(testcase_list)
        test_case.pre_update(context)
        self.assertEqual(5, test_case.delay)

        config_list = [
            {
                'generators': "H"
            }
        ]
        self.assertRaises(TypeError, config_object.parse, config_list)

        if __name__ == '__main__':
            unittest.main()
