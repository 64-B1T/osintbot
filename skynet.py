import discord
import sys
import os
import subprocess 
import requests
import archiveis
import asyncio
import waybackpy
from datetime import date
from concurrent.futures import ThreadPoolExecutor

client = discord.Client()
agent_name = "Hal9001"
_executor = ThreadPoolExecutor(1)

agent_id = 3
event_id = 1
task_url = "https://quriosinty-dev.herokuapp.com/api/v1/task/"

prefix = "~"
user_agent = "Mozilla/5.0 (Windows NT 5.1; rv:40.0) Gecko/20100101 Firefox/40.0"
flag_queue = []

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    
#Main Controls
async def commands_interpreter(message):
    command = stripCommandList(message)[0]
    if command == "ping":
        await returnPing(message)
    elif command == "prepFlag":
        await prepFlag(message)
    elif command == "ShutDown":
        await shutDown(message)
    elif command == "Restart":
        await restart(message)
    elif command == "help":
        await help(message)
    elif command == "viewTask":
        await viewTask(message)
    elif command == "createChannel":
        await createChannel(message)
    elif command == "doneHere":
        await doneHere(message)
    elif command == "viewQueue":
        await viewQueue(message)
    else:
        rtrnmsg = "I'm sorry " + getName(message) + ", I'm afraid I can't do that."
        await message.channel.send(rtrnmsg)
    
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith(prefix):
        await commands_interpreter(message)
        
#Helpers 
def helpsave(wayback):
    return wayback.save()

async def archive_helper(url):
    wayback = waybackpy.Url(url, user_agent)
    #loop = asyncio.get_event_loop()
    #archive = await loop.run_in_executor(_executor, helpsave(wayback))
    
    #archive = await wayback.save()
    #
    archive = wayback.save()
    return archive
    
def makeTask(name, description, data, timeest, request_responses, maker):
    taskdef = {"name": name,
              #"status" : "Open",
              "description" : description,
              "request_responses" : request_responses,
              "time_estimate" : timeest,
              "data" : data, 
              "tool" : str(agent_id),
              "event_id" : str(event_id),
              "created_by" : maker}
    url = requests.post(task_url, data = taskdef)
    
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


#Temporary Functions (Until I can figure out how to use the API)
    
    
#Command Functions
async def returnPing(message):
    await message.channel.send("Pong")
    
  
async def prepFlag(message):
    cmds = stripCommandList(message)
    #archivelink = archiveis.capture(cmds[1])
    await message.channel.send("Beginning Flag Prep")
    def check(m):
        return m.author == message.author and m.channel == message.channel
    await message.channel.send("Would you like to submit any metadata or additional information? (N) to cancel")
    url = cmds[1]
    #archive = await asyncio.gather((archive_helper(url)))
    archive = await archive_helper(url)
    answer = await client.wait_for('message', timeout = 45, check=check)
    await message.channel.send("Thank you")
    context = "No additional Context"
    if answer.content.strip() is not "N":
        context = answer.content.strip()
     
    
    help_str = "New Flag: " + url + "\n" + "Archive Link: " + str(archive.archive_url) + "\n"
    help_str += "Archived At: " + str(archive.timestamp.strftime("%m/%d/%Y %H:%M:%S")) + "\n"
    help_str += "User Description: " + context
    await message.channel.send(help_str)
    await message.channel.send("Shall I submit the task request? (Y/N)")
    
    answer = await client.wait_for('message', timeout = 45, check = check)
    if answer.content.strip().lower() != "y":
        #await message.channel.send("This is what I got:(" + answer.content.strip().lower() + ")")
        await message.channel.send("Cancelling")
        return 
    data_format = {"URL" : url,
                   "ArchiveURL" : str(archive.archive_url),
                   "ArchiveTime" : str(archive.timestamp.strftime("%m/%d/%Y %H:%M:%S")),
                   "UserDescription" : context}
                   
    flag_queue.append(data_format)
    makeTask("Flag Creation Request", "Please Examine and Create Flags", data_format,
                "1 minute", 1, message.author.display_name)
    await message.channel.send("Submitted")

async def viewQueue(message):
    counter = 1
    returnStr = "```"
    for i in range(len(flag_queue)):
        returnStr+= "Flag " + str(i+1) + "\n"
        returnStr+= "URL: " + flag_queue[i]["URL"] + "\n"
        returnStr+= "Archive URL: " + flag_queue[i]["ArchiveURL"]+ "\n"
        returnStr+= "Archive Time: " + flag_queue[i]["ArchiveTime"]+ "\n"
        returnStr+= "Description: " + flag_queue[i]["UserDescription"]+ "\n"
        if counter > 14:
            await message.channel.send(returnStr+"```")
            returnStr = "```"
            counter = 0
    if counter > 0:
        await message.channel.send(returnStr+"```")
        

async def createChannel(message):
    cmds = stripCommandList(message)
    cmdstr = " ".join(cmds[1:])
    cmdl = cmdstr.split(",")
    
    server = message.guild;
    catid = discord.utils.get(server.categories, name = "Discussions")
    channel = await server.create_text_channel(cmdl[0], category=catid)
    if len(cmdl) > 1:
        await channel.send("This channel was created to discuss: " + cmdl[1])
    
async def doneHere(message):
    if message.channel.category.name == "Discussions":
        await message.channel.send("Are you sure? (Y/N)")
        def check(m):
            return m.author == message.author and m.channel == message.channel
        answer = await client.wait_for('message', timeout = 45, check = check)
        if answer.content.strip().lower() != "y":
            #await message.channel.send("This is what I got:(" + answer.content.strip().lower() + ")")
            await message.channel.send("Cancelling")
            return 
        await message.channel.send("Goodbye")
        await message.channel.delete()
    else:
        await message.channel.send("I don't have permission for that")
    
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
    x = requests.get(task_url+num)
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


with open('token.txt', 'r') as file:
    token = file.read().strip()
client.run(token)