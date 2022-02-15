from dateutil import tz
from datetime import datetime
import re
from replit import db

TO_ZONE = tz.gettz('Australia/Melbourne')
START_DATE = datetime.strptime('2021-06-20', '%Y-%m-%d').replace(tzinfo = TO_ZONE)

WORDLE_PATTERN = re.compile("^[🟩⬜🟨⬛]+$")
NO_SCORE = 0
LOSS = -1

def update_arrs():
   for server in db:
    for user in db[server]:
      db[server][user].append(NO_SCORE)

def validateLine(line):
    return WORDLE_PATTERN.match(line)

# gets whether the message is a valid wordle thing
def validate(result):
    current_wordle = (datetime.utcnow().replace(tzinfo=tz.gettz('UTC')).astimezone(TO_ZONE) - START_DATE).days + 1
    lines = result.split('\n')
    if (len(lines) < 3):
      return False
    # check if the day actually makes sense
    if (int(lines[0].split(' ')[1]) > current_wordle):
        return False
    
    for i in lines[2:]:
        if not validateLine(i):
            return False
    return True


def getScore(result):
    if validate(result):
        header = result.split('\n')[0].split(' ')
        score = int(header[2].split('/')[0])
        day = int(header[1])
        if (score == 'X'):
            return (LOSS, day)
        else:
            return (int(score), day)

def addScore(score, day, server, user):
  if server not in db.keys():
    db[server] = {}
  if user not in db[server].keys():
    db[server][user] = [NO_SCORE] * ((datetime.utcnow().replace(tzinfo=tz.gettz('UTC')).astimezone(TO_ZONE) - START_DATE).days + 1)
  if (len(db[server][user]) < day):
    update_arrs()
  if (db[server][user][day - 1] == NO_SCORE):
    db[server][user][day - 1] = score