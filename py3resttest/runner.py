import os
import sys
from argparse import ArgumentParser
import logging
from pathlib import Path
from typing import Dict, List

import yaml
from py3resttest.testcase import TestSet

from utils import register_extensions

logger = logging.getLogger('py3resttest')
logging.basicConfig(format='%(levelname)s:%(message)s')


class ArgsRunner:

    def __init__(self):
        self.log = logging.INFO
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
        parser.add_argument("--log", help="Logging level", action="store", type=str,
                            choices=["info", "error", "warning", "debug"])
        parser.add_argument("--interactive", help="Interactive mode", action="store", type=str)
        parser.add_argument("--url", help="Base URL to run tests against", action="store", type=str)
        parser.add_argument("--test", help="Test file to use", action="store", type=str)
        parser.add_argument(u'--extensions', help='Extensions to import, separated by semicolons',
                            nargs='+', type=str)
        parser.add_argument('--vars', help='Variables to set, as a YAML dictionary', action="store", type=str)
        parser.add_argument(u'--insecure', help='Disable cURL host and peer cert verification', action='store_true',
                            default=False)
        parser.add_argument(u'--absolute_urls', help='Enable absolute URLs in tests instead of relative paths',
                            action="store_true")
        parser.add_argument(u'--skip_term_colors', help='Turn off the output term colors',
                            action='store_true', default=False)

        parser.parse_args(namespace=self)


class Runner:

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
        logger.info("Total %s group found" % len(testcase_set.test_group_list_dict))
        for test_group, test_group_object in testcase_set.test_group_list_dict.items():
            logger.info("Running Group %s" % test_group)
            for testcase_object in test_group_object.testcase_list:
                logger.info("Running test %s ..." % testcase_object.name)
                testcase_object.run()

        logger.info("TEST RESULT")
        for test_group, test_group_object in testcase_set.test_group_list_dict.items():
            logger.info("Result for Group %s" % test_group)
            for testcase_object in test_group_object.testcase_list:
                if testcase_object.failures:
                    for failure in testcase_object.failures:
                        logger.warning("%s Failed: %s" % (testcase_object.name, failure))
                        logger.warning("%s BODY: %s" % (testcase_object.name, testcase_object.body))
                        logger.warning("%s HEADER: %s" % (testcase_object.name, testcase_object.headers))

                else:
                    logger.info("Success: %s " % testcase_object.name)

        return 0

if __name__ == '__main__':
    r = Runner()
    r.main()
