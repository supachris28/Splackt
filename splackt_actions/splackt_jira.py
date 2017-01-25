from slackbot.bot import respond_to, listen_to
import io
import re
import json
import requests
import slackbot_settings
import traceback

jira_reg = '(\w+-\d+)'
@listen_to(jira_reg)
@respond_to(jira_reg)
def check_slack(message, incoming_message):
    try:
        jira_url = 'https://packtpub.atlassian.net/rest/api/2/search?jql=id=' + incoming_message
        print('checking JIRA for ' + incoming_message)
        r = requests.get(url=jira_url, headers={'Authorization': slackbot_settings.JIRA_AUTH, 'Content-Type': 'application/json', 'accept':'application/json'})
        #print (r)
        j = r.json()
        #print(j)
        if r.status_code == 200 and j['total'] == 1:
            title = j['issues'][0]['fields']['summary']
            status = j['issues'][0]['fields']['status']['name']
            key = j['issues'][0]['key']
            url = 'https://packtpub.atlassian.net/browse/' + key
            description = j['issues'][0]['fields']['description']
            creator = j['issues'][0]['fields']['creator']['displayName']
            assignee = ''
            if j['issues'][0]['fields']['assignee']:
                assignee = j['issues'][0]['fields']['assignee']['displayName']
            reply = key + ': `' + status + '`'
            att = [
                {
                    'fallback': description,
                    'title': title,
                    'title_link': url,
                    'fields': [
                        {
                            "title": "Creator",
                            "value": creator,
                            "short": True
                        },
                        {
                            "title": "Assignee",
                            "value": assignee,
                            "short": True
                        }
                    ],
                    'text': description
                }
            ]
            message.send_webapi(reply, json.dumps(att))
    except:
        print('something went wrong....')
        print(traceback.format_exc())