import discord
import os
import typing
import asyncio
import pandas as pd
import schedule
from webserver import keep_alive
from replit import db
from discord.ext import commands
from dateutil import tz
from datetime import datetime
from wordle import *

intents = discord.Intents.default()
intents.members = True
client = commands.Bot(command_prefix="~", intents=intents)

TO_ZONE = tz.gettz('Australia/Melbourne')
BOT_TOKEN = os.environ['TOKEN']

# code that handles updating each day with new wordle hopefully this works
def seconds_until(hours, minutes):
    given_time = datetime.time(hours, minutes).replace(tzinfo = TO_ZONE)
    now = datetime.datetime.now().replace(tzinfo = TO_ZONE)
    future_exec = datetime.datetime.combine(now, given_time)
    if (future_exec - now).days < 0:
      future_exec = datetime.datetime.combine(now + datetime.timedelta(days=1), given_time)

    return (future_exec - now).total_seconds()


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
  # detects wordle and if finds wordle then adds result into database
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
    await ctx.channel.send(f"Score for {member.name} for day {day}: {score}")

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

@client.command()
async def scoreboard(ctx, order_by: typing.Optional[str]):
  if str(ctx.guild.id) not in db.keys():
    await ctx.channel.send("This server has no Wordles recorded.")
    return
  
  # construct scoreboard
  dic = {}
  for user in db[str(ctx.guild.id)]:
    game_data = db[str(ctx.guild.id)][user]
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
    username = client.get_user(int(user)).name
    dic[username] = {'Average': avg, 'Clears':wins}

  # turn into df for easy sorting and printing
  dic = pd.DataFrame.from_dict(dic, orient='index')
  if ((order_by is None) or (order_by == 'avg')):
    await ctx.channel.send(f"```{dic.sort_values(by = 'Average', ascending = True).to_string()}```")
  
  elif (order_by == 'clears'):
    await ctx.channel.send(f"```{dic.sort_values(by = 'Clears', ascending = False).to_string()}```")
  
  else:
    await ctx.channel.send("Syntax: ~scoreboard [clears/avg]")


keep_alive()
client.run(BOT_TOKEN)
