import logging
import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, List

import yaml
from alive_progress import alive_bar

from py3resttest.testcase import TestSet
from py3resttest.utils import register_extensions

logger = logging.getLogger('py3resttest')
logging.basicConfig(format='%(levelname)s:%(message)s')


class ArgsRunner:

    def __init__(self):
        self.log = logging.ERROR
        self.interactive = None
        self.url = None
        self.test = None
        self.extensions = None
        self.vars = None
        self.verbose = None
        self.insecure = None
        self.absolute_urls = None
        self.skip_term_colors = None

    def args(self):
        parser = ArgumentParser(description='usage: %prog base_url test_filename.yaml [options]')
        # parser.add_argument("--log", help="Logging level", action="store", type=str,
        #                     choices=["info", "error", "warning", "debug"])
        #parser.add_argument("--interactive", help="Interactive mode", action="store", type=str)
        parser.add_argument("--url", help="Base URL to run tests against", action="store", type=str, required=True)
        parser.add_argument("--test", help="Test file to use", action="store", type=str, required=True)
        #parser.add_argument(u'--extensions', help='Extensions to import, separated by semicolons', nargs='+', type=str)
        #parser.add_argument('--vars', help='Variables to set, as a YAML dictionary', action="store", type=str)
        # parser.add_argument(u'--insecure', help='Disable cURL host and peer cert verification', action='store_true',
        #                     default=False)
        # parser.add_argument(u'--absolute_urls', help='Enable absolute URLs in tests instead of relative paths',
        #                     action="store_true")
        # parser.add_argument(u'--skip_term_colors', help='Turn off the output term colors',
        #                     action='store_true', default=False)

        parser.parse_args(namespace=self)


class Runner:

    FAIL = '\033[91m'
    SUCCESS = '\033[92m'
    NOCOL = '\033[0m'

    def __init__(self):
        self.__args = ArgsRunner()

    def read_test_file(self, file_location: str) -> List[Dict]:
        with open(file_location, 'r') as f:
            test_dict = yaml.safe_load(f.read())
        return test_dict

    def main(self) -> int:
        self.__args.args()  # Set the arguments
        logger.setLevel(self.__args.log)

        # If user provided any custom extension add it into the system path and import it
        working_folder = os.path.realpath(os.path.abspath(os.getcwd()))
        if self.__args.extensions is not None:

            if working_folder not in sys.path:
                sys.path.insert(0, working_folder)
            register_extensions(self.__args.extensions)
        p = Path(self.__args.test)

        test_case_dict = self.read_test_file(p.absolute())
        testcase_set = TestSet()
        testcase_set.parse(self.__args.url, testcase_list=test_case_dict, working_directory=p.parent.absolute())

        success_dict = {}
        failure_dict = {}
        total_testcase_count = len([y for x, y in testcase_set.test_group_list_dict.items() for c in y.testcase_list])
        with alive_bar(total_testcase_count) as bar:
            for test_group, test_group_object in testcase_set.test_group_list_dict.items():
                for testcase_object in test_group_object.testcase_list:
                    bar()
                    testcase_object.run()
                    if testcase_object.is_passed:
                        try:
                            (count, case_list) = success_dict[test_group]
                            case_list.append(testcase_object)
                            success_dict[test_group] = (count + 1, case_list)
                        except KeyError:
                            success_dict[test_group] = (1, [testcase_object])
                    else:
                        try:
                            count, case_list = failure_dict[test_group]
                            case_list.append(testcase_object)
                            failure_dict[test_group] = (count + 1, case_list)
                        except KeyError:
                            failure_dict[test_group] = (1, [testcase_object])
        print("========== TEST RESULT ===========")
        print("Total Test to run: %s" % total_testcase_count)
        for group_name, case_list_tuple in failure_dict.items():
            print("%sGroup Name: %s %s" % (self.FAIL, group_name, self.NOCOL))
            count, courtcase_list = case_list_tuple
            print('%sTotal testcase failed: %s %s' % (self.FAIL, count, self.NOCOL))
            for index, testcase in enumerate(courtcase_list):
                print('\t%s %s. Case Name: %s %s' % (self.FAIL, index+1, testcase.name, self.NOCOL))
                for f in testcase.failures:
                    print('\t\t%s %s %s' % (self.FAIL, f, self.NOCOL))

        for group_name, case_list_tuple in success_dict.items():
            print("%sGroup Name: %s %s" % (self.SUCCESS, group_name, self.NOCOL))
            count, courtcase_list = case_list_tuple
            print('%sTotal testcase success: %s %s' % (self.SUCCESS, count, self.NOCOL))
            for index, testcase in enumerate(courtcase_list):
                print('\t%s %s. Case Name: %s %s' % (self.SUCCESS, index+1, testcase.name, self.NOCOL))
        return 0


def main():
    r = Runner()
    r.main()


if __name__ == '__main__':
    main()
