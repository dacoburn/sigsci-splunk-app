
# encoding = utf-8

import os
import sys
import time
from datetime import datetime, timedelta
import json
import calendar
import requests
from timeit import default_timer as timer

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''


#def use_single_instance_mode():
#    return True
    

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # delta = definition.parameters.get('delta', None)
    # site = definition.parameters.get('site', None)
    pass

def collect_events(helper, ew):
    start = timer()
    # loglevel = helper.get_log_level()
    # Proxy setting configuration
    proxy_settings = helper.get_proxy()
    # User credentials

    # Global variable configuration
    email = helper.get_global_setting("email")
    password = helper.get_global_setting("password")
    apitoken = helper.get_global_setting("apitoken")
    # helper.log_info(apitoken)
    corp_name = helper.get_global_setting("corp")
    api_host = 'https://dashboard.signalsciences.net'
    helper.log_info("email: %s" % email)
    helper.log_info("corp: %s" % corp_name)

    pythonRequestsVersion = requests.__version__
    userAgentVersion = "1.0.25"
    userAgentString = "SigSci-Splunk-TA-Requests/%s (PythonRequests %s)" \
        % (userAgentVersion, pythonRequestsVersion)

    # Definition for error handling on the response code

    def checkResponse(code, responseText, curSite=None,
                      from_time=None, until_time=None):
        site_name = curSite
        if code == 400:
            if "Rate limit exceeded" in responseText:
                return("rate-limit")
            else:
                helper.log_error("Bad API Request (ResponseCode: %s)" % (code))
                helper.log_error("ResponseError: %s" % responseText)
                helper.log_error('from: %s' % from_time)
                helper.log_error('until: %s' % until_time)
                helper.log_error('email: %s' % email)
                helper.log_error('Corp: %s' % corp_name)
                helper.log_error('SiteName: %s' % site_name)
                return("bad-request")
        elif code == 500:
            helper.log_error(
                "Caused an Internal Server error (ResponseCode: %s)" % (code))
            helper.log_error("ResponseError: %s" % responseText)
            helper.log_error('from: %s' % from_time)
            helper.log_error('until: %s' % until_time)
            helper.log_error('email: %s' % email)
            helper.log_error('Corp: %s' % corp_name)
            helper.log_error('SiteName: %s' % site_name)
            return("internal-error")
        elif code == 401:
            helper.log_error(
                "Unauthorized, likely bad credentials or site configuration," +
                " or lack of permissions (ResponseCode: %s)" % (code))
            helper.log_error("ResponseError: %s" % responseText)
            helper.log_error('email: %s' % email)
            helper.log_error('Corp: %s' % corp_name)
            helper.log_error('SiteName: %s' % site_name)
            return("unauthorized")
        elif code >= 400 and code <= 599 and code != 400 \
                and code != 500 and code != 401:
            helper.log_error("ResponseError: %s" % responseText)
            helper.log_error('from: %s' % from_time)
            helper.log_error('until: %s' % until_time)
            helper.log_error('email: %s' % email)
            helper.log_error('Corp: %s' % corp_name)
            helper.log_error('SiteName: %s' % site_name)
            return("other-error")
        else:
            return("success")

    def sigsciAuth():
        helper.log_info("Authenticating to SigSci API")
        # Authenticate
        authUrl = api_host + '/api/v0/auth'
        authHeader = {
            "User-Agent": userAgentString
        }
        auth = requests.post(
            authUrl,
            data={"email": email, "password": password},
            headers=authHeader
        )

        authCode = auth.status_code
        authError = auth.text

        authResult = checkResponse(authCode, authError)
        if authResult is None or authResult != "success":
            helper.log_error("API Auth Failed")
            helper.log_error(authResult)
            exit()
        elif authResult is not None and authResult == "rate-limit":
            helper.log_error("SigSci Rate Limit hit")
            helper.log_error("Retrying in 10 seconds")
            time.sleep(10)
            sigsciAuth()
        else:
            parsed_response = auth.json()
            token = parsed_response['token']
            helper.log_info("Authenticated")
            return(token)

    def getRequestData(url, headers):
        method = "GET"
        response_raw = \
            helper.send_http_request(url, method, parameters=None,
                                     payload=None, headers=headers,
                                     cookies=None, verify=True, cert=None,
                                     timeout=None, use_proxy=True)
        responseCode = response_raw.status_code
        responseError = response_raw.text
        return(response_raw, responseCode, responseError)

    def pullRequests(curSite, delta, token, key=None, apiMode=None):
        site_name = curSite
        until_time = datetime.utcnow() - timedelta(minutes=5)
        until_time = until_time.replace(second=0, microsecond=0)
        from_time = until_time - timedelta(minutes=delta)
        until_time = calendar.timegm(until_time.utctimetuple())
        from_time = calendar.timegm(from_time.utctimetuple())

        helper.log_info("SiteName: %s" % site_name)
        helper.log_info("From: %s\nUntil:%s" % (from_time, until_time))

        inputNames = helper.get_input_stanza_names()
        singleName = ""

        if type(inputNames) is dict and inputNames > 1:
            helper.log_info("Multi instance mode")
            for curName in inputNames:
                singleName = curName
        else:
            helper.log_info("Single instance mode")
            helper.log_info("Inputs: %s" % (inputNames))
            helper.log_info("Inputs Num: %s" % len(inputNames))
            singleName = inputNames



        # Loop across all the data and output it in one big JSON object
        if apiMode == "apitoken":
            headers = {
                'Content-type': 'application/json',
                'x-api-user': email,
                'x-api-token': apitoken,
                'User-Agent': userAgentString
            }
        else:
            headers = {
                'Content-type': 'application/json',
                'Authorization': 'Bearer %s' % token,
                'User-Agent': userAgentString
            }

        url = api_host + \
            ('/api/v0/corps/%s/sites/%s/feed/requests?from=%s&until=%s'
                % (corp_name, site_name, from_time, until_time))
        loop = True

        counter = 1
        helper.log_info("Pulling requests from requests API")
        allRequests = []
        while loop:
            helper.log_info("Processing page %s" % counter)
            startPage = timer()
            responseResult, responseCode, ResponseError = \
                getRequestData(url, headers)

            sigSciRequestCheck = \
                checkResponse(responseCode, ResponseError, curSite=site_name,
                              from_time=from_time, until_time=until_time)

            if sigSciRequestCheck is None or sigSciRequestCheck != "success":
                helper.log_error("Failed to pull results")
                helper.log_error(sigSciRequestCheck)
                exit()
            elif sigSciRequestCheck is not None and \
                    sigSciRequestCheck == "rate-limit":
                helper.log_error("SigSci Rate Limit hit")
                helper.log_error("Retrying in 10 seconds")
                time.sleep(10)
                break
            else:
                response = json.loads(responseResult.text)

            curPageNumRequests = len(response['data'])
            helper.log_info("Number of Requests for Page: %s"
                            % curPageNumRequests)

            for request in response['data']:
                data = json.dumps(request)
                data = json.loads(data)
                headersFix = {}
                headersFix['headersOut'] = data['headersOut']
                headersFix['headersIn'] = data['headersIn']

                newFormatOut = {}

                if not (headersFix['headersOut'] is None):
                    for out in headersFix['headersOut']:
                        newFormatOut[out[0]] = out[1]

                    data['headersOut'] = newFormatOut

                newFormatIn = {}

                if not (headersFix['headersIn'] is None):
                    for hIn in headersFix['headersIn']:
                        newFormatIn[hIn[0]] = hIn[1]

                    data['headersIn'] = newFormatIn

                data = json.dumps(data)

                helper.log_debug("%s" % data)
                allRequests.append(data)

            if "next" in response and "uri" in response['next']:
                next_url = response['next']['uri']
                if next_url == '':
                    helper.log_info("Finished Page %s" % counter)
                    counter += 1
                    endPage = timer()
                    pageTime = endPage - startPage
                    pageTimeResult = round(pageTime, 2)
                    helper.log_info("Total Page Time: %s seconds"
                                    % pageTimeResult)
                    loop = False
                else:
                    url = api_host + next_url
                    helper.log_info("Finished Page %s" % counter)
                    counter += 1
                    endPage = timer()
                    pageTime = endPage - startPage
                    pageTimeResult = round(pageTime, 2)
                    helper.log_info("Total Page Time: %s seconds"
                                    % pageTimeResult)
            else:
                loop = False

        totalRequests = len(allRequests)
        helper.log_info("Total Requests Pulled: %s" % totalRequests)
        writeStart = timer()
        for curEvent in allRequests:
            if key is None:
                event = \
                    helper.new_event(source=singleName,
                                     index=helper.get_output_index(),
                                     sourcetype=helper.get_sourcetype(),
                                     data=curEvent)
            else:
                indexes = helper.get_output_index()
                curIndex = indexes[key]
                types = helper.get_sourcetype()
                curType = types[key]
                event = \
                    helper.new_event(source=singleName,
                                     index=curIndex, sourcetype=curType,
                                     data=curEvent)

            try:
                ew.write_event(event)
            except Exception as e:
                raise e
        writeEnd = timer()
        writeTime = writeEnd - writeStart
        writeTimeResult = round(writeTime, 2)
        helper.log_info("Total Event Output Time: %s seconds"
                        % writeTimeResult)

    # If multiple inputs configured it creates an array of values and the
    # script only gets called once per Input configuration

    multiCheck = helper.get_arg('delta')
    hostTest = helper.get_arg('Host')
    helper.log_info("Host: %s" % (hostTest))

    if apitoken is not None and apitoken != "":
        authMode = "apitoken"
        helper.log_info("AuthMode: API Token")
    else:
        authMode = "password"
        helper.log_info("AuthMode: Password")
        sigsciToken = sigsciAuth()

    if type(multiCheck) is dict:
        for activeInput in multiCheck:
            delta = int(multiCheck[activeInput])
            allSites = helper.get_arg('site')
            site = allSites[activeInput]
            helper.log_info("site: %s" % site)
            if authMode == "apitoken":
                pullRequests(key=activeInput, curSite=site, delta=delta,
                             token=apitoken, apiMode="apitoken")
            else:
                pullRequests(key=activeInput, curSite=site, delta=delta,
                             token=sigsciToken)
            helper.log_info("Finished Pulling Requests for %s" % site)
    else:
        delta = int(helper.get_arg('delta'))
        site = helper.get_arg('site')
        helper.log_info("site: %s" % site)
        if authMode == "apitoken":
            pullRequests(site, delta, apitoken, apiMode="apitoken")
        else:
            pullRequests(site, delta, sigsciToken)
        helper.log_info("Finished Pulling Requests for %s" % site)
    end = timer()
    totalTime = end - start
    timeResult = round(totalTime, 2)
    helper.log_info("Total Script Time: %s seconds" % timeResult)
