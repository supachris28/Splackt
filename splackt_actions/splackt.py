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
import matplotlib.pyplot as plt
import slackbot_settings

#import pandas

g = py2neo.Graph('http://neo4j:skynet@178.62.55.202:7474/db/data')


# standard word lists
product_types = "(book|ebook|video|subscription)"
sales_keywords = "(sales|value|revenue|quantity)"
quantity_keywords = "(many (\w+ )* ?sold|sell|quantity)"
engagement_keywords = "(page ?views|engagement)"


@respond_to('(joke|doughnut|donut)')
@listen_to('(joke|doughnut|donut)')
def joke(message, incoming_message):
    joke_response = requests.get('http://tambal.azurewebsites.net/joke/random')
    message.send_webapi(joke_response.json()['joke'])
    

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
            message.reply('\n'.join(map(lambda x: '%s - %s' %x, ox)))
        else:
            message.reply("Answer: " + str(ox[0][0]))
    else:
        message.reply("I can't figure that out yet, ask someone in the data team...")

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


@respond_to('hello')
def hello(message):
    message.reply('yo')


@respond_to('who are you', re.IGNORECASE)
def whoami(message):
    message.reply('I am Splackt, Greg wrote me to test the idea of Slackbots!')


@respond_to('title (.*)',re.IGNORECASE)
def get_title(message, title=''):
    message.reply('k, looking for titles which look like \'%s\'' % title)
    ans = titlator.get_title(title)
    if len(ans) == 1:
        message.reply('Found a match!')
        
    else:
        message.reply('No Exact Matches, heres the top match:')
    att = [
        {
            'fallback':'search results',
            'text': '\n'.join(str(i)+' :  '+str(j) for i,j in ans[0].items())
        }
    ]
    message.send_webapi('',json.dumps(att))

@respond_to('titles like (.*)',re.IGNORECASE)
def search_titles(message, title=''):
    message.reply('k, Looking for 20 recent titles containing the string "%s"'% title)
    ox = titlator.db.p.ex('''
        SELECT isbn10, published_date,CONVERT(title using ascii) from home.dim_products
         WHERE title like \'%%'''+title+'''%%\' 
             and published_date < curdate()
             and type='books'
         order by published_date desc
        ''')
    message.reply('Found %d Results' % len(ox))
    att = [
        {
            'fallback':'Search Results',
            'text':'\n'.join(map(lambda x: '{0} - [{1}] - {2}'.format(*x), ox[:20]))
        }
    ]
    message.send_webapi('',json.dumps(att))

@respond_to('isbn10 (\w+)', re.IGNORECASE)
def get_info(message, isbn = ''):
    if len(isbn)!= 10:
        message.reply('%s doesnt look like an isbn to me. Should be 10 digits')



@respond_to('getme (.*)', re.IGNORECASE)
def getme(message, tags =''):
    tags = tags.split(',')
    message.reply('k, looking for sections about %s' % ','.join(tags))
    answer = g.run('''
        MATCH (n:StackOverflowTag)
        WHERE n.name in {tags}
        MATCH (n)<-[r:BOOKPART_MENTIONS]-(a:Section)
        with n.name as tag,toFloat(r.count) as about, a as t
        where 
        with t, avg(about) as aboutness,count(distinct tag) as o
        WHERE o=length({tags})
        MATCH (t)-[:FROM]->(c:Chapter)-[:FROM]->(b:Book)
        return aboutness, b.title as bname, b.isbn13 as isbn, c.title as chap_title,t.title as sec_title,o
        order by aboutness desc limit 10
        ''', {'tags':tags}).data()
    message.reply('k, found %d items, displaying top 10' % len(answer))
    for i in answer[:10]:
        message.reply('Section: %s' % i.sec_title)
        message.reply('from chapter: %s' % i.chap_title)
        message.reply('from book: %s' % i.bname)
        message.reply('has score %.2f' % i.aboutness)
        message.reply('========')

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
