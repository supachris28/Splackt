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
         WHERE title like \'%%%s%%\' 
             and published_date < curdate()
             and type='books'
         order by published_date desc
        ''' % title)
    message.reply('Found %d Results' % len(ox))
    att = [
        {
            'fallback':'Search Results',
            'text':'\n'.join(map(lambda x: '%s - [%s] - %s' %x, ox[:20]))
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
