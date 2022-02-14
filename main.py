import discord
from discord.ext import commands
import os
import re
import typing
from replit import db
import asyncio
import schedule
from webserver import keep_alive
from dateutil import tz
from datetime import datetime


client = commands.Bot(command_prefix="~")

TO_ZONE = tz.gettz('Australia/Melbourne')
START_DATE = datetime.strptime('2021-06-20', '%Y-%m-%d').replace(tzinfo = TO_ZONE)

WORDLE_PATTERN = re.compile("^[🟩⬜🟨⬛]+$")
NO_SCORE = 0
LOSS = -1
BOT_TOKEN = os.environ['TOKEN']

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
  if (db[server][user][day - 1] == NO_SCORE):
    db[server][user][day - 1] = score



def seconds_until(hours, minutes):
    given_time = datetime.time(hours, minutes).replace(tzinfo = TO_ZONE)
    now = datetime.datetime.now().replace(tzinfo = TO_ZONE)
    future_exec = datetime.datetime.combine(now, given_time)
    if (future_exec - now).days < 0:
      future_exec = datetime.datetime.combine(now + datetime.timedelta(days=1), given_time)

    return (future_exec - now).total_seconds()

def update_arrs():
   for server in db:
    for user in db[server]:
      db[server][user] = db[server][user] + [NO_SCORE]

schedule.every().day.at("00:01").do(update_arrs)
async def task():
  while True:
    schedule.run_pending()
    await asyncio.sleep(1)

@client.event
async def on_ready():
  client.loop.create_task(task())

@client.event
async def on_message(message):
  if (message.content.startswith('Wordle')):
    result = getScore(message.content)
    if (result is not None):
      addScore(result[0], result[1], str(message.guild.id), str(message.author.id))
  await client.process_commands(message)


@client.command()
async def scoreof(ctx,  member: typing.Optional[discord.Member], arg):
  if (member is None):
    member = ctx.author

  if str(ctx.guild.id) not in db.keys():
    await ctx.channel.send("This server has no Wordles recorded.")
    return

  if (arg is None):
    await ctx.channel.send("Syntax : $scoreof [user] day")

  member_id = str(member.id)

  if member_id not in db[str(ctx.guild.id)]:
    await ctx.channel.send(f"{member.name} has no Wordles recorded.")
    return
  day = int(arg)
  score = db[str(ctx.guild.id)][member_id][day - 1]
  if (score == NO_SCORE):
    await ctx.channel.send('No score found for that day.')
  elif (score == LOSS):
    await ctx.channel.send(f"Failed on day {day}.")
  else:
    await ctx.channel.send(f"Score for {ctx.author.name} for day {day}: {score}")

@client.command()
async def wordlestats(ctx, member: typing.Optional[discord.Member]):

  if str(ctx.guild.id) not in db.keys():
    await ctx.channel.send("This server has no Wordles recorded.")
    return

  if (member is None):
    member = ctx.author

  member_id = str(member.id)

  if member_id not in db[str(ctx.guild.id)]:
    await ctx.channel.send(f"{member.name} has no Wordles recorded.")
    return

  game_data = db[str(ctx.guild.id)][member_id]
  wins = 0
  losses = 0
  incompletes = 0
  total_score = 0

  for score in game_data:
    if score == 0:
      incompletes += 1
    elif score == -1:
      losses += 1
    else:
      wins += 1
      total_score += score
  
  avg = total_score / wins
  await ctx.channel.send(f"{member.name} has completed {wins}/{len(game_data)} Wordles, with a {avg} average score.")

@client.command()
async def parsewordles(ctx, limit = 1000):
  messages = await ctx.channel.history(limit = limit).flatten()
  await ctx.channel.send("Parsing wordles in this channel")
  for message in messages:
    if (message.content.startswith('Wordle')):
      result = getScore(message.content)
      if (result is not None):
        addScore(result[0], result[1], str(message.guild.id), str(message.author.id))
  await ctx.channel.send("Done!")

keep_alive()
client.run(BOT_TOKEN)