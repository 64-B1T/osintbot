import discord
import sys
import os
import subprocess 
import requests

client = discord.Client()

prefix = "~"

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    
#Command Functions
async def returnPing(message):
    await message.channel.send("Pong")
  
async def newFlag(message):
    await message.channel.send("Not Implemented Yet, But Someday...")
    
async def shutDown(message):
    await message.channel.send("Shutting Down. Good Bye Dave")
    exit()
    
async def restart(message):
    await message.channel.send("Rebooting....")
    subprocess.call(["python", os.path.join(sys.path[0], __file__)] + sys.argv[1:])
    exit()

async def viewTask(message):
    cmds = stripCommandList(message)
    num = cmds[1]
    x = requests.get("https://quriosinty-dev.herokuapp.com/api/v1/task/"+num)
    if x.ok:
        await message.channel.send(formatTask(x.json()))
    else:
        await message.channel.send("I didn't find anything")
    
    
    
async def help(message):
  
    helpMenu =   "My prefix is: " + prefix + "\n" + """
        ping:\t\tCheck if the bot is live
        newFlag:\t\tAdd a new flag to quriosinty
        ShutDown:\t\tShut down the bot
        Restart:\t\tRestart the bot
        ViewTasks:\t\tView A Specified Task
        """
    await message.channel.send(helpMenu)
#Helpers
def getName(message):
    return message.author.display_name
   
def stripCommandList(message):
    return message.content[len(prefix):].split()
   
def formatTask(task):
    taskstr = task['name'] + " " + task['status'] + " since " + task['date_created'] + "\n"
    taskstr += str(task['request_responses']) + " responses so far " + task['time_estimate'] + "(s) estimated\n"
    taskstr += "Description:\n" + task['description'] + "\n"
    taskstr += "Flag URL: " + task['flag']['url']
    return taskstr
#Main Controls
async def commands_interpreter(message):
    command = stripCommandList(message)[0]
    if command == "ping":
        await returnPing(message)
    elif command == "newFlag":
        await newFlag(message)
    elif command == "ShutDown":
        await shutDown(message)
    elif command == "Restart":
        await restart(message)
    elif command == "help":
        await help(message)
    elif command == "ViewTask":
        await viewTask(message)
    else:
        rtrnmsg = "I'm sorry " + getName(message) + ", I'm afraid I can't do that."
        await message.channel.send(rtrnmsg)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith(prefix):
        await commands_interpreter(message)

with open('token.txt', 'r') as file:
    token = file.read().strip()
client.run(token)