# coding=utf-8

from slackbot.bot import respond_to, listen_to
import io
import os
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
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import slackbot_settings


def getSimpleSalesData(message, incoming_message, search_type, search_content, search_period):
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
        
        group_by = check_each(incoming_message, date_value)
        sql = "SELECT " + group_by
        if group_by != "":
            sql += ", "
        sql += metric + " FROM " + table_name + " WHERE 1=1 "
        
        
        if search_content != "":
            sql += " AND order_sale_type = '" + search_content + "'"
        
        if search_period != "":
            print("search_period: " + search_period)
            if len(search_period) == 4:
                sql += " AND " + date_value + " BETWEEN '" + date_to_string(period_to_date(search_period)) + "' AND '" + date_to_string(date_add_year(period_to_date(search_period))) + "'"
            if search_period.count('-') == 1:
                sql += " AND " + date_value + " BETWEEN '" + date_to_string(period_to_date(search_period)) + "' AND '" + date_to_string(date_add_month(period_to_date(search_period))) + "'"
            if search_period.count('-') == 2:
                sql += " AND " + date_value + " BETWEEN '" + date_to_string(period_to_date(search_period)) + "' AND '" + date_to_string(date_add_day(period_to_date(search_period))) + "'"
            if 'W' in search_period:
                sql += " AND " + date_value + " BETWEEN '" + date_to_string(period_to_date(search_period)) + "' AND '" + date_to_string(date_add_week(period_to_date(search_period))) + "'"
        else:
            today = datetime.datetime.now()
            this_month = period_to_date(str(today.year) + "-" + str(today.month))
            sql += " AND " + date_value + " BETWEEN '" + date_to_string(this_month) +"' AND '" + date_to_string(date_add_month(this_month)) + "'"
            message.reply("No date found so looking for this month only...")
        
        if group_by != "":
            sql += " GROUP BY " + group_by + " ORDER BY 1 "
        
    if sql != "":
        print(sql)
        message.reply("Looking...")
        res = titlator.db.p.execute(sql)
        ox = res.fetchall()
        
        
        print(ox)
        if group_by:
            plot_results(message, ox, "", re.search("(by|each) (day|week|month)", incoming_message.lower(), re.IGNORECASE).group(2), search_type)
            message.reply('\n'.join(map(lambda x: '{0} - {1}'.format(x[0],x[1]), ox)))
        else:
            message.reply("Answer: " + str(ox[0][0]))
    else:
        message.reply("I can't figure that out yet, ask someone in the data team...")

def check_each(incoming_message, date_value):
    m = re.search("(by|each) (day|week|month)", incoming_message.lower(), re.IGNORECASE)
    if m:
        if m.group(2) == "day":
            return "DATE_FORMAT(" + date_value + ", '%%Y-%%m-%%d')"
        if m.group(2) == "week":
            return "DATE_FORMAT(" + date_value + ", '%%Y-%%U')"
        if m.group(2) == "month":
            return "DATE_FORMAT(" + date_value + ", '%%Y-%%m-%%b')"
    return ""
        
def period_to_date(search_period):
    if 'W' in search_period:
        search_period = str(Week.fromstring(search_period).monday())
    if search_period.count('-') < 2:
        search_period += "-01"
    if search_period.count('-') < 2:
        search_period += "-01"
        
    return datetime.datetime.strptime(search_period, '%Y-%m-%d')

def date_to_string(date_in):
    return date_in.strftime('%Y-%m-%d')

def date_add_month(date_in, months=1):
    month = date_in.month - 1 + months
    year = int(date_in.year + month / 12 )
    month = month % 12 + 1
    day = min(date_in.day,calendar.monthrange(year,month)[1])
    return datetime.date(year,month,day)

def date_add_year(date_in, years=1):
    year = date_in.year + years
    month = date_in.month
    day = min(date_in.day,calendar.monthrange(year,month)[1])
    return datetime.date(year,month,day)
    
def date_add_day(date_in, days=1):
    return date_in + datetime.timedelta(days=days)
    
def date_add_week(date_in, weeks=1):
    return date_in + datetime.timedelta(weeks=weeks)


def plot_results(message, result, title, x_label, y_label):
    data = []
    xTickMarks = []
    plt.style.use('fivethirtyeight')
    fig = plt.figure()
    ax = fig.add_subplot(111)

    for row in result:
       data.append(int(row[1]))
       xTickMarks.append(str(row[0]))

    
    ## necessary variables
    ind = np.arange(len(data))                # the x locations for the groups
    width = 0.35                      # the width of the bars

    ## the bars
    rects1 = ax.bar(ind, data, width,
                    color='black',
                    error_kw=dict(elinewidth=2,ecolor='red'))


    # axes and labels
    ax.set_xlim(-width,len(ind)+width)
    ax.set_ylim(0,max(data))


    ax.set_ylabel(y_label)
    ax.set_xlabel(x_label)
    ax.set_title(title)

    ax.set_xticks(ind+width)
    xtickNames = ax.set_xticklabels(xTickMarks)

    plt.setp(xtickNames, rotation=45, fontsize=10)
    fig.subplots_adjust(bottom=0.2,left=0.15)
    filename = 'charts/' + str(uuid.uuid1()) + '.png'
    dir = os.path.dirname(filename)

    try:
        os.stat(dir)
    except:
        os.mkdir(dir)  
    plt.savefig(filename)
    post_image(filename, slackbot_settings.API_TOKEN, message.channel._body['id'])
    

def post_image(filename, token, channels):
    f = {'file': (filename, open(filename, 'rb'), 'image/png', {'Expires':'0'})}
    response = requests.post(url='https://slack.com/api/files.upload', data={'token': token, 'channels': channels, 'media': f}, headers={'Accept': 'application/json'}, files=f)
    #print(response.text)
