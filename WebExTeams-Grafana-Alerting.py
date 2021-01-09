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


import inspect  # part of the logging stack
import logging.handlers  # Needed for logging
import sys  # for error to catch and debug
import threading  # for periodic cron type jobs
import traceback  # helps add more logging infomation
import wsgiserver  # Runs the Flask webesite
from flask import Flask  # Flask website
from flask import Response  # Used to respond to stats request
import signal  # catches SIGTERM and SIGINT
from flask import request  # Flask website requester details
from webexteamssdk import WebexTeamsAPI  # gets and posts messages

import credentials  # imports static values

FLASK_HOST = credentials.FLASK_HOST
FLASK_PORT = credentials.FLASK_PORT
FLASK_HOSTNAME = credentials.FLASK_HOSTNAME
TARGET_URL = "http://" + FLASK_HOSTNAME + ":" + str(FLASK_PORT) + "/wxt_webhook"
ABSOLUTE_PATH = credentials.ABSOLUTE_PATH
LOGFILE = credentials.LOGFILE

THREAD_TO_BREAK = threading.Event()

WXT_BOT_ACCESS_TOKEN = credentials.WXT_BOT_ACCESS_TOKEN
WXT_BOT_ROOM_ID = credentials.WXT_BOT_ROOM_ID
api = WebexTeamsAPI(access_token=WXT_BOT_ACCESS_TOKEN)
WXT_BOT_NAME = credentials.WXT_BOT_NAME

flask_app = Flask(__name__)


@flask_app.route('/wxt_bot_message', methods=['GET', 'POST'])
def wxt_bot_message():
    function_logger = logger.getChild("%s.%s.%s" % (inspect.stack()[2][3], inspect.stack()[1][3], inspect.stack()[0][3]))
    function_logger.info("wxt_bot_message")
    try:
        if request.method == 'GET':
            function_logger.info("GOT GET MESSAGE")
            function_logger.debug(request.json)
            return Response("WORKING", mimetype='text/plain')
        elif request.method == 'POST':
            function_logger.info("GOT POST MESSAGE")
            function_logger.debug(request.json)
            if request.json["state"] == "ok":
                prepend = "✅😀🐵"
                postpend = "🐵😀✅"
            elif request.json["state"] == "alerting":
                prepend = "⚠️🤬🙉"
                postpend = "🙉🤬⚠️"
            else:
                prepend = "‼️😨🙈"
                postpend = "🙈😨‼️"
            message_response = "%s %s to see more infomation please [click here](%s) %s" % (prepend, request.json["title"], request.json["ruleUrl"], postpend)
            api.messages.create(WXT_BOT_ROOM_ID, text=request.json["title"], markdown=message_response)
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
    handler = logging.handlers.TimedRotatingFileHandler(LOGFILE, backupCount=365, when='D')
    logger_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(process)d:%(name)s - %(message)s')
    handler.setFormatter(logger_formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info("---------------------- STARTING ----------------------")
    logger.info("cisco EoS EoL script started")

    # Catch SIGTERM etc
    signal.signal(signal.SIGHUP, graceful_killer)
    signal.signal(signal.SIGTERM, graceful_killer)

    # Start Server
    logger.info("start web server")
    http_server = wsgiserver.WSGIServer(host=FLASK_HOST, port=FLASK_PORT, wsgi_app=flask_app)
    http_server.start()