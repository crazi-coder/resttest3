import os
import unittest
from inspect import currentframe, getframeinfo
from pathlib import Path

from py3resttest.utils import ChangeDir, read_testcase_file, Parser

filename = getframeinfo(currentframe()).filename
current_module_path = Path(filename)


class TestCaseUtils(unittest.TestCase):

    def test_ch_dir(self):
        ch_dir = os.getcwd()
        with ChangeDir('../') as cd:
            self.assertEqual(cd.saved_path, ch_dir)
            self.assertNotEqual(cd.new_path, ch_dir)

    def test_read_file(self):
        with ChangeDir(current_module_path.parent) as cd:
            data = read_testcase_file(cd.new_path + '/sample.yaml')
            self.assertEqual(data['include'], 'example')

    def test_encode_unicode_bytes(self):
        decode_str = Parser.encode_unicode_bytes('my😽')
        self.assertEqual(decode_str, bytes('my😽', 'utf-8'))
        decode_str = Parser.encode_unicode_bytes(bytes('my😽', 'utf-8'))
        self.assertEqual(decode_str, bytes('my😽', 'utf-8'))
        decode_str = Parser.encode_unicode_bytes('hello')
        self.assertEqual(decode_str, bytes('hello', 'utf-8'))

    def test_safe_substitute_unicode_template(self):
        result = Parser.safe_substitute_unicode_template("This is $x test", {'x': 'unit'})
        self.assertEqual("This is unit test", result)

    def test_safe_to_json(self):
        class Example:
            x = 1
            y = 2

        result = Parser.safe_to_json(Example)
        self.assertEqual(result, {'x': 1, 'y': 2})

        result = Parser.safe_to_json("Example1")
        self.assertEqual(result, "Example1")

        result = Parser.safe_to_json(bytes("Example", "utf-8"))
        self.assertEqual(result, "Example")
        result = Parser.safe_to_json(1)
        self.assertEqual(result, "1")

    def test_flatten_dictionaries(self):
        input_dict = {"x": 1, "y": 2}
        result_dict = Parser.flatten_dictionaries(input_dict)
        self.assertEqual(input_dict, result_dict)
        input_dict.update({"y": {"a": 1}})
        result_dict = Parser.flatten_dictionaries(input_dict)
        self.assertEqual(input_dict, result_dict)

        result_dict = Parser.flatten_dictionaries([input_dict, input_dict, input_dict])
        self.assertEqual(input_dict, result_dict)
        result_dict = Parser.flatten_dictionaries([input_dict])
        self.assertEqual(input_dict, result_dict)
        result_dict = Parser.flatten_dictionaries([{'x': 1}, input_dict])
        self.assertEqual(input_dict, result_dict)
        result_dict = Parser.flatten_dictionaries([input_dict, {'x': 2}])
        self.assertNotEqual(input_dict, result_dict)
        result_dict = Parser.flatten_dictionaries([{'x': 2}, input_dict])
        self.assertEqual(input_dict, result_dict)

    def test_flatten_lowercase_keys_dict(self):
        input_dict = {"x": 1, "y": 2}
        result_dict = Parser.flatten_lowercase_keys_dict([{'x': 2}, input_dict])
        self.assertEqual(input_dict, result_dict)
        input_dict = {"X": 1, "y": 2}
        result_dict = Parser.flatten_lowercase_keys_dict([{'x': 2}, input_dict])
        self.assertEqual({'x': 1, 'y': 2}, result_dict)

        input_dict = {"X": 1, "y": 2}
        result_dict = Parser.flatten_lowercase_keys_dict(input_dict)
        self.assertEqual({'x': 1, 'y': 2}, result_dict)

        input_dict = 22  # unexpected
        result_dict = Parser.flatten_lowercase_keys_dict(input_dict)
        self.assertEqual(22, result_dict)

    def test_lowercase_keys(self):
        input_val = 23
        result_dict = Parser.lowercase_keys(input_val)
        self.assertEqual(23, result_dict)

    def test_coerce_string_to_ascii(self):
        result = Parser.coerce_string_to_ascii(bytes("Hello", 'utf-8'))
        self.assertEqual(result, "Hello".encode('ascii'))

    def test_coerce_to_string(self):
        result = Parser.coerce_to_string(bytes("Hello", 'utf-8'))
        self.assertEqual(result, "Hello")

    def test_parse_headers(self):
        request_text = (
            b'GET /who/ken/trust.html HTTP/1.1\r\n'
            b'Host: cm.bell-labs.com\r\n'
            b'Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.3\r\n'
            b'Accept: text/html;q=0.9,text/plain\r\n'
            b'\r\n'
        )
        result_list = Parser.parse_headers(request_text)
        self.assertEqual(3, len(result_list))
        self.assertEqual(('host', 'cm.bell-labs.com'), result_list[0])

        request_text = ""
        result_list = Parser.parse_headers(request_text)
        self.assertEqual(0, len(result_list))

        request_text = '\r\n'
        result_list = Parser.parse_headers(request_text)
        self.assertEqual(0, len(result_list))


if __name__ == '__main__':
    unittest.main()
