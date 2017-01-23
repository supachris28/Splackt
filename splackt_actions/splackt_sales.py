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
import matplotlib.pyplot as plt
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
    getSimpleData(message, incoming_message, search_type, search_content, search_period)

def getSimpleData(message, incoming_message, search_type, search_content, search_period):
    print("searching:" + search_type)
    print("for: " + search_content)
    
    sql = ""
    date_value = ""
    table_name = ""
    metric = ""
    
    if search_type == "sales-volume" or search_type == "sales-value":
        if search_type == "sales-volume":
            date_value = "order_transaction_date"
            table_name = "home.fact_direct_sales"
            metric = "COUNT(*) as `count`"
        
        if search_type == "sales-value":
            date_value = "order_transaction_date"
            table_name = "home.fact_direct_sales"
            #metric = "CONCAT('£',CAST(SUM(order_gbp_paid) as char(10))) as `sum`"
            metric = "SUM(order_gbp_paid) as `sum`"
        
        group_by = splackt_helper.check_each(incoming_message, date_value)
        sql = "SELECT " + group_by
        if group_by != "":
            sql += ", "
        sql += metric + " FROM " + table_name + " WHERE 1=1 "
        
        
        if search_content != "":
            sql += " AND order_sale_type = '" + search_content + "'"
        
        if search_period != "":
            print("search_period: " + search_period)
            if len(search_period) == 4:
                sql += " AND " + date_value + " BETWEEN '" + splackt_helper.date_to_string(splackt_helper.period_to_date(search_period)) + "' AND '" + splackt_helper.date_to_string(splackt_helper.date_add_year(splackt_helper.period_to_date(search_period))) + "'"
            if search_period.count('-') == 1:
                sql += " AND " + date_value + " BETWEEN '" + splackt_helper.date_to_string(splackt_helper.period_to_date(search_period)) + "' AND '" + splackt_helper.date_to_string(splackt_helper.date_add_month(splackt_helper.period_to_date(search_period))) + "'"
            if search_period.count('-') == 2:
                sql += " AND " + date_value + " BETWEEN '" + splackt_helper.date_to_string(splackt_helper.period_to_date(search_period)) + "' AND '" + splackt_helper.date_to_string(splackt_helper.date_add_day(splackt_helper.period_to_date(search_period))) + "'"
            if 'W' in search_period:
                sql += " AND " + date_value + " BETWEEN '" + splackt_helper.date_to_string(splackt_helper.period_to_date(search_period)) + "' AND '" + splackt_helper.date_to_string(splackt_helper.date_add_week(splackt_helper.period_to_date(search_period))) + "'"
        else:
            today = datetime.datetime.now()
            this_month = splackt_helper.period_to_date(str(today.year) + "-" + str(today.month))
            sql += " AND " + date_value + " BETWEEN '" + splackt_helper.date_to_string(this_month) +"' AND '" + splackt_helper.date_to_string(splackt_helper.date_add_month(this_month)) + "'"
            message.reply("No date found so looking for this month only...")
        
        if group_by != "":
            sql += " GROUP BY " + group_by + " ORDER BY 1 "
        
    if sql != "":
        print(sql)
        message.reply("Looking...")
        ox = titlator.db.p.ex(sql)
        
        
        #print(ox)
        if group_by:
            splackt_helper.plot_results(message, ox, "", re.search("(by|each) (day|week|month)", incoming_message.lower(), re.IGNORECASE).group(2), search_type)
            message.reply('\n'.join(map(lambda x: '%s - %s' %x, ox)))
        else:
            message.reply("Answer: " + str(ox[0][0]))
    else:
        message.reply("I can't figure that out yet, ask someone in the data team...")
