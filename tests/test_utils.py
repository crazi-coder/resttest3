import os
import unittest

from py3resttest.utils import ChangeDir, read_testcase_file


class TestCaseUtils(unittest.TestCase):

    def test_ch_dir(self):
        ch_dir = os.getcwd()
        with ChangeDir('../') as cd:
            self.assertEqual(cd.saved_path, ch_dir)
            self.assertNotEquals(cd.new_path, ch_dir)

    def test_read_file(self):
        with ChangeDir(os.getcwd()) as cd:
            data = read_testcase_file(cd.new_path + '/tests/sample.yaml')
            self.assertEqual(data['include'], 'example')


if __name__ == '__main__':
    unittest.main()
