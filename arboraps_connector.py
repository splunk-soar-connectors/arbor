# --
# File: arboraps_connector.py
#
# Copyright (c) Phantom Cyber Corporation, 2017-2018
#
# This unpublished material is proprietary to Phantom Cyber.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Phantom Cyber Corporation.
#
# --

# Standard library imports
import json
import datetime
import requests
from bs4 import BeautifulSoup

# Phantom App imports
import phantom.app as phantom
from phantom.base_connector import BaseConnector
from phantom.action_result import ActionResult

# Local imports
from arboraps_consts import *


def _break_ip_address(cidr_ip_address):
    """ Function divides the input parameter into IP address and network mask.

    :param cidr_ip_address: IP address in format of IP/prefix_size
    :return: IP, prefix_size
    """

    if "/" in cidr_ip_address:
        ip_address, prefix_size = cidr_ip_address.split("/")
    else:
        ip_address = cidr_ip_address
        prefix_size = 0

    return ip_address, int(prefix_size)


class RetVal(tuple):
    def __new__(cls, val1, val2):
        return tuple.__new__(RetVal, (val1, val2))


class ArborApsConnector(BaseConnector):

    def __init__(self):

        # Call the BaseConnectors init first
        super(ArborApsConnector, self).__init__()

        self._server_url = None
        self._username = None
        self._password = None
        self._verify_server_cert = False
        self._session = None

        return

    def initialize(self):
        """ This is an optional function that can be implemented by the AppConnector derived class. Since the
        configuration dictionary is already validated by the time this function is called, it's a good place to do any
        extra initialization of any internal modules. This function MUST return a value of either phantom.APP_SUCCESS or
        phantom.APP_ERROR. If this function returns phantom.APP_ERROR, then AppConnector::handle_action will not get
        called.
        """

        # get the asset config
        config = self.get_config()

        # Access values in asset config by the name
        self._server_url = config[ARBORAPS_TA_CONFIG_SERVER_URL].strip("/")
        self._username = config[ARBORAPS_TA_CONFIG_USERNAME]
        self._password = config[ARBORAPS_TA_CONFIG_PASSWORD]
        self._verify_server_cert = config.get(ARBORAPS_TA_CONFIG_VERIFY_SSL, False)

        # Custom validation for IP address
        self.set_validator(ARBORAPS_TA_PARAM_IP, self._is_ip)

        return phantom.APP_SUCCESS

    def _is_ip(self, cidr_ip_address):
        """ Function that checks given address and return True if address is valid IPv4 address.

        :param cidr_ip_address: IP address
        :return: status (success/failure)
        """

        try:
            ip_address, net_mask = _break_ip_address(cidr_ip_address)
        except Exception as e:
            self.debug_print(ARBORAPS_INVALID_IP, e)
            return False

        # Validate IP address
        if not phantom.is_ip(ip_address):
            self.debug_print(ARBORAPS_INVALID_IP)
            return False

        # Check if net mask is out of range
        if net_mask not in range(0, 33):
            self.debug_print(ARBORAPS_INVALID_IP)
            return False

        return True

    def _process_empty_response(self, response, action_result):
        """ This function is used to process empty response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(
            phantom.APP_ERROR, "Empty response and no information in the header"), None)

    def _process_html_response(self, response, action_result):
        """ This function is used to process html response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # An html response, consider it as an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split('\n')
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = '\n'.join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = "Status Code: {0}. Data from server:\n{1}\n".format(status_code, error_text)

        message = message.replace('{', '{{').replace('}', '}}')

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, response, action_result):
        """ This function is used to process json response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # Try a json parse
        try:
            resp_json = response.json()
        except Exception as e:
            return RetVal(action_result.set_status(
                phantom.APP_ERROR, "Unable to parse JSON response. Error: {0}".format(str(e))), None)

        if 200 <= response.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # Process the error returned in the json
        message = "Error from server. Status Code: {0} Data from server: {1}".format(
            response.status_code, response.text.replace('{', '{{').replace('}', '}}'))

        if isinstance(resp_json, dict):
            for item in resp_json.get('errors'):
                message = "Error from server. Status Code: {0} Data from server: {1}".format(
                    response.status_code, item.get('message'))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, response, action_result):
        """ This function is used to process html response.

        :param response: response data
        :param action_result: object of Action Result
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message)
        """

        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, 'add_debug_data'):
            action_result.add_debug_data({'r_status_code': response.status_code})
            action_result.add_debug_data({'r_text': response.text})
            action_result.add_debug_data({'r_headers': response.headers})

        # Process each 'Content-Type' of response separately

        # Process a json response
        if 'json' in response.headers.get('Content-Type', ''):
            return self._process_json_response(response, action_result)

        # Process an HTML response, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if 'html' in response.headers.get('Content-Type', ''):
            return self._process_html_response(response, action_result)

        # Handle an empty response
        if not response.text:
            return self._process_empty_response(response, action_result)

        # Everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {0} Data from server: {1}".format(
            response.status_code, response.text.replace('{', '{{').replace('}', '}}'))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, params=None, data=None, method="get"):
        """ Function that makes the REST call to the device. It's a generic function that can be called from various
        action handlers.

        :param endpoint: REST endpoint that needs to appended to the service address
        :param action_result: object of ActionResult class
        :param params: request parameters
        :param data: request body
        :param method: GET/POST/PUT/DELETE (Default will be GET)
        :return: status phantom.APP_ERROR/phantom.APP_SUCCESS(along with appropriate message),
        response obtained by making an API call
        """

        resp_json = None

        try:
            request_func = getattr(self._session, method)
        except AttributeError:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Invalid method: {0}".format(method)), resp_json)

        try:
            r = request_func("{0}{1}".format(self._server_url, endpoint),
                             verify=self._verify_server_cert,
                             data=data,
                             params=params)
        except Exception as e:
            return RetVal(action_result.set_status(
                phantom.APP_ERROR, "Error Connecting to server. Details: {0}".format(str(e))), resp_json)

        # In case of login, check for successful login
        if endpoint == ARBORAPS_TA_REST_LOGIN:
            _, _ = self._process_response(r, action_result)
            if r.status_code == 200:
                # In case of invalid credential
                if "Username\nPassword\nLog In\n" in action_result.get_message():
                    return RetVal(action_result.set_status(
                        phantom.APP_ERROR, "Error Connecting to server. Details: Invalid Credentials"), resp_json)

                # Return success
                return RetVal(phantom.APP_SUCCESS, resp_json)

        if method == 'delete' and r.status_code == 204:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        return self._process_response(r, action_result)

    def _login(self, action_result):
        """ This function tests the connectivity of an asset with given credentials.

        :param action_result: object of Action Result
        :return: status success/failure
        """

        self._session = requests.Session()

        # Make REST call
        ret_val, response = self._make_rest_call(endpoint=ARBORAPS_TA_REST_LOGIN, action_result=action_result,
                                                 data={'username': self._username, 'password': self._password},
                                                 method='post')

        # Something went wrong
        if phantom.is_fail(ret_val):
            return action_result.get_status(), response

        return RetVal(action_result.set_status(phantom.APP_SUCCESS, response), {})

    def _logout(self):
        """ Function used to logout from Arbor Networks APS. Called from finalize method at the end of each action.

        :return: status (success/failure)
        """

        # Only initializing action_result for REST calls, not adding it to BaseConnector
        action_result = ActionResult()

        # Make REST call
        ret_val, _ = self._make_rest_call(endpoint=ARBORAPS_TA_REST_LOGOUT, action_result=action_result)

        # Something went wrong
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return phantom.APP_SUCCESS

    def _handle_test_connectivity(self, param):
        """ This function tests the connectivity of an asset with given credentials.

        :param param: (not used in this method)
        :return: status success/failure
        """

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress(ARBORAPS_TA_CONNECTION_TEST_MSG)

        # Initiating login session
        ret_val, _ = self._login(action_result)

        # Something went wrong
        if phantom.is_fail(ret_val):
            self.save_progress("{0}".format(ARBORAPS_TEST_CONNECTIVITY_FAIL))
            return action_result.get_status()

        # Return success
        self.save_progress(ARBORAPS_TEST_CONNECTIVITY_PASS)
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_list_ips(self, param):
        """ This function is used to list IPs on the blacklist or whitelist.

        :param param: dictionary of input parameters
        :return: status phantom.APP_SUCCESS/phantom.APP_ERROR (along with appropriate message)
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Initiating login session
        ret_val, _ = self._login(action_result)

        # Something went wrong
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Prepare endpoint
        endpoint = ARBORAPS_TA_REST_BLACKLISTED_HOSTS if param['list'] == 'blacklist' else ARBORAPS_TA_REST_WHITELISTED_HOSTS

        # Get IPs from requested list
        ret_val, response = self._make_rest_call(endpoint=endpoint, action_result=action_result)

        # Something went wrong
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        ips = response.pop('{0}ed-hosts'.format(param['list']))
        response['hosts'] = ips

        action_result.add_data(response)
        action_result.update_summary({'num_ips': len(ips)})

        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_unblacklist_ip(self, param):
        """ This function is used to un-blacklist IP or CIDR.

        :param param: dictionary of input parameters
        :return: status phantom.APP_SUCCESS/phantom.APP_ERROR (along with appropriate message)
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Initiating login session
        ret_val, _ = self._login(action_result)

        # Something went wrong
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Get required parameter
        ip_address, net_mask = _break_ip_address(param[ARBORAPS_TA_PARAM_IP])
        if net_mask != 32:
            ip_address = param[ARBORAPS_TA_PARAM_IP]

        # Prepare endpoint
        endpoint = "{0}{1}/".format(ARBORAPS_TA_REST_BLACKLISTED_HOSTS, ip_address)

        # Get blacklisted hosts
        ret_val, response = self._make_rest_call(endpoint=endpoint, action_result=action_result)

        # Something went wrong
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # If IP is not present in blacklist
        if not response:
            return action_result.set_status(phantom.APP_SUCCESS, ARBORAPS_ALREADY_UNBLACKLISTED)

        # Prepare params
        params = {'hostAddress': ip_address}

        # Delete IP from blacklist
        ret_val, response = self._make_rest_call(endpoint=ARBORAPS_TA_REST_BLACKLISTED_HOSTS,
                                                 action_result=action_result, method='delete', params=params)

        # Something went wrong
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, ARBORAPS_UNBLACKLISTED_SUCCESSFULLY)

    def _handle_blacklist_ip(self, param):
        """ This function is used to blacklist IP or CIDR.

        :param param: dictionary of input parameters
        :return: status phantom.APP_SUCCESS/phantom.APP_ERROR (along with appropriate message)
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Initiating login session
        ret_val, _ = self._login(action_result)

        # Something went wrong
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Get required parameter
        ip_address, net_mask = _break_ip_address(param[ARBORAPS_TA_PARAM_IP])
        if net_mask != 32:
            ip_address = param[ARBORAPS_TA_PARAM_IP]

        # Prepare endpoint
        endpoint = "{0}{1}/".format(ARBORAPS_TA_REST_BLACKLISTED_HOSTS, ip_address)

        # Get blacklisted hosts
        ret_val, response = self._make_rest_call(endpoint=endpoint, action_result=action_result)

        # Something went wrong
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # If IP already present in blacklist
        if response:
            # Add the response into the data section
            date_time = datetime.datetime.utcfromtimestamp(response['updateTime'])
            response['updatetimeISO'] = date_time.isoformat() + 'Z'
            action_result.add_data(response)
            return action_result.set_status(phantom.APP_SUCCESS, ARBORAPS_ALREADY_BLACKLISTED)

        # Prepare params
        params = {'hostAddress': ip_address}

        # Add IP in blacklist
        ret_val, response = self._make_rest_call(endpoint=ARBORAPS_TA_REST_BLACKLISTED_HOSTS,
                                                 action_result=action_result, method='post', params=params)

        # Something went wrong
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        date_time = datetime.datetime.utcfromtimestamp(response['updateTime'])
        response['updatetimeISO'] = date_time.isoformat() + 'Z'
        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, ARBORAPS_BLACKLISTED_SUCCESSFULLY)

    def _handle_unwhitelist_ip(self, param):
        """ This function is used to un-whitelist IP or CIDR.

        :param param: dictionary of input parameters
        :return: status phantom.APP_SUCCESS/phantom.APP_ERROR (along with appropriate message)
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Initiating login session
        ret_val, _ = self._login(action_result)

        # Something went wrong
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Get required parameter
        ip_address, net_mask = _break_ip_address(param[ARBORAPS_TA_PARAM_IP])
        if net_mask != 32:
            ip_address = param[ARBORAPS_TA_PARAM_IP]

        # Prepare endpoint
        endpoint = "{0}{1}/".format(ARBORAPS_TA_REST_WHITELISTED_HOSTS, ip_address)

        # Get whitelisted hosts
        ret_val, response = self._make_rest_call(endpoint=endpoint, action_result=action_result)

        # Something went wrong
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # If IP is not present in whitelist
        if not response:
            return action_result.set_status(phantom.APP_SUCCESS, ARBORAPS_ALREADY_UNWHITELISTED)

        # Prepare params
        params = {'hostAddress': ip_address}

        # Delete IP from whitelist
        ret_val, response = self._make_rest_call(endpoint=ARBORAPS_TA_REST_WHITELISTED_HOSTS,
                                                 action_result=action_result, method='delete', params=params)

        # Something went wrong
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        return action_result.set_status(phantom.APP_SUCCESS, ARBORAPS_UNWHITELISTED_SUCCESSFULLY)

    def _handle_whitelist_ip(self, param):
        """ This function is used to whitelist IP or CIDR.

        :param param: dictionary of input parameters
        :return: status phantom.APP_SUCCESS/phantom.APP_ERROR (along with appropriate message)
        """

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Initiating login session
        ret_val, _ = self._login(action_result)

        # Something went wrong
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Get required parameter
        ip_address, net_mask = _break_ip_address(param[ARBORAPS_TA_PARAM_IP])
        if net_mask != 32:
            ip_address = param[ARBORAPS_TA_PARAM_IP]

        # Prepare endpoint
        endpoint = "{0}{1}/".format(ARBORAPS_TA_REST_WHITELISTED_HOSTS, ip_address)

        # Get whitelisted hosts
        ret_val, response = self._make_rest_call(endpoint=endpoint, action_result=action_result)

        # Something went wrong
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # If IP already present in whitelist
        if response:
            # Add the response into the data section
            date_time = datetime.datetime.utcfromtimestamp(response['updateTime'])
            response['updatetimeISO'] = date_time.isoformat() + 'Z'
            action_result.add_data(response)
            return action_result.set_status(phantom.APP_SUCCESS, ARBORAPS_ALREADY_WHITELISTED)

        # Prepare params
        params = {'hostAddress': ip_address}

        # Add IP in whitelist
        ret_val, response = self._make_rest_call(endpoint=ARBORAPS_TA_REST_WHITELISTED_HOSTS,
                                                 action_result=action_result, method='post', params=params)

        # Something went wrong
        if phantom.is_fail(ret_val):
            return action_result.get_status()

        # Add the response into the data section
        date_time = datetime.datetime.utcfromtimestamp(response['updateTime'])
        response['updatetimeISO'] = date_time.isoformat() + 'Z'
        action_result.add_data(response)

        return action_result.set_status(phantom.APP_SUCCESS, ARBORAPS_WHITELISTED_SUCCESSFULLY)

    def handle_action(self, param):
        """ This function gets current action identifier and calls member function of its own to handle the action.

        :param param: dictionary which contains information about the actions to be executed
        :return: status success/failure
        """

        # Dictionary mapping each action with its corresponding actions
        action_mapping = {
            'test_connectivity': self._handle_test_connectivity,
            'list_ips': self._handle_list_ips,
            'block_ip': self._handle_blacklist_ip,
            'unblock_ip': self._handle_unblacklist_ip,
            'blacklist_ip': self._handle_blacklist_ip,
            'unblacklist_ip': self._handle_unblacklist_ip,
            'whitelist_ip': self._handle_whitelist_ip,
            'unwhitelist_ip': self._handle_unwhitelist_ip
        }

        action = self.get_action_identifier()
        action_execution_status = phantom.APP_SUCCESS

        if action in action_mapping.keys():
            action_function = action_mapping[action]
            action_execution_status = action_function(param)

        return action_execution_status

    def finalize(self):
        """ This function gets called once all the param dictionary elements are looped over and no more handle_action
        calls are left to be made. It gives the AppConnector a chance to loop through all the results that were
        accumulated by multiple handle_action function calls and create any summary if required. Another usage is
        cleanup, disconnect from remote devices etc.

        :return: status (success/failure)
        """

        return self._logout()


if __name__ == '__main__':

    import sys
    import pudb
    pudb.set_trace()

    if (len(sys.argv) < 2):
        print "No test json specified as input"
        exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = ArborApsConnector()
        connector.print_progress_message = True
        r_val = connector._handle_action(json.dumps(in_json), None)
        print (json.dumps(json.loads(r_val), indent=4))

    exit(0)
