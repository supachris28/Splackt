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
    filename = str(uuid.uuid1()) + '.png'
    plt.savefig(filename)
    post_image(filename, slackbot_settings.API_TOKEN, message.channel._body['id'])
    

def post_image(filename, token, channels):
    f = {'file': (filename, open(filename, 'rb'), 'image/png', {'Expires':'0'})}
    response = requests.post(url='https://slack.com/api/files.upload', data={'token': token, 'channels': channels, 'media': f}, headers={'Accept': 'application/json'}, files=f)
    print(response.text)

    def check_each(incoming_message, date_value):
    m = re.search("(by|each) (day|week|month)", incoming_message.lower(), re.IGNORECASE)
    if m:
        if m.group(2) == "day":
            return "DATE_FORMAT(" + date_value + ", '%Y-%m-%d')"
        if m.group(2) == "week":
            return "DATE_FORMAT(" + date_value + ", '%Y-%U')"
        if m.group(2) == "month":
            return "DATE_FORMAT(" + date_value + ", '%Y-%m-%b')"
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
