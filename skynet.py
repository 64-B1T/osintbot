import sys
import os
import subprocess
import requests
import asyncio
import functools
import concurrent.futures
import json
from datetime import date
from configparser import ConfigParser

import discord
import archiveis
import waybackpy


client = discord.Client()
agent_name = "Hal9001"


config = ConfigParser()
config.read("./config.ini")
agent_id = config["DEFAULT"]["AgentId"]
event_id = config["DEFAULT"]["EventId"]
tool_token = config["DEFAULT"]["ToolToken"]
task_url = config["DEFAULT"]["QuriosintyUrl"] + "task/"
bot_token = config["DEFAULT"]["BotToken"]
flag_queue_fname = config["DEFAULT"]["FlagQueueFname"]
processed_flags_fname = config["DEFAULT"]["ProcessedFname"]
token_json = config["DEFAULT"]["TokenJson"]


prefix = "~"
user_agent = "Mozilla/5.0 (Windows NT 5.1; rv:40.0) Gecko/20100101 Firefox/40.0"
flag_queue = []


@client.event
async def on_ready():
 
    print("We have logged in as {0.user}".format(client))


# Main Controls
async def help(message):

    helpMenu = (
        "My prefix is: "
        + prefix
        + "\n```"
        + """
        ping:\tCheck if the bot is live
        prepFlag:\tAdd and automatically archive a new flag
        ShutDown:\tShut down the bot
        Restart:\tRestart the bot
        ViewTasks:\tView A Specified Task
        createChannel:\tCreate a new channel dedicated to a topic (as a one word argument)
        doneHere:\t delete the channel command was issued from. Must be a discussion channel 
        viewQueue:\t view the current flag submission queue
        getOpenFlag:\t Pull a flag from the queue for manual submission to quriosinty
        searchFlags:\t Search by either URL or keywords or both for known flags
        editFlagDesc:\t editFlagDesc [Uid} [Desc} edit a flag description via uid
        """
        + "```"
    )
    await message.channel.send(helpMenu)


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
    elif command == "getOpenFlag":
        await getOpenFlag(message)
    elif command == "searchFlags":
        await searchFlags(message)
    elif command == "editFlagDesc":
        await editFlagDesc(message)
    elif command == "register":
        await register(message)
    elif command == "delete":
        await delete(message)
    else:
        rtrnmsg = "I'm sorry " + getName(message) + ", I'm afraid I can't do that."
        await message.channel.send(rtrnmsg)


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith(prefix):
        await commands_interpreter(message)


# Helpers
def checkProcessed(URL, mode = 0):
    queueItems = []
    procItems = []
    with open(flag_queue_fname, 'r') as json_file:
        data = json.load(json_file)
    for i in range(data["lower"], data["upper"] + 1):
        if data[str(i)]["URL"] == URL or URL in data[str(i)]["UserDescription"]:
            if mode == 0:
                return data[str(i)], 1, str(i)
            queueItems.append([data[str(i)], str(i)])
    with open(processed_flags_fname, 'r') as json_file:
        data = json.load(json_file)
    for i in range(data["lower"], data["upper"] + 1):
        if data[str(i)]["URL"] == URL or URL in data[str(i)]["UserDescription"]:
            if mode == 0:
                return data[str(i)], 2, str(i)
            procItems.append([data[str(i)], str(i)])
    if mode == 0:
        return None, 0, str(i)
    return queueItems, procItems, None
    
def helpsave(wayback):
    return wayback.save()
    
    
def archive_helper(url):
    wayback = waybackpy.Url(url, user_agent)
    # loop = asyncio.get_event_loop()
    # archive = await loop.run_in_executor(_executor, helpsave(wayback))

    # archive = await wayback.save()
    #
    archive = wayback.save()
    return archive
    

async def makeTask(message, name, description, data, timeest, request_responses, maker):
    with open(token_json, 'r') as json_file:
        data2 = json.load(json_file)
    if not str(message.author.id) in data2:
        await message.channel.send("You are not registered, so I can't submit to the Quriosinty Queue, however I've submitted to the local queue")
        return
    auth_token = data2[str(message.author.id)]
    headers = {'content-type': 'application/json', 'Authorization': 'Token {}'.format(auth_token)}
    taskdef = {
        "name": name,
        "description": description,
        "request_responses": request_responses,
        "time_estimate": timeest,
        "data": data,
        "tool": str(agent_id),
        "event_id": str(event_id),
    }
    reqd = json.dumps(taskdef)
    if str(message.author.id) in reqd:
        print("Security Flaw")
        print(reqd)
        return
    requests.post(task_url, data=reqd, headers=headers)
    await message.channel.send("Submitted")


def getName(message):
    return message.author.display_name


def stripCommandList(message):
    return message.content[len(prefix) :].split()

def formatFlagTask(item):
    returnStr = "URL: " + item["URL"] + "\n"
    returnStr += "Archive URL: " + item["ArchiveURL"] + "\n"
    returnStr += "Archive Time: " + item["ArchiveTime"] + "\n"
    returnStr += "Description: " + item["UserDescription"] + "\n"
    returnStr += "Added By: " + item["AddedBy"] + "\n"
    if "ProcessedBy"  in item:
        returnStr += "Processed By: " + item["ProcessedBy"] + "\n"
    returnStr += "\n"
    return returnStr
    
def formatTask(task):
    taskstr = (
        task["name"] + " " + task["status"] + " since " + task["date_created"] + "\n"
    )
    taskstr += (
        str(task["request_responses"])
        + " responses so far "
        + task["time_estimate"]
        + "(s) estimated\n"
    )
    taskstr += "Description:\n" + task["description"] + "\n"
    taskstr += "Flag URL: " + task["flag"]["url"]
    return taskstr

def preppendQueue(task, fname):
    with open(fname, 'r') as json_file:
        data = json.load(json_file)
    data[str(data["lower"]-1)] = task
    data["lower"] = data["lower"] -1
    data["num"] = data["num"] + 1
    with open(fname, 'w') as json_file:
        json.dump(data, json_file)

def appendQueue(task, fname):
    with open(fname, 'r') as json_file:
        data = json.load(json_file)
    data[str(data["upper"] + 1)] = task
    data["upper"] = data["upper"] + 1
    data["num"] = data["num"] + 1
    with open(fname, 'w') as json_file:
       json.dump(data, json_file)

def popQueue(fname):
    with open(fname, 'r') as json_file:
        data = json.load(json_file)
    if data["num"] == 0:
        return None
    retr = data[str(data["lower"])]
    data.pop(str(data["lower"]))
    data["lower"] = min(data["lower"]+1, data["upper"])
    data["num"] = data["num"] - 1
            
    with open(fname, 'w') as json_file:
        json.dump(data, json_file)
     
    return retr
    
def peekQueue(fname):
    with open(fname, 'r') as json_file:
        data = json.load(json_file)
    if data["num"] == 0:
        return None
    retr = data[str(data["lower"])]
    return retr 


    
# Temporary Functions (Until I can figure out how to use the API)


# Command Functions
async def register(message):
    terms = stripCommandList(message)
    token = terms[1]
    with open(token_json, 'r') as json_file:
        data = json.load(json_file)
    data[str(message.author.id)] = token
    with open(token_json, 'w') as json_file:
        json.dump(data, json_file)
    await message.channel.send("Registered!")

    
async def searchFlags(message):
    terms = stripCommandList(message)
    qres = []
    pres = []
    for term in terms[1:]:
        queued, processed, _ = checkProcessed(term, 1)
        for q in queued:
            if q not in qres:
                qres.append(q)
        for p in processed:
            if p not in pres:
                pres.append(p)
    returnStr = ""
    counter = 1
    if queued != []:
        
        returnStr = "In Queue:\n```"
        for i in range(len(qres)):
            returnStr += "Flag " + str(counter) + "\n"
            returnStr += "UID: Q" + str(qres[i][1]) + "\n"
            returnStr += formatFlagTask(qres[i][0])
            counter += 1
            if counter > 14:
                await message.channel.send(returnStr + "```")
                returnStr = "```"
                counter = 0
        if counter > 0:
            returnStr+= "```\n"
    if processed != []:
        returnStr += "In Processed:\n```"
        for i in range(len(pres)):
            returnStr += "Flag " + str(counter) + "\n"
            returnStr += "UID: P" + str(pres[i][1]) + "\n"
            returnStr += formatFlagTask(pres[i][0])
            counter += 1
            if counter > 14:
                await message.channel.send(returnStr + "```")
                returnStr = "```"
                counter = 0
        if counter > 0:
            await message.channel.send(returnStr + "```")
    if returnStr == "":
        await message.channel.send("I didn't find anything")
    else:
        await message.channel.send(returnStr)
        
        
async def editFlagDesc(message):
    terms = stripCommandList(message)
    uid = terms[1]
    desc = " ".join(terms[2:])
    fname = flag_queue_fname
    if uid[0] == "P":
        fname = processed_flags_fname
    with open(fname, 'r') as json_file:
        data = json.load(json_file)
    keyname = uid[1:]
    print(keyname)
    if not keyname in data:
        await message.channel.send("Didn't find anything matching that UID")
        return
    data[str(uid[1:])]["UserDescription"] = desc            
    with open(fname, 'w') as json_file:
        json.dump(data, json_file)
    await message.channel.send("Edits Submitted")
    
async def delete(message):
    terms = stripCommandList(message)
    uid = terms[1]
    fname = flag_queue_fname
    if uid[0] == "P":
        fname = processed_flags_fname
    with open(fname, 'r') as json_file:
        data = json.load(json_file)
    data.pop(uid)
    with open(fname, 'w') as json_file:
        json.dump(data, json_file)
    
    
async def getOpenFlag(message):
    item = popQueue(flag_queue_fname)
    if item == None:
        await message.channel.say("Nothing to do!")
        return 
    returnStr = "Here's what I've got for you:\n"
    returnStr += "```" + formatFlagTask(item) + "```"
    returnStr += "When you've finished, please type \"Done\""
    
    await message.channel.send(returnStr)
    def check(m):
        return m.author == message.author and m.channel == message.channel
    try:
        answer = await client.wait_for('message', timeout = 90, check=check)
    except asyncio.TimeoutError:
        await message.channel.send("Cancelled")
        preppendQueue(item,flag_queue_fname)
        return
    
    if "done" in answer.content.lower().strip():
        await message.channel.send("Thank you")
        appendQueue(item, processed_flags_fname)
        return
    else:
        await message.channel.send("Cancelled")
        preppendQueue(item,flag_queue_fname)

async def viewQueue(message):
    with open(flag_queue_fname, 'r') as json_file:
        data = json.load(json_file)
    counter = 0
    iter = 0
    returnStr = "```"
    #for i in range(len(flag_queue)):
    for i in range(data["lower"], data["upper"]+1):
        counter+=1
        item = data[str(i)]
        returnStr += "Flag " + str(i - data["lower"] + 1) + "\n"
        returnStr += formatFlagTask(item)
        if counter > 14:
            await message.channel.send(returnStr + "```")
            returnStr = "```"
            counter = 0
    if counter > 0:
        await message.channel.send(returnStr + "```")
        
async def returnPing(message):
    await message.channel.send("Pong")


async def prepFlag(message):
    cmds = stripCommandList(message)
    # archivelink = archiveis.capture(cmds[1])
    url = cmds[1].strip()
    possdata, type, _ = checkProcessed(url)
    if possdata is not None:
        if type == 1:
            await message.channel.send("Requested Flag is already in Queue. Here are the Details:\n```" + formatFlagTask(possdata) + "```")
            return 
        await message.channel.send("Requested Flag has already been processed. Here are the Details:\n```" + formatFlagTask(possdata) + "```")
        return
    await message.channel.send("Beginning Flag Prep")

    def check(m):
        return m.author == message.author and m.channel == message.channel
    
    
    await message.channel.send("Archiving... Please wait, this may take some time.")
    
    loop = asyncio.get_running_loop()
    archive = await loop.run_in_executor(None, functools.partial(archive_helper, url))
    await message.channel.send("Would you like to submit any metadata or additional information? (N) to cancel")
    
    #archive = await asyncio.gather((archive_helper(url)))
    
    #archive = await archive_helper(url)
    #archive_helper(url)
    answer = await client.wait_for('message', timeout = 45, check=check)
    await message.channel.send("Thank you")
    

    context = "No additional Context"
    if answer.content.strip() is not "N":
        context = answer.content.strip()

    help_str = (
        "New Flag: " + url + "\n" + "Archive Link: " + str(archive.archive_url) + "\n"
    )
    help_str += (
        "Archived At: " + str(archive.timestamp.strftime("%m/%d/%Y %H:%M:%S")) + "\n"
    )
    help_str += "User Description: " + context
    await message.channel.send(help_str)
    await message.channel.send("Shall I submit the task request? (Y/N)")

    answer = await client.wait_for("message", timeout=45, check=check)
    if answer.content.strip().lower() != "y":
        # await message.channel.send("This is what I got:(" + answer.content.strip().lower() + ")")
        await message.channel.send("Cancelling")
        return
    data_format = {
        "URL": url,
        "ArchiveURL": str(archive.archive_url),
        "ArchiveTime": str(archive.timestamp.strftime("%m/%d/%Y %H:%M:%S")),
        "UserDescription": context,
        "AddedBy":message.author.display_name
    }

    appendQueue(data_format, flag_queue_fname)
    await makeTask(
        message,
        "Flag Creation Request",
        "Please Examine and Create Flags",
        data_format,
        "1 minute",
        1,
        message.author.display_name,
    )
    





async def createChannel(message):
    cmds = stripCommandList(message)
    cmdstr = " ".join(cmds[1:])
    cmdl = cmdstr.split(",")

    server = message.guild
    catid = discord.utils.get(server.categories, name="Discussions")
    channel = await server.create_text_channel(cmdl[0], category=catid)
    if len(cmdl) > 1:
        await channel.send("This channel was created to discuss: " + cmdl[1])


async def doneHere(message):
    if message.channel.category.name == "Discussions":
        await message.channel.send("Are you sure? (Y/N)")

        def check(m):
            return m.author == message.author and m.channel == message.channel

        answer = await client.wait_for("message", timeout=45, check=check)
        if answer.content.strip().lower() != "y":
            # await message.channel.send("This is what I got:(" + answer.content.strip().lower() + ")")
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
    x = requests.get(task_url + num)
    if x.ok:
        await message.channel.send(formatTask(x.json()))
    else:
        await message.channel.send("I didn't find anything")





client.run(bot_token)
