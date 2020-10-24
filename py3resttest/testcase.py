import json
import logging
import os
import string
import time
import traceback
from io import BytesIO
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urljoin

import pycurl

from py3resttest.binding import Context
from py3resttest.constants import (
    AuthType, YamlKeyWords, TestCaseKeywords, DEFAULT_TIMEOUT, EnumHttpMethod, FAILURE_CURL_EXCEPTION,
    FAILURE_TEST_EXCEPTION, FAILURE_INVALID_RESPONSE
)
from py3resttest.contenthandling import ContentHandler
from py3resttest.exception import HttpMethodError, BindError, ValidatorError
from py3resttest.generators import parse_generator
from py3resttest.utils import read_testcase_file, ChangeDir, Parser
from py3resttest.validators import parse_extractor, parse_validator, Failure

logger = logging.getLogger('py3resttest')


class TestCaseConfig:

    def __init__(self):
        self.__variable_binds_dict = {}
        self.timeout = 60
        self.print_bodies = False
        self.retries = 0
        self.generators = {}

    @property
    def variable_binds(self):
        return self.__variable_binds_dict

    @variable_binds.setter
    def variable_binds(self, variable_dict):
        if isinstance(variable_dict, dict):
            self.__variable_binds_dict.update(Parser.flatten_dictionaries(variable_dict))

    def parse(self, config_node):
        node = Parser.flatten_lowercase_keys_dict(config_node)

        for key, value in node.items():
            if key == 'timeout':
                self.timeout = int(value)
            elif key == u'print_bodies':
                self.print_bodies = Parser.safe_to_bool(value)
            elif key == 'retries':
                self.retries = int(value)
            elif key == 'variable_binds':
                self.variable_binds = value
            elif key == u'generators':
                if not isinstance(value, list):
                    raise TypeError("generators in config should defined as list(array).")
                flat = Parser.flatten_dictionaries(value)
                gen_dict = {}
                for generator_name, generator_config in flat.items():
                    gen = parse_generator(generator_config)
                    gen_dict[str(generator_name)] = gen
                self.generators = gen_dict

    def __str__(self):
        return json.dumps(self, default=Parser.safe_to_json)


class TestSet:
    __testcase_file = set()
    test_group_list_dict = {}

    def __init__(self):
        self.__context = Context()
        self.__extract_binds = {}
        self.__variable_binds = {}
        self.config = TestCaseConfig()

    def parse(self, base_url: str, testcase_list: List, test_file=None, working_directory=None, variable_dict=None):

        if working_directory is None:
            working_directory = os.path.abspath(os.getcwd())
        else:
            working_directory = Path(working_directory)
        if variable_dict is None:
            self.config.variable_binds = variable_dict
        if test_file:
            self.__testcase_file.add(test_file)

        testcase_config_object = TestCaseConfig()
        for testcase_node in testcase_list:
            if not isinstance(testcase_node, dict):
                logger.warning("Skipping the configuration %s" % testcase_node)
                continue

            testcase_node = Parser.lowercase_keys(testcase_node)
            for key in testcase_node:
                sub_testcase_node = testcase_node[key]
                if key == YamlKeyWords.INCLUDE:
                    if not isinstance(sub_testcase_node, list):
                        raise ValueError("include should be list not %s" % type(sub_testcase_node))
                    for testcase_file_path in sub_testcase_node:
                        testcase_file_path = testcase_file_path.replace('.', '/')
                        testcase_file = working_directory.joinpath("%s.yaml" % testcase_file_path).resolve()
                        if testcase_file not in self.__testcase_file:
                            self.__testcase_file.add(testcase_file)
                            import_testcase_list = read_testcase_file(testcase_file)
                            with ChangeDir(working_directory):
                                self.parse(base_url, import_testcase_list, variable_dict=variable_dict)
                elif key == YamlKeyWords.IMPORT:
                    if sub_testcase_node not in self.__testcase_file:
                        testcase_file_path = os.path.dirname(os.path.realpath(sub_testcase_node))
                        logger.debug("Importing testcase from %s", testcase_file_path)
                        self.__testcase_file.add(sub_testcase_node)
                        import_testcase_list = read_testcase_file(testcase_file_path)
                        with ChangeDir(testcase_file_path):
                            self.parse(base_url, import_testcase_list, variable_dict=variable_dict)
                elif key == YamlKeyWords.URL:
                    __group_name = TestCaseGroup.DEFAULT_GROUP
                    try:
                        group_object = TestSet.test_group_list_dict[__group_name]
                    except KeyError:
                        group_object = TestCaseGroup(TestCaseGroup.DEFAULT_GROUP, config=testcase_config_object)
                        TestSet.test_group_list_dict[__group_name] = group_object
                    testcase_object = TestCase(
                        base_url=base_url, extract_binds=group_object.extract_binds,
                        variable_binds=group_object.variable_binds, context=group_object.context,
                        config=group_object.config
                    )
                    testcase_object.url = testcase_node[key]
                    group_object.testcase_list = testcase_object

                elif key == YamlKeyWords.TEST:
                    with ChangeDir(working_directory):
                        __group_name = None
                        for node_dict in sub_testcase_node:
                            if __group_name is None:
                                __group_name = node_dict.get(TestCaseKeywords.group)
                                break

                        __group_name = __group_name if __group_name else TestCaseGroup.DEFAULT_GROUP
                        try:
                            group_object = TestSet.test_group_list_dict[__group_name]
                        except KeyError:
                            group_object = TestCaseGroup(TestCaseGroup.DEFAULT_GROUP, config=testcase_config_object)
                            TestSet.test_group_list_dict[__group_name] = group_object

                        testcase_object = TestCase(
                            base_url=base_url, extract_binds=group_object.extract_binds,
                            variable_binds=group_object.variable_binds, context=group_object.context,
                            config=group_object.config
                        )
                        testcase_object.parse(sub_testcase_node)
                        group_object.testcase_list = testcase_object

                elif key == YamlKeyWords.CONFIG:
                    testcase_config_object.parse(sub_testcase_node)

        self.config = testcase_config_object

        return


class TestCaseGroup:
    DEFAULT_GROUP = "NO GROUP"

    def __init__(self, name, context=None, extract_binds=None, variable_binds=None, config=None):
        self.__testcase_list = []
        self.__benchmark_list = []
        self.__config = None

        self.__name = name
        self.__testcase_file = set()
        self.__context = context if context else Context()
        self.__extract_binds = extract_binds if extract_binds else {}
        self.__variable_binds = variable_binds if variable_binds else {}
        self.__is_global = None

        self.config = config

    @property
    def testcase_list(self):
        return self.__testcase_list

    @testcase_list.setter
    def testcase_list(self, testcase_object):
        self.__testcase_list.append(testcase_object)

    @property
    def is_global(self):
        return self.__is_global

    @is_global.setter
    def is_global(self, val):
        if self.__is_global is None:
            self.__is_global = val

    @property
    def benchmark_list(self):
        return self.__benchmark_list

    @benchmark_list.setter
    def benchmark_list(self, benchmark_objet):
        self.__benchmark_list.append(benchmark_objet)

    @property
    def extract_binds(self):
        return self.__extract_binds

    @extract_binds.setter
    def extract_binds(self, extract_dict):
        self.__extract_binds.update(extract_dict)

    @property
    def variable_binds(self):
        return self.__variable_binds

    @variable_binds.setter
    def variable_binds(self, var_dict):
        if isinstance(var_dict, dict):
            self.__variable_binds.update(var_dict)

    @property
    def config(self):
        return self.__config

    @config.setter
    def config(self, config_obj: TestCaseConfig):
        self.__config = config_obj
        self.variable_binds = config_obj.variable_binds

    @property
    def context(self):
        return self.__context



class TestResult:

    def __init__(self,  body, status_code):
        self.__headers = None
        self.__body = body
        self.__status_code = status_code
        self.__status = False
        self.__elapsed = 0.000
        self.__failure_list = []

    @property
    def failures(self):
        return self.__failure_list

    @failures.setter
    def failures(self, value):
        self.__failure_list.append(value)

    @property
    def headers(self):
        return self.__headers

    @headers.setter
    def headers(self, value):
        self.__headers = value


class TestCase:
    DEFAULT_NAME = "NO NAME"

    KEYWORD_DICT = {k: v for k, v in TestCaseKeywords.__dict__.items() if not k.startswith('__')}

    def __init__(self, base_url, extract_binds, variable_binds, context=None, config=None):
        self.__base_url = base_url
        self.__url = None
        self.__body = None
        self.__config = config if config else TestCaseConfig()
        self.__auth_username = None
        self.__auth_password = None
        self.__delay = 0
        self.__verbose = False
        self.__ssl_insecure = False
        self.__response_headers = None
        self.__response_code = None
        self.__passed = False
        self.__failure_list = []

        self.__header_dict = {}
        self.__http_method = EnumHttpMethod.GET.name
        self.__group = TestCaseGroup.DEFAULT_GROUP
        self.__name = TestCase.DEFAULT_NAME
        self._should_stop_on_failure = False
        self._test_run_delay = 0
        self._auth_type = AuthType.BASIC
        self._curl_options = None
        self.__variable_binds_dict = variable_binds if variable_binds else {}
        self.__generator_binds_dict = {}
        self.__extract_binds_dict = extract_binds if extract_binds else {}
        self.__validator_list = []

        self.__expected_http_status_code_list = [200]
        self.__context = Context() if context is None else context

        self.templates = {}
        self.result = None
        self.config = config

    def __str__(self):
        return json.dumps(self, default=Parser.safe_to_json)

    @property
    def config(self) -> Optional[TestCaseConfig]:
        return self.__config

    @config.setter
    def config(self, config_object: TestCaseConfig):
        if config_object:
            self.variable_binds.update(config_object.variable_binds)
            self.generator_binds.update(config_object.generators)

    @property
    def auth_username(self):
        return self.__auth_username

    @auth_username.setter
    def auth_username(self, username):
        self.__auth_username = Parser.coerce_string_to_ascii(username)

    @property
    def auth_password(self):
        return self.__auth_password

    @auth_password.setter
    def auth_password(self, password):
        self.__auth_password = Parser.coerce_string_to_ascii(password)

    @property
    def http_method(self):
        return self.__http_method

    @http_method.setter
    def http_method(self, method: str):
        __method = ["GET", "PUT", "POST", "DELETE", "PATCH"]
        if method.upper() not in __method:
            raise HttpMethodError("Method %s is not supported." % method)
        self.__http_method = method.upper()

    @property
    def name(self):
        return self.__name

    @property
    def group(self):
        return self.__group

    @property
    def is_passed(self):
        return bool(self.__passed)

    @property
    def url(self):
        val = self.realize_template("url", self.__context)
        if val is None:
            val = self.__url
        return val

    @url.setter
    def url(self, value):
        if isinstance(value, dict):
            # this is the templated url , we need to convert it into actual URL
            template_str = Parser.lowercase_keys(value)['template']
            url = urljoin(self.__base_url, Parser.coerce_to_string(template_str))
            self.set_template("url", url)
            self.__url = url
        else:
            url = urljoin(self.__base_url, Parser.coerce_to_string(value))
            self.__url = url

    @property
    def generator_binds(self):
        return self.__generator_binds_dict

    @property
    def delay(self):
        return self.__delay

    @generator_binds.setter
    def generator_binds(self, value: Dict):
        binds_dict = Parser.flatten_dictionaries(value)
        __binds_dict = {str(k): str(v) for k, v in binds_dict.items()}
        self.__generator_binds_dict.update(__binds_dict)

    @property
    def variable_binds(self):
        return self.__variable_binds_dict

    @property
    def extract_binds(self):
        return self.__extract_binds_dict

    @extract_binds.setter
    def extract_binds(self, bind_dict):
        bind_dict = Parser.flatten_dictionaries(bind_dict)
        for variable_name, extractor in bind_dict.items():
            if not isinstance(extractor, dict) or len(extractor) == 0:
                raise BindError("Extractors must be defined as maps of extractorType:{configs} with 1 entry")
            if len(extractor) > 1:
                raise BindError("Cannot define multiple extractors for given variable name")
            for extractor_type, extractor_config in extractor.items():
                self.__extract_binds_dict[variable_name] = parse_extractor(extractor_type, extractor_config)

    @property
    def expected_http_status_code_list(self):
        return [int(x) for x in self.__expected_http_status_code_list]

    @expected_http_status_code_list.setter
    def expected_http_status_code_list(self, value):
        self.__expected_http_status_code_list = value

    @property
    def validators(self):
        return self.__validator_list

    @validators.setter
    def validators(self, validator_list):
        if not isinstance(validator_list, list):
            raise ValidatorError('Misconfigured validator section, must be a list of validators')
        for validator in validator_list:
            if not isinstance(validator, dict):
                raise ValidatorError("Validators must be defined as validatorType:{configs} ")
            for validator_type, validator_config in validator.items():
                validator = parse_validator(validator_type, validator_config)
                self.__validator_list.append(validator)

    @property
    def headers(self) -> Dict:
        # if not self.templates.get('headers'):
        #     return self.__header_dict
        context_values = self.__context.get_values()
        header_dict = {}
        for key, header in self.__header_dict.items():
            if isinstance(header, dict):
                if key == 'template':
                    for k, v in header.items():
                        templated_string = string.Template(v).safe_substitute(context_values)
                        header_dict[k] = templated_string
                    continue
                templated_value = header.get('template')
                if templated_value:
                    templated_string = string.Template(templated_value).safe_substitute(context_values)
                    header_dict[key] = templated_string
                else:
                    logger.warning("Skipping the header: %s. We don't support mapping as header" % header)
            else:
                header_dict[key] = header

        return header_dict

    @headers.setter
    def headers(self, headers):
        config_value = Parser.flatten_dictionaries(headers)
        if isinstance(config_value, dict):
            for key, value in config_value.items():
                if isinstance(value, dict):
                    if value.get('template'):
                        self.set_template("headers", value.get('template'))
            self.__header_dict.update(config_value)
        else:
            raise ValidatorError("Illegal header type: headers must be a dictionary or list of dictionary keys")

    def set_template(self, variable_name, template_string):
        self.templates[variable_name] = string.Template(str(template_string))

    @property
    def body(self):
        if isinstance(self.__body, str) or self.__body is None:
            return self.__body
        else:
            return self.__body.get_content(context=self.__context)

    @body.setter
    def body(self, value):
        if value:
            if isinstance(value, bytes):
                self.__body = ContentHandler.parse_content(value.decode())
            else:
                self.__body = ContentHandler.parse_content(value)
        else:
            self.__body = value

    @property
    def failures(self):
        return self.__failure_list

    def realize_template(self, variable_name, context):
        if context is None or self.templates is None or variable_name not in self.templates:
            return None
        if not context.get_values():
            return None
        val = self.templates[variable_name].safe_substitute(context.get_values())
        return val

    def parse(self, testcase_dict):
        testcase_dict = Parser.flatten_lowercase_keys_dict(testcase_dict)

        for keyword in TestCase.KEYWORD_DICT.keys():
            value = testcase_dict.get(keyword)
            if value is None:
                continue

            if keyword == TestCaseKeywords.auth_username:
                self.auth_username = value
            elif keyword == TestCaseKeywords.auth_password:
                self.auth_password = value
            elif keyword == TestCaseKeywords.method:
                self.http_method = value
            elif keyword == TestCaseKeywords.delay:
                self.__delay = int(value)
            elif keyword == TestCaseKeywords.group:
                self.__group = value
            elif keyword == TestCaseKeywords.name:
                self.__name = value
            elif keyword == TestCaseKeywords.url:
                self.url = value
            elif keyword == TestCaseKeywords.extract_binds:
                self.extract_binds = value
            elif keyword == TestCaseKeywords.validators:
                self.validators = value
            elif keyword == TestCaseKeywords.headers:
                self.headers = value
            elif keyword == TestCaseKeywords.variable_binds:
                self.__variable_binds_dict = Parser.flatten_dictionaries(value)
            elif keyword == TestCaseKeywords.generator_binds:
                self.__generator_binds_dict = {str(k): str(v) for k, v in Parser.flatten_dictionaries(value)}
            elif keyword == TestCaseKeywords.options:
                raise NotImplementedError("Yet to Support")
            elif keyword == TestCaseKeywords.body:
                self.body = value

        expected_status = testcase_dict.get(TestCaseKeywords.expected_status, [])
        if expected_status:
            self.expected_http_status_code_list = expected_status
        else:
            if self.http_method in ["POST", "PUT", "DELETE"]:
                self.expected_http_status_code_list = [200, 201, 204]

        return

    def pre_update(self, context):
        if self.variable_binds:
            context.bind_variables(self.variable_binds)
        if self.generator_binds:
            for key, value in self.generator_binds.items():
                context.bind_generator_next(key, value)
        return

    def post_update(self, context):
        if self.extract_binds:
            for key, value in self.extract_binds.items():
                result = value.extract(
                    body=self.body, headers=self.headers, context=context)
                if result:
                    context.bind_variable(key, result)
        return

    def is_dynamic(self):
        if self.templates:
            return True
        if isinstance(self.__body, ContentHandler) and self.__body.is_dynamic():
            return True
        return False

    def render(self):
        if self.is_dynamic() or self.__context is not None:
            if isinstance(self.__body, ContentHandler):
                self.__body = self.__body.get_content(self.__context)

        return

    def __perform_validation(self) -> List:

        failure_list = []
        for validator in self.validators:
            logger.debug("Running validator: %s" % validator.name)
            validate_result = validator.validate(body=self.body, headers=self.headers, context=self.__context)
            if not validate_result:
                self.__passed = False
            if hasattr(validate_result, 'details'):
                failure_list.append(validate_result)

        return failure_list

    def run(self, context=None, timeout=None, curl_handler=None):

        if context is None:
            context = self.__context

        self.pre_update(context)
        self.render()
        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        if curl_handler:

            try:  # Check the curl handle isn't closed, and reuse it if possible
                curl_handler.getinfo(curl_handler.HTTP_CODE)
                # Below clears the cookies & curl options for clean run
                # But retains the DNS cache and connection pool
                curl_handler.reset()
                curl_handler.setopt(curl_handler.COOKIELIST, "ALL")
            except pycurl.error:
                curl_handler = pycurl.Curl()
        else:
            curl_handler = pycurl.Curl()

        body_byte = BytesIO()
        header_byte = BytesIO()
        curl_handler.setopt(curl_handler.URL, str(self.url))
        curl_handler.setopt(curl_handler.TIMEOUT, timeout)
        curl_handler.setopt(pycurl.WRITEFUNCTION, body_byte.write)
        curl_handler.setopt(pycurl.HEADERFUNCTION, header_byte.write)
        curl_handler.setopt(pycurl.VERBOSE, self.__verbose)
        if self.config.timeout:
            curl_handler.setopt(pycurl.CONNECTTIMEOUT, self.config.timeout)

        if self.__ssl_insecure:
            curl_handler.setopt(pycurl.SSL_VERIFYPEER, 0)
            curl_handler.setopt(pycurl.SSL_VERIFYHOST, 0)

        if self.body:
            logger.debug("Request body %s" % self.body)
            curl_handler.setopt(curl_handler.READFUNCTION, BytesIO(bytes(self.body, 'utf-8')).read)

        if self.auth_username and self.auth_password:
            curl_handler.setopt(pycurl.USERPWD, self.auth_username + ':' + self.auth_password)

        body_length = len(self.body) if self.body else 0
        if self.http_method == EnumHttpMethod.POST.name:
            curl_handler.setopt(EnumHttpMethod.POST.value, 1)
            curl_handler.setopt(pycurl.POSTFIELDSIZE, body_length)

        elif self.http_method == EnumHttpMethod.PUT.name:
            curl_handler.setopt(EnumHttpMethod.PUT.value, 1)
            curl_handler.setopt(pycurl.INFILESIZE, body_length)

        elif self.http_method == EnumHttpMethod.PATCH.name:
            curl_handler.setopt(EnumHttpMethod.PATCH.value, EnumHttpMethod.PATCH.name)
            curl_handler.setopt(pycurl.POSTFIELDS, self.body)

        elif self.http_method == EnumHttpMethod.DELETE.name:
            curl_handler.setopt(EnumHttpMethod.DELETE.value, EnumHttpMethod.DELETE.name)
            if self.body:
                curl_handler.setopt(pycurl.POSTFIELDS, self.body)
                curl_handler.setopt(pycurl.POSTFIELDSIZE, body_length)

        elif self.http_method == EnumHttpMethod.HEAD.name:
            curl_handler.setopt(pycurl.NOBODY, 1)
            curl_handler.setopt(EnumHttpMethod.HEAD.value, EnumHttpMethod.HEAD.name)
        else:
            curl_handler.setopt(pycurl.CUSTOMREQUEST, self.http_method.upper())
            if self.body:
                curl_handler.setopt(pycurl.POSTFIELDS, self.body)
                curl_handler.setopt(pycurl.POSTFIELDSIZE, body_length)

        head = self.headers
        if head.get('content-type'):
            content_type = head['content-type']
            head[u'content-type'] = content_type + ' ; charset=UTF-8'

        headers = [str(header_name) + ':' + str(header_value) for header_name, header_value in head.items()]
        headers.append("Expect:")
        headers.append("Connection: close")
        logger.debug("Request headers %s " % head)
        curl_handler.setopt(curl_handler.HTTPHEADER, headers)

        if self.__delay:
            time.sleep(self.__delay)
        try:
            logger.info("Hitting %s" % self.url)
            curl_handler.perform()
        except pycurl.error as e:
            logger.error("Unknown Exception", exc_info=True)
            self.__passed = False
            curl_handler.close()
            trace = traceback.format_exc()
            self.__failure_list.append(
                Failure(message="Curl Exception: {0}".format(e), details=trace, failure_type=FAILURE_CURL_EXCEPTION))
            return
        body = body_byte.getvalue()
        body_byte.close()
        logger.debug("RESPONSE: %s" % self.body)
        response_code = curl_handler.getinfo(pycurl.RESPONSE_CODE)
        self.body = body
        self.__response_code = int(response_code)

        try:
            response_headers = Parser.parse_headers(header_byte.getvalue())
            self.__response_headers = response_headers
            logger.debug("RESPONSE HEADERS: %s" % self.__response_headers)
            header_byte.close()

        except Exception as e:  # Need to catch the expected exception
            trace = traceback.format_exc()
            self.__failure_list.append(Failure(
                message="Header parsing exception: {0}".format(e), details=trace, failure_type=FAILURE_TEST_EXCEPTION)
            )
            self.__passed = False
            curl_handler.close()
            return

        if self.__response_code in self.expected_http_status_code_list:
            self.__passed = True
            self.__failure_list.extend(self.__perform_validation())
            self.post_update(context)
        else:
            self.__passed = False
            failure_message = "Invalid HTTP response code: response code {0} not in expected codes {1}".format(
                self.__response_code, self.expected_http_status_code_list
            )
            self.__failure_list.append(
                Failure(message=failure_message, details=None, failure_type=FAILURE_INVALID_RESPONSE)
            )
        curl_handler.close()
