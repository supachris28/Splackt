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
from isoweek import Week
import numpy as np
import slackbot_settings
import splackt_helper

#import pandas

g = py2neo.Graph('http://neo4j:skynet@178.62.55.202:7474/db/data')


# standard word lists
product_types = "(book|ebook|video|subscription)"
sales_keywords = "(sales|value|revenue|quantity)"
quantity_keywords = "(many (\w+ )* ?sold|sell|quantity)"
engagement_keywords = "(page ?views|engagement)"


@respond_to("(.*)")
#@listen_to("(.*)")
def testLooking(message, incoming_message):
    
    incoming_message = incoming_message.replace('?', '')
    
    #data search variables
    search_type = ""
    search_content = ""
    search_period = ""

    response = "You're looking for"
    
    if re.search(sales_keywords, incoming_message, re.IGNORECASE):
        response += " sales (value)"
        search_type = "sales-value"
    
    if re.search(quantity_keywords, incoming_message, re.IGNORECASE):
        response += " sales (volume)"
        search_type = "sales-volume"
    
    m = re.search(engagement_keywords, incoming_message, re.IGNORECASE)
    if m:
        response += " " + m.group(0)
        search_type = "engagement"
    
    
    response += " info"
    
    m = re.search(product_types, incoming_message, re.IGNORECASE)
    if m:
        response += " for " + m.group(0)
        search_content = m.group(0)
    
    tagged = timex.tag(incoming_message)
    print (tagged)
    base_date = datetime.datetime.now()
    grounded = timex.ground(tagged, base_date)
    
    print(grounded)
    
    m = re.search("TIMEX2 val=\"(.*)\"", grounded)
    if m:
        response += " over the period " + m.group(1)
        search_period = m.group(1)
    
    
    if response == "You're looking for info":
        response = "I don't understand you.... try it again in Klingon"
        return
    
    message.reply(response)
    splackt_helper.getSimpleSalesData(message, incoming_message, search_type, search_content, search_period)
