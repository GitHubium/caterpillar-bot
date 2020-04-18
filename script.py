



'''

TODO


- Add polls graph at the end of 10 minutes
- .endpoll command to end all polls in current channel
- use https://pythonspot.com/matplotlib-pie-chart/
- Can't be more than 500 polls at once
- do @commands.cooldown(1, 30, commands.BucketType.user) for quotethat and addquote


'''


import random
import asyncio
import json
import time
import discord
from discord.ext import commands, tasks
import matplotlib.pyplot as plt
import numpy as np
import os

#load_dotenv()
TOKEN = "NjkzMTg4NzcxOTEwMzg1NzY0.Xn6F7g.FvIBCzO8UWXvKycKqNXS_vvVCLQ"#os.getenv('DISCORD_TOKEN')\

client= commands.Bot(command_prefix=['.','cat','<@693188771910385764>'], case_insensitive=True, help_command=None)

quotesCharacterLimit = 256

# variables
emptyjson = """
{ 
    "quotes": 
    {

    } 
}
"""
pollEmojis = ["1⃣", "2⃣", "3⃣", "4⃣", "5⃣", "6⃣", "7⃣", "8⃣", "9⃣", "0⃣", "🇦", "🇧", "🇨", "🇩", "🇪", "🇫", "🇬", "🇭", "🇮", "🇯"]
activePolls = [
#{
#     "timestamp": 999999999999
#     "guild": 1234567890,
#     "channel": 1234567890,
#     "message": 1234567890
#     "reactions": 
#     {
#         0: {
#              "option": "yes",
#              "count": 3
#         },
#         1: {
#              "option": "No",
#              "count": 2
#         },
#     }
#},
]
pctI = -1


class ReactionQueue:
    def __init__(self):
        self.queue = []#[timestamp, guild_id, channel_id, message_id, choices]
        self.lastEdit = 0
        self.editInterval = 1000# in ms

    async def alert(self, payload):
        user_id = payload.user_id
        if user_id == client.user.id:# if bot reacts to itself
            return
        
        message_id = payload.message_id
        channel_id = payload.channel_id
        guild_id = payload.guild_id


        choices = next((x for x in activePolls if \
            message_id == x["message"] and channel_id == x["channel"] and guild_id == x["guild"]), None)# if alerted (reacted) message is a poll
        if choices == None:
            return
        choices = choices["reactions"]


        # Don't add the same scan request if it's already in the queue
        now = time.time()
        found = False
        for item in self.queue:
            if item[3] == message_id and item[1] == guild_id and item[2] == channel_id and now - item[0] > self.editInterval:# ignore new request to same poll earlier (it will get checked anyways)
                found = True
                break
        if found:
            return
        else:
            self.queue.append([now, guild_id, channel_id, message_id, choices])
        

        if len(self.queue) > 2:# if already multiple items in the queue, don't imediately excecute a new edit, instead let the async while loop handle it
            print("Queue > 2 now")
            return

        elif len(self.queue) == 1:
            
            if time.time() > self.lastEdit+self.editInterval:
                print("Queue went from 0 -> 1 -> 0, time = "+str(self.queue[0][0]))
                await self.editOldest()
                self.lastEdit = time.time()
            else:
                await asyncio.sleep((time.time()-self.lastEdit)/1000)
                await self.editOldest()
                self.lastEdit = time.time()
                print("Waited a short time to empty queue ("+str(len(self.queue))+")")

        elif len(self.queue) == 2:
            print("Queue = 2 now")
            while len(self.queue) > 0:
                await self.editOldest()
                self.lastEdit = time.time()
                await asyncio.sleep(self.editInterval/1000)
                print("Emptying queue ("+str(len(self.queue))+")")


    async def editOldest(self):
        oldest = self.queue.pop(0)
        guild_id = oldest[1]
        channel_id = oldest[2]
        message_id = oldest[3]
        choices = oldest[4]

        channel = client.get_guild(guild_id).get_channel(channel_id)
        message = await channel.fetch_message(message_id)
        reactions = message.reactions

        description = "\n"
        for i in range(len(choices)):
            entity = choices[i]
            reaction = next((x for x in reactions if pollEmojis.index(str(x)) == i), None)
            if reaction == None:
                #TODO send warning message
                continue
            entity["count"] = reaction.count-1
            description += "\n**"+str(pollEmojis[i])+"** - "+entity["option"]+" ("+str(entity["count"])+")" 
 
        title = message.embeds[0].title 

        embed = discord.Embed(
            title = title,
            description = description,
            color=discord.Color.blurple()
        ) 
        await message.edit(embed=embed)

rQueue = ReactionQueue()

def exportPiChart(percentages, labels, title, file_name):
    UPLOAD_DIR = 'export'
    # Create direcotry if not exists
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

    AXIS = [-0.03, -0.09, 1.06, 1.06]
    fracs = percentages
    labels = labels
    TITLE = title
    # Make a square figure and axes
    plt.figure(1, figsize=(6, 6))
    global pctI
    pctI = -1
    def func(pct):
        global pctI
        pctI += 1
        if pct == 0:
            return ""
        return "{:.1f}%\n{:.16}".format(pct, labels[pctI])
    ax = plt.axes(AXIS)
    ax.pie(percentages, autopct=lambda pct:func(pct), textprops={'color':"w"})
    plt.title(TITLE, bbox={'facecolor': '0.8', 'pad': 5}, y=0.95)
    plt.savefig(UPLOAD_DIR+'/'+file_name, transparent=True)

def writeDB(jsonData, filename):
    with open("servers/"+str(filename) + ".json", 'w') as outfile:
        json.dump(jsonData, outfile, sort_keys=True, indent=4, ensure_ascii=False)

def readDB(filename):
    with open("servers/"+str(filename) + ".json", 'r') as infile:
        parsed_json = json.load(infile)
    return parsed_json

def addQuote(json, addedBy, quote, dateAdded):
    length = len(json["quotes"])
    json["quotes"].update({str(length):
        {"addedBy":addedBy,
        "content":quote[0:quotesCharacterLimit],
        "dateadded":str(dateAdded)
        }})

def formatQuoteItem(ctx, key, val):
    displayName = ctx.guild.get_member(val["addedBy"]).display_name
    return "**`" + key + "`** - "+val["content"]+" - __" + displayName + "__"

@client.command(alias=["add","addquote","quoteadd"])
async def addquote(ctx, *, newQuote):
    parsed_json = readDB(ctx.guild.id)
    addQuote(parsed_json, ctx.message.author.id, newQuote, ctx.message.created_at.date()) # Update local variable holding json
    writeDB(parsed_json, ctx.guild.id) # Rewrite to file
    await ctx.send("Quote added: \""+newQuote+"\"")


@client.command()
@commands.cooldown(1, 30, commands.BucketType.user)
async def quotethat(ctx, optionalId=None):
    parsed_json = readDB(ctx.guild.id)
    if optionalId == None:
        messages = []
        async for elem in ctx.channel.history(limit=2):
            messages.append(elem)
        msg = messages[1]
    else:
        msg = await ctx.channel.fetch_message(optionalId)

    if msg.author == client.user:
        await ctx.send("Unable to quote myself")
        return

    newQuote = msg.content

    addQuote(parsed_json, msg.author.id, newQuote, msg.created_at.date()) # Update local variable holding json
    writeDB(parsed_json, ctx.guild.id) # Rewrite to file
    
    await ctx.send("Quote added: \""+newQuote+"\"")

@client.command()
async def quoteid(ctx, id):
    quotethat(ctx, id)

@client.command()
async def randomquote(ctx):
    parsed_json = readDB(ctx.guild.id)
    if len(parsed_json["quotes"]) == 0:
        await ctx.send("No quotes to choose from! Add a new quote with `.addQuote` and `.quoteThat` commands.")
        return
    num = random.randint(0, len(parsed_json["quotes"]) - 1)
    await ctx.send("#**`" + str(num) + "`**: " + parsed_json["quotes"][str(num)]["content"])

@client.command(aliases=["all","allquotes"])
async def quotes(ctx):
    parsed_json = readDB(ctx.guild.id)
    mess = ""
    for key in parsed_json["quotes"]:
        val = parsed_json["quotes"][key]
        mess += formatQuoteItem(ctx, key, val)+"\n"
    if mess == "":
        mess = "Currently no quotes for this server - add a new quote with **.addQuote**"
    await ctx.send(mess)

@client.command(aliases=["quotesby","quoteby"])
async def by(ctx, user):
    parsed_json = readDB(ctx.guild.id)
    mess = ""
    for key in parsed_json["quotes"]:
        val = parsed_json["quotes"][key]
        
        if val["addedBy"] == ctx.message.mentions[0].id:#TODO bug here, it may return User instead of array
            mess += formatQuoteItem(ctx, key, val)+"\n"
    if mess == "":
        mess = "No quotes by "+user+" found"
    await ctx.send(mess)

@client.command(aliases=["del","delete"])
async def deletequote(ctx, ind):
    parsed_json = readDB(ctx.guild.id)
    if ind not in parsed_json["quotes"]:
        await ctx.send("Number not found, type .allquotes for details")
        return  

    pjq = parsed_json["quotes"]
    for i in range(int(ind), len(pjq)-1):
        parsed_json["quotes"][str(i)] = pjq[str(i+1)]#shift items down
    del parsed_json["quotes"][str(len(pjq)-1)]#remove last item
    
    writeDB(parsed_json, ctx.guild.id) # Rewrite to file
    await ctx.send("Quote **`{}`** deleted".format(ind))


@client.command()
async def help(ctx):
    with open('commands.txt', 'r') as file:
        commands = file.read()

    embed = discord.Embed(
        description=commands,
        color=discord.Color.green()
    ) 

    embed.set_author(
        name="Caterpillar Help - Commands",
         icon_url="https://cdn.discordapp.com/avatars/693188771910385764/c1da0eab65bc2cc81d64dc7f5845b1ff.png"
    )
    await ctx.send(embed=embed)

@client.command(pass_context=True)
async def ping(ctx):
    t = await ctx.send('Pong!')
    ms = (t.created_at-ctx.message.created_at).total_seconds() * 1000
    await t.edit(content='Pong! Took: {}ms'.format(int(ms)))

@client.command()
async def play(ctx, *, playing):
    await client.change_presence(activity=discord.Game(playing))
    await ctx.send("I'm now playing "+playing)

@client.command()
async def say(ctx, *, thing):
    await ctx.send(thing)

@client.command()
async def status(ctx, *, inputStatus):
    sta = {
        "dnd": discord.Status.dnd,
        "do not disturb": discord.Status.dnd,
        "idle": discord.Status.idle,
        "online": discord.Status.online,
        "invisible": discord.Status.invisible,
        "offline": discord.Status.offline,
        "mro": discord.Status.mro
    }
    status = sta[inputStatus.lower()]
    await client.change_presence(status=status)
    await ctx.send("My status is now "+str(status))

@client.command()
async def invite(ctx):
    if ctx.author.id != 439076109678805004:
        await ctx.send("Only the developer can use this command")
        return
    
    await ctx.send("https://discordapp.com/api/oauth2/authorize?client_id=693188771910385764&permissions=8&scope=bot")

   
@client.command()
async def poll(ctx, question, *args):
    description = "\n"
    i = 0
    for a in args:
        description += "\n**"+str(pollEmojis[i])+"** - "+a+" (0)"
        i += 1

    embed = discord.Embed(
        title=question,
        description=description,
        color=discord.Color.default()
    ) 


    embededMsg = await ctx.send(embed=embed)
    choices = {}
    i = 0
    for a in args:
        emoji = await embededMsg.add_reaction(pollEmojis[i])
        choices[i] = {
            "option": a,
            "count": 0
        }
        i += 1
    activePolls.append({
        "timestamp": time.time(),
        "guild": embededMsg.guild.id,
        "channel": embededMsg.channel.id,
        "message": embededMsg.id,
        "reactions": choices
    })

# This is called once the client has connected, this function checks if there is a .json file for each currently disconnected server, if it doesnt exist, it creates one.
@client.event
async def on_ready():
    print("Logged in as")
    print(client.user.name)
    print(client.user.id)
    print("------")

    if not os.path.exists("servers"):
        os.makedirs("servers")

    for s in client.guilds:
        filename = str(s.id) + ".json"
        try:
            with open("servers/"+filename) as file:
                print("")
        except IOError: # File not created
            print("No store exists for {} ({}), creating now".format(str(s), str(s.id)))
            with open("servers/"+filename, 'w') as outfile:
                parsed = json.loads(emptyjson)
                json.dump(parsed, outfile, sort_keys = True, indent = 4, ensure_ascii = False)
    
    await client.change_presence(status=discord.Status.online, activity=discord.Game('.help'))

    params = {
          "font.size": "18",
          "font.weight": "bold",
          "font.family": "verdana"}
    plt.rcParams.update(params)

    deleteOldPolls.start()

    print("ready")

@client.event
async def on_raw_reaction_add(payload):
    await rQueue.alert(payload)

@client.event
async def on_raw_reaction_remove(payload):
    await rQueue.alert(payload)

@tasks.loop(seconds=15)
async def deleteOldPolls():
    now = time.time()
    for i in range(len(activePolls)-1, -1, -1):
        if now > activePolls[i]["timestamp"] + 60:# 10 seconds
            thePoll = activePolls.pop(i)
           
            channel = client.get_guild(thePoll["guild"]).get_channel(thePoll["channel"])
            message = await channel.fetch_message(thePoll["message"])
            title = message.embeds[0].title
            reactions = message.reactions
            choices = thePoll["reactions"]
            percentages = []
            labels = []
            
            for i in range(len(choices)):
                entity = choices[i]
                reaction = next((x for x in reactions if pollEmojis.index(str(x)) == i), None)
                if reaction == None:#other reactions
                    continue
                percentages.append(reaction.count-1)
                labels.append(entity["option"])
    
            total = sum(percentages)
            if total == 0:
            
                embed = discord.Embed(
                    title = "No Results for "+title,
                    description = "If you think this is a bug, DM me <@439076109678805004>",
                    color=discord.Color.red()
                )
                await channel.send(embed=embed)
            else:

                winner = None
                isTie = False
                largest = 0
                for i in range(len(percentages)):
                    if percentages[i] > largest:
                        largest = percentages[i]
                        winner = i
                        isTie = False
                    elif percentages[i] == largest:
                        isTie = True
                    percentages[i] = round(100*percentages[i]/total)


                
                fileName = "pie.png"
                exportPiChart(percentages, labels, title, fileName)
                file = discord.File("export/"+fileName)
                if isTie:
                    winnerText = "Tie"
                else:
                    winnerText = "Winner: "+choices[winner]["option"]+" ("+(choices[winner]["count"]-1)+" Votes)"
                embed = discord.Embed(
                    title=winnerText,
                    color=discord.Color.green(),
                    image={
                        "url": "attachment://pie.png"
                    }
                )

                await channel.send(embed=embed, file=file)
                
@client.command()
@commands.is_owner()
async def shutdown(ctx):
    await ctx.bot.logout()

client.run(TOKEN)

