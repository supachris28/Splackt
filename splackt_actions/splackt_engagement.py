# coding=utf-8

from slackbot.bot import respond_to, listen_to
import io
import re
import uuid
import py2neo
import dbapi as pdbc
import titlator, json
import requests
import timex
import datetime
import calendar
import traceback
from isoweek import Week
import numpy as np
import slackbot_settings
import splackt_helper

#import pandas

g = py2neo.Graph('http://neo4j:skynet@178.62.55.202:7474/db/data')
print('[splackt_engagement] loaded')


# standard word lists
engagement_keywords = "(page ?views|titles? read|books? read|users|pages? read|pages? viewed)"

input_check = "(.*" + engagement_keywords + ".*)"
@respond_to(input_check)
#@listen_to(input_check)
def testLooking(message, incoming_message, type):
    try:
        print('[splackt_engagement] verifying')
        
        incoming_message = incoming_message.replace('?', '')
        
        #data search variables
        search_type = ""
        search_content = ""
        search_period = ""

        response = "You're looking for"
        
        m = re.search(engagement_keywords, incoming_message, re.IGNORECASE)
        if m:
            response += " " + m.group(0)
            search_type = "engagement"
        
        response += " info"
        
        print(response)
        
        if response == "You're looking for info":
            response = "I don't understand you.... try it again in Klingon"
            return
            
        tagged = timex.tag(incoming_message)
        print (tagged)
        base_date = datetime.datetime.now()
        grounded = timex.ground(tagged, base_date)
        
        print(grounded)
        
        m = re.search("TIMEX2 val=\"(.*)\"", grounded)
        if m:
            response += " over the period " + m.group(1)
            search_period = m.group(1)
        
        message.reply(response)
        splackt_helper.getSimpleEngagementData(message, incoming_message, search_type, search_content, search_period)
        
    except:
        print('something went wrong....')
        print(traceback.format_exc())