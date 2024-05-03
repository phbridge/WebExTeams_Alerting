# Copyright (c) 2021 Cisco and/or its affiliates.
#
# This software is licensed to you under the terms of the Cisco Sample
# Code License, Version 1.1 (the "License"). You may obtain a copy of the
# License at
#
#                https://developer.cisco.com/docs/licenses
#
# All use of the material herein must be in accordance with the terms of
# the License. All rights not expressly granted by the License are
# reserved. Unless required by applicable law or agreed to separately in
# writing, software distributed under the License is distributed on an "AS
# IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.

# # Title
# WebExTeams-Grafana-Alerting
#
# # Language
# Python 3.5+
#
# # Description
# This is a mini web server designed to take the POST from a Grafana WebHook and then convert it into a WebExTeams message
#
# # Contacts
# Phil Bridges - phbridge@cisco.com
#
# # Licence
# Please see LICENCE file
#
# # EULA
# This software is provided as is and with zero support level. Support can be purchased by providing Phil bridges with a
# varity of Beer, Wine, Steak and Greggs pasties. Please contact phbridge@cisco.com for support costs and arrangements.
# Until provison of alcohol or baked goodies your on your own but there is no rocket sciecne involved so dont panic too
# much. To accept this EULA you must include the correct flag when running the script. If this script goes crazy wrong and
# breaks everything then your also on your own and Phil will not accept any liability of any type or kind. As this script
# belongs to Phil and NOT Cisco then Cisco cannot be held responsable for its use or if it goes bad, nor can Cisco make
# any profit from this script. Phil can profit from this script but will not assume any liability. Other than the boaring
# stuff please enjoy and plagerise as you like (as I have no ways to stop you) but common curtacy says to credit me in some
# way [see above comments on Beer, Wine, Steak and Greggs.].
#


import inspect                  # part of the logging stack
import logging.handlers         # Needed for logging
import sys                      # for error to catch and debug
# import threading                # for periodic cron type jobs
import traceback                # helps add more logging infomation
import wsgiserver               # Runs the Flask webesite
from flask import Flask         # Flask website
from flask import Response      # Used to respond to stats request
import signal                   # catches SIGTERM and SIGINT
from flask import request       # Flask website requester details
# from webexteamssdk import WebexTeamsAPI  # gets and posts messages
import requests
import time

import credentials  # imports static values

FLASK_HOST = credentials.FLASK_HOST
FLASK_PORT = credentials.FLASK_PORT
FLASK_HOSTNAME = credentials.FLASK_HOSTNAME
TARGET_URL = "http://" + FLASK_HOSTNAME + ":" + str(FLASK_PORT) + "/wxt_webhook"
ABSOLUTE_PATH = credentials.ABSOLUTE_PATH
LOGFILE = credentials.LOGFILE
#
# THREAD_TO_BREAK = threading.Event()

WXT_BOT_ACCESS_TOKEN = credentials.WXT_BOT_ACCESS_TOKEN
WXT_BOT_ROOM_ID = credentials.WXT_BOT_ROOM_ID
# api = WebexTeamsAPI(access_token=WXT_BOT_ACCESS_TOKEN)
WXT_BOT_NAME = credentials.WXT_BOT_NAME

flask_app = Flask(__name__)


@flask_app.route('/wxt_bot_message', methods=['GET', 'POST'])
def wxt_bot_message():
    function_logger = logger.getChild("%s.%s.%s" % (inspect.stack()[2][3], inspect.stack()[1][3], inspect.stack()[0][3]))
    function_logger.info("wxt_bot_message")
    function_logger.setLevel(logging.DEBUG)
    message_response = ""
    try:
        if request.method == 'GET':
            function_logger.info("GOT GET MESSAGE")
            function_logger.debug(request.json)
            return Response("WORKING", mimetype='text/plain')
        elif request.method == 'POST':
            function_logger.info("GOT POST MESSAGE")
            function_logger.debug(request.json)
            for each in request.json['alerts']:
                if each["status"] == "resolved":
                    prepend = "✅😀🐵"
                    postpend = "🐵😀✅"
                elif each["status"] == "firing":
                    prepend = "⚠️🤬🙉"
                    postpend = "🙉🤬⚠️"
                else:
                    prepend = "‼️😨🙈"
                    postpend = "🙈😨‼️"
                alertname = "No Alert Name"
                if each["labels"].get("alertname"):
                    alertname = each["labels"]["alertname"]
                rulename = "No Rule Name"
                if each["labels"].get("rulename"):
                    rulename = each["labels"]["rulename"]
                message_response += "%s %s - %s to see more infomation please [click here](%s) %s \n" % (prepend, rulename, alertname, each["panelURL"], postpend)

                if len(message_response) > (7439 * .80):
                    function_logger.info("response length reached %s sending partial message" % str(len(message_response)))
                    message_create(roomId=WXT_BOT_ROOM_ID, text=message_response, markdown=message_response)
                    # api.messages.create(WXT_BOT_ROOM_ID, text=message_response, markdown=message_response)
                    message_response = ""

            if len(message_response) > 2:
                # api.messages.create(WXT_BOT_ROOM_ID, text=message_response, markdown=message_response)
                message_create(roomId=WXT_BOT_ROOM_ID, text=message_response, markdown=message_response)
            return Response("WORKING", mimetype='text/plain', status=200)
    except KeyError as e:
        function_logger.warning("could not build WxT string due to missing %s" % str(e))
        function_logger.warning("the raw data for this client was %s" % str(request.json))
        function_logger.warning("Unexpected error: %s" % str(sys.exc_info()[0]))
        function_logger.warning("Unexpected error: %s" % str(e))
        function_logger.debug("TRACEBACK= %s" % str(traceback.format_exc()))
    except Exception as e:
        function_logger.error("something went bad with WxT process")
        function_logger.error("Unexpected error:%s" % str(sys.exc_info()[0]))
        function_logger.error("Unexpected error:%s" % str(e))
        function_logger.error("TRACEBACK=%s" % str(traceback.format_exc()))
    return Response("ERROR", mimetype='text/plain', status=500)


def message_create(roomId, text, markdown=None):
    function_logger = logger.getChild("%s.%s.%s" % (inspect.stack()[2][3], inspect.stack()[1][3], inspect.stack()[0][3]))
    webex_message_url = "https://webexapis.com/v1/messages"
    webex_headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % WXT_BOT_ACCESS_TOKEN
    }
    body_data = {
        "roomId": roomId,
        "text": text,
        "markdown": markdown
    }
    success = False
    attempts = 0
    while attempts < 5 and not success:
        try:
            response = requests.post(url=webex_message_url, header=webex_headers, data=body_data)
            if response.status_code == 200:
                success = True
            else:
                function_logger.critical("got %s code from post" % response.status_code)
                function_logger.critical("got text as %s" % response.text)
                function_logger.critical("got headers as %s" % response.headers)
                time.sleep(1)
        except requests.exceptions.ConnectTimeout as e:
            attempts += 1
            function_logger.warning("attempted " + str(attempts) + " Failed Connection Timeout")
            function_logger.warning("Unexpected error:" + str(sys.exc_info()[0]))
            function_logger.warning("Unexpected error:" + str(e))
            function_logger.warning("TRACEBACK=" + str(traceback.format_exc()))
            time.sleep(1)
        except requests.exceptions.ConnectionError as e:
            attempts += 1
            function_logger.warning("attempted " + str(attempts) + " Failed Connection Timeout")
            function_logger.warning("Unexpected error:" + str(sys.exc_info()[0]))
            function_logger.warning("Unexpected error:" + str(e))
            function_logger.warning("TRACEBACK=" + str(traceback.format_exc()))
            time.sleep(1)
        except Exception as e:
            function_logger.error("attempted " + str(attempts) + " Failed")
            function_logger.error("Unexpected error:" + str(sys.exc_info()[0]))
            function_logger.error("Unexpected error:" + str(e))
            function_logger.debug("TRACEBACK=" + str(traceback.format_exc()))
            time.sleep(1)
            break
    return


def update_influx(raw_string, timestamp=None):
    function_logger = logger.getChild("%s.%s.%s" % (inspect.stack()[2][3], inspect.stack()[1][3], inspect.stack()[0][3]))
    # function_logger.setLevel(logging.INFO)
    try:
        string_to_upload = ""
        if timestamp is not None:
            timestamp_string = str(int(timestamp.timestamp()) * 1000000000)
            for each in raw_string.splitlines():
                string_to_upload += each + " " + timestamp_string + "\n"
        else:
            string_to_upload = raw_string
        function_logger.debug(string_to_upload)
        success_array = []
        upload_to_influx_sessions = requests.session()
        for influx_path_url in INFLUX_DB_PATH:
            success = False
            attempts = 0
            attempt_error_array = []
            while attempts < 5 and not success:
                try:
                    upload_to_influx_sessions_response = upload_to_influx_sessions.post(url=influx_path_url, data=string_to_upload, timeout=(20, 10))
                    if upload_to_influx_sessions_response.status_code == 204:
                        function_logger.debug("content=%s" % upload_to_influx_sessions_response.content)
                        function_logger.debug("status_code=%s" % upload_to_influx_sessions_response.status_code)
                        success = True
                    else:
                        attempts += 1
                        function_logger.warning("status_code=%s" % upload_to_influx_sessions_response.status_code)
                        function_logger.warning("content=%s" % upload_to_influx_sessions_response.content)
                except requests.exceptions.ConnectTimeout as e:
                    attempts += 1
                    function_logger.debug("update_influx - attempted " + str(attempts) + " Failed Connection Timeout")
                    function_logger.debug("update_influx - Unexpected error:" + str(sys.exc_info()[0]))
                    function_logger.debug("update_influx - Unexpected error:" + str(e))
                    function_logger.debug("update_influx - String was:" + str(string_to_upload).splitlines()[0])
                    function_logger.debug("update_influx - TRACEBACK=" + str(traceback.format_exc()))
                    attempt_error_array.append(str(sys.exc_info()[0]))
                except requests.exceptions.ConnectionError as e:
                    attempts += 1
                    function_logger.debug("update_influx - attempted " + str(attempts) + " Failed Connection Error")
                    function_logger.debug("update_influx - Unexpected error:" + str(sys.exc_info()[0]))
                    function_logger.debug("update_influx - Unexpected error:" + str(e))
                    function_logger.debug("update_influx - String was:" + str(string_to_upload).splitlines()[0])
                    function_logger.debug("update_influx - TRACEBACK=" + str(traceback.format_exc()))
                    attempt_error_array.append(str(sys.exc_info()[0]))
                except Exception as e:
                    function_logger.error("update_influx - attempted " + str(attempts) + " Failed")
                    function_logger.error("update_influx - Unexpected error:" + str(sys.exc_info()[0]))
                    function_logger.error("update_influx - Unexpected error:" + str(e))
                    function_logger.error("update_influx - String was:" + str(string_to_upload).splitlines()[0])
                    function_logger.debug("update_influx - TRACEBACK=" + str(traceback.format_exc()))
                    attempt_error_array.append(str(sys.exc_info()[0]))
                    break
            success_array.append(success)
        upload_to_influx_sessions.close()
        super_success = False
        for each in success_array:
            if not each:
                super_success = False
                break
            else:
                super_success = True
        if not super_success:
            function_logger.error("update_influx - FAILED after 5 attempts. Failed up update " + str(string_to_upload.splitlines()[0]))
            function_logger.error("update_influx - FAILED after 5 attempts. attempt_error_array: " + str(attempt_error_array))
            return False
        else:
            function_logger.debug("update_influx - " + "string for influx is " + str(string_to_upload))
            function_logger.debug("update_influx - " + "influx status code is  " + str(upload_to_influx_sessions_response.status_code))
            function_logger.debug("update_influx - " + "influx response is code is " + str(upload_to_influx_sessions_response.text[0:1000]))
            return True
    except Exception as e:
        function_logger.error("update_influx - something went bad sending to InfluxDB")
        function_logger.error("update_influx - Unexpected error:" + str(sys.exc_info()[0]))
        function_logger.error("update_influx - Unexpected error:" + str(e))
        function_logger.error("update_influx - TRACEBACK=" + str(traceback.format_exc()))
    return False





def graceful_killer(signal_number, frame):
    function_logger = logger.getChild("%s.%s.%s" % (inspect.stack()[2][3], inspect.stack()[1][3], inspect.stack()[0][3]))
    function_logger.info("Got Kill signal")
    function_logger.info('Received:' + str(signal_number))
    http_server.stop()
    function_logger.info("stopped HTTP server")
    quit()


if __name__ == "__main__":
    # Create Logger
    logger = logging.getLogger(".__main__")
    handler = logging.handlers.TimedRotatingFileHandler(LOGFILE, backupCount=30, when='D')
    logger_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(process)d:%(name)s - %(message)s')
    handler.setFormatter(logger_formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info("---------------------- STARTING ----------------------")
    logger.info("WebExTeams_Alerting started")

    # Catch SIGTERM etc
    signal.signal(signal.SIGHUP, graceful_killer)
    signal.signal(signal.SIGTERM, graceful_killer)

    # Start Server
    logger.info("start web server")
    http_server = wsgiserver.WSGIServer(host=FLASK_HOST, port=FLASK_PORT, wsgi_app=flask_app)
    http_server.start()