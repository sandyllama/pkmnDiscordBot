# #!/usr/bin/python

from os.path import abspath
import pprint
import asyncio
from datetime import timedelta, datetime
import operator
import discord
import json
import pickle
import random
import re
import sys
import os
import time
import copy

# GLOBALS
MAIN_DATA = {}
IMPLEMENTED_COMMANDS = ["!help", "!mystery", "!register", "!draft", "!undraft", "!start_draft", "!all_teams", "!my_team", "!available", "!search", "!tiers", "!search_teams", "!supply", "!recommendation", "!search_mega"]

MESSAGE_BUFFER = asyncio.Queue()

# User needs to put their token here!
token = 'TOKEN HERE!'
client = discord.Client()



# CONFIGURATION
# Load the configuration file
# configFilename = 'config.json'
# print('Loading config from', abspath(configFilename))
# config = json.load(open(configFilename))
# subredditName = config['subredditName']



# SYNCHRONOUS FUNCTIONS

# FILE MANIPULATION OPERATIONS
def loadDataFile():
    fileHandler = open("data.json", 'r')
    data = json.load(fileHandler)
    global MAIN_DATA
    MAIN_DATA = data

def writeDataFile():
    global MAIN_DATA
    fileHandler = open("data.json", 'w')
    json.dump(MAIN_DATA, fileHandler, indent=4, sort_keys=True)

def attemptDataFileLoad():
    try:
        loadDataFile()
    except IOError:
        # data file doesn't exist yet, so make one
        print("No data.json file found, creating new one.")
        global MAIN_DATA
        MAIN_DATA = {
        'users': [], 
        'freePokemon': [],
        'draftStarted': False,
        'draftFinished': False,
        'draftRound': 1,
        'numberOfDraftRounds': 11,
        'draftCurrentPosition': None,
        'draftGoingForwards': True,
        'draftOrder': [],
        'timeDraftBegan': None,
        'timeOfLastDraft': None
        }

        fileHandler = open("pkmnList.txt", "r")
        for line in fileHandler:
            splitline = line.split()
            newPokemonDict = {}
            newPokemonDict["name"] = splitline[1]
            newPokemonDict["type"] = []
            if len(splitline) == 6:
                newPokemonDict["type"].append(splitline[2])
                newPokemonDict["type"].append(splitline[3])
            elif len(splitline) == 5:
                newPokemonDict["type"].append(splitline[2])
            else:
                print("ERROR: Pokemon list file is broken.")
                exit()

            newPokemonDict["tier"] = splitline[-2]
            if newPokemonDict["tier"] == "0":
                newPokemonDict["legal"] = False
            else:
                newPokemonDict["legal"] = True
            newPokemonDict["mega"] = splitline[-1]
            newPokemonDict["owner"] = None
            MAIN_DATA["freePokemon"].append(newPokemonDict)
        writeDataFile()
        loadDataFile()

# COMMAND PROCESSING OPERATIONS
def command_register(msg):
    global MAIN_DATA

    # username
    # print(str(msg.author.id))
    # print(str(msg.author.name))
    # print(str(msg.author.discriminator))

    # command
    command = str(msg.content).split(' ', 1)[0].strip()
    # print(command)

    # args
    args = " ".join(str(msg.content).split(' ', 1)[1:])
    # print(args)
    
    response = "ERROR: in command_register"

    # check if the user is already registered
    for iterUser in MAIN_DATA['users']:
        if msg.author.id == iterUser["discord_id"]:
            if iterUser["teamName"] is not None:
                response = ("ERROR: You're already registered!")
                return response

    if (len(args.split()) <= 1):
        response = """ERROR: You need to specify a team name and a 3 character abbreviation!
e.g. !register The Miami Donphans MID"""
        return response

    # Split team name and abbreviation. First 3 characters of last word is their abbreviation
    # EG: Los Angeles Lanturns LAL
    inputAbbreviation = args.split()[-1].upper()
    inputTeamName = ' '.join(args.split()[0:-1])
    if len(inputAbbreviation) > 3:
        inputAbbreviation = inputAbbreviation[0:3]
    if len(inputAbbreviation) < 3:
        response = ("ERROR: Your abbreviation should be 3 characters!")
        return response

    # Reject the user if the team name or abbreviation is already in use
    for iterUser in MAIN_DATA["users"]:
        if inputTeamName == iterUser["teamName"]:
            response = ("ERROR: That team name is already in use! Pick another one, please.")
            return response
        if inputAbbreviation == iterUser["teamAbbreviation"]:
            response = ("ERROR: That abbreviation is already in use! Pick another one, please.")
            return response

    # registration looks good, so create and store a new user dict
    newUser = {}
    
    # TODO: FIX ME. Unused entries?
    newUser["discord_id"] = str(msg.author.id)
    newUser["discord_name"] = str(msg.author.name)
    newUser["discord_discriminator"] = str(msg.author.discriminator)


    newUser["freeAgentPicks"] = 3
    newUser["teamName"] = inputTeamName
    newUser["teamAbbreviation"] = inputAbbreviation
    newUser["teamMembers"] = []
    newUser["draftList"] = []
    newUser["zCaptain"] = None
    newUser["draftedMega"] = False

    MAIN_DATA["users"].append(newUser)

    response = ("""Your team, The """ + inputTeamName + """, has been registered. Congratulations!
Welcome to the Appokelachian League. Happy battling!
        """)

    writeDataFile()

    return response


# This is the command to start the draft
def admin_command_start_draft(msg):
    global MAIN_DATA

    # command
    command = str(msg.content).split(' ', 1)[0].strip()

    # args
    args = " ".join(str(msg.content).split(' ', 1)[1:])
    
    # if the draft has already finished, this command should be rejected
    if MAIN_DATA["draftFinished"] == True:
        response = ("ERROR: The draft already finished. If you want to run a new draft, kill the bot and then delete data.json.")
        return response

    # If the draft has been started, this command will fail.
    if MAIN_DATA["draftStarted"] == True:
        response = ("ERROR: The draft has already been started.")
        return response

    # MAIN_DATA will hold information about the draft
    MAIN_DATA["draftStarted"] = True
    MAIN_DATA["timeDraftBegan"] = str(datetime.now())
    MAIN_DATA["timeOfLastDraft"] = MAIN_DATA["timeDraftBegan"] 


    # get a random ordering of users
    listOfUsers = []
    for user in MAIN_DATA["users"]:
        listOfUsers.append(user["discord_id"])

    random.shuffle(listOfUsers)
    MAIN_DATA["draftOrder"] = listOfUsers
    MAIN_DATA["draftCurrentPosition"] = 0

    #
    response = """The draft has been started at: """ + str(datetime.now()) + """. 

The draft order is:
"""

    for user_id in listOfUsers:
        for actualUser in MAIN_DATA["users"]:
            if actualUser["discord_id"] == str(user_id):
                response = response + """
""" + actualUser["discord_name"] + "#" + actualUser["discord_discriminator"]
                break

    writeDataFile()

    return response

# users draft pokemon
def command_draft(msg):
    global MAIN_DATA

    # command
    command = str(msg.content).split(' ', 1)[0].strip()
    # print(command)

    # args
    args = " ".join(str(msg.content).split(' ', 1)[1:])
    # print(args)
    
    # if the draft has already finished, this command should be rejected
    if MAIN_DATA["draftFinished"] == True:
        response = ("ERROR: The draft already finished.")
        return response

    # username lookup
    thisUser = {}
    for tempUser in MAIN_DATA["users"]:
        if tempUser["discord_id"] == str(msg.author.id):
            thisUser = tempUser

    if len( thisUser["draftList"]) >= 21:
        response = ("ERROR: Your draft list is too long. Please remove Pokemon before trying to draft more.")
        return response


    # Pokemon name changed to lowercase, whitespace and misc chars stripped
    fixed_args = args.lower()
    fixed_args = "".join(fixed_args.split())
    fixed_args = fixed_args.replace(".", "")
    fixed_args = fixed_args.replace(":", "")
    fixed_args = fixed_args.replace("'", "")


    for pokemon in MAIN_DATA["freePokemon"]:
        if( pokemon["name"].lower() == fixed_args):
            if( pokemon["owner"] is not None):
                response = pokemon["name"] + " has already been drafted by another player."
                return response
            else:
                if (pokemon["legal"] == True):
                    if (pokemon["mega"] == "1" and thisUser["draftedMega"] == True):
                        response = "You can't draft a second Mega!"
                        return response
                    for tempUser in MAIN_DATA["users"]:
                        if tempUser["discord_id"] == str(msg.author.id):
                            if pokemon["name"] not in tempUser["draftList"]:
                                tempUser["draftList"].append(pokemon["name"])
                                response = pokemon["name"] + """ has been added to your draft list, which is now as follows:
    """
                                iterator = 1
                                for name in tempUser["draftList"]:
                                    response = response + """
    """ + "**" + str(iterator) + ")** " + name
                                    iterator = iterator + 1
                                
                                writeDataFile()
                                return response
                            else:
                                response = (pokemon["name"] + " is already on your drafting list.")
                                return response
                else:
                    response = (pokemon["name"] + " is banned, and cannot be drafted.")
                    return response


    response = ("ERROR: [" + args +"] is not the name of any existing Pokemon. Please check your spelling.")
    return response

# remove a pokemon from draft list
def command_undraft(msg):
    global MAIN_DATA

    # command
    command = str(msg.content).split(' ', 1)[0].strip()
    # print(command)

    # args
    args = " ".join(str(msg.content).split(' ', 1)[1:])
    # print(args)

    # If the draft is finished, reject this command
    if MAIN_DATA["draftFinished"] == True:
        response = ("ERROR: The draft already finished.")
        return response

    # username lookup
    thisUser = {}
    for tempUser in MAIN_DATA["users"]:
        if tempUser["discord_id"] == msg.author.id:
            thisUser = tempUser

    if len( thisUser["draftList"]) == 0:
        response = ("ERROR: Your draft list is empty. You can't remove Pokemon from your draft list now.")
        return response


    # Pokemon name changed to lowercase, whitespace and misc chars stripped
    fixed_args = args.lower()
    fixed_args = "".join(fixed_args.split())
    fixed_args = fixed_args.replace(".", "")
    fixed_args = fixed_args.replace(":", "")
    fixed_args = fixed_args.replace("'", "")


    # Check to see they're deleting something that exists
    correctSpelling = False

    for pokemon in MAIN_DATA["freePokemon"]:
        if( pokemon["name"].lower() == fixed_args):
            correctSpelling = True
            break

    if not correctSpelling:
        response = ("ERROR: [" + args +"] is not the name of any existing Pokemon. Please check your spelling.")
        return response


    # They entered a correctly spelled pokemon. Let's remove it if it's on their list.
    for tempUser in MAIN_DATA["users"]:
        if tempUser["discord_id"] == msg.author.id:

            # We found the user
            for pokemonName in tempUser["draftList"]:
                if pokemonName.lower() == str(fixed_args):

                    # we found a match, so let's remove it
                    tempUser["draftList"].remove(pokemonName)

                    # If the user's list would be empty, change the message a bit.
                    if len(tempUser["draftList"]) == 0:
                        response = pokemon["name"] + """ has been removed from your draft list, which is now empty."""
                    else:
                        response = pokemon["name"] + """ has been removed from your draft list, which is now as follows:
"""
                        iterator = 1
                        for name in tempUser["draftList"]:
                            response = response + """
""" + "**" + str(iterator) + ")** " + name
                            iterator = iterator + 1
                    
                    writeDataFile()
                    return response

            response = (pokemon["name"] + " is not in your drafting list.")
            return response

    response = ("ERROR: [" + args +"] could not be removed from your list. **Please report this error!**")
    return response



# get info about teams
def command_all_teams(msg):
    global MAIN_DATA

    if MAIN_DATA["draftStarted"] is False:
        response = ("ERROR: The draft hasn't been started yet.")
        return response

    response = ""

    if MAIN_DATA["draftFinished"] is False:
        response = "Current draft round: " + str(MAIN_DATA["draftRound"]) + " / " + str(MAIN_DATA["numberOfDraftRounds"]) + """
Current draft position: """ + str(MAIN_DATA["draftCurrentPosition"] + 1) + """
"""

        if MAIN_DATA["draftGoingForwards"] is True:
            response += """The draft is moving forwards.

"""
        else:
            response += """The draft is moving backwards.

"""

    draftPosCounter = 0
    for draftPlacement in MAIN_DATA["draftOrder"]:
        for iterUser in MAIN_DATA["users"]:
            if iterUser["discord_id"] == draftPlacement:
                
                # We found a match
                draftPosCounter += 1

                response = response + iterUser["discord_name"] + " | **" + iterUser["teamName"] + "** [" + iterUser["teamAbbreviation"] + "]" + """ - Draft Position: """ + str(draftPosCounter) + """
"""
    return response


# get info about teams
def command_search_teams(msg):
    global MAIN_DATA

    if not hasattr(msg, 'content'):
        return "You need to specify a team abbreviation to search for."
    
    if msg.content is None:
        return "You need to specify a team abbreviation to search for."

    # arg
    if len(msg.content) == 17:
        abbreviation = str(msg.content).split(' ', 1)[1]
        abbreviation = abbreviation.upper()
    else:
        # print(len(msg.content))
        return "You need to specify a team abbreviation of exactly 3 characters."

    response = "ERROR: Team not found!"

    # lookup
    for iterUser in MAIN_DATA["users"]:
        if iterUser["teamAbbreviation"] == abbreviation:
            response = ""
            response = response + iterUser["discord_name"] + " | **" + iterUser["teamName"] + "** [" + iterUser["teamAbbreviation"] + "]" + """

Team Members:
"""

            teamMateCounter = 1
            for entry in iterUser["teamMembers"]:
                response = response + "**" + str(teamMateCounter) + ")** " + entry + """
"""
                teamMateCounter += 1

            response = response + """

        """

    return response



# get info about my team
def command_my_team(msg):
    global MAIN_DATA

    response = ""

    for iterUser in MAIN_DATA["users"]:
        if iterUser["discord_id"] == msg.author.id:        
            response = response + iterUser["discord_name"] + " | **" + iterUser["teamName"] + "** [" + iterUser["teamAbbreviation"] + "]" + """

Team Members: 
"""
            teamMateCounter = 1
            for entry in iterUser["teamMembers"]:
                response = response + "**" + str(teamMateCounter) + ")** " + entry + """
"""
                teamMateCounter +=1
            response = response + """
Draft List:
"""
            teamMateCounter = 1
            for entry in iterUser["draftList"]:
                response = response + "**" + str(teamMateCounter) + ")** " + entry + """
"""
                teamMateCounter +=1    
    return response


# get info about pokemon
def command_search(msg):
    global MAIN_DATA

    # args
    args = " ".join(str(msg.content).split(' ', 1)[1:])

    # Pokemon name changed to lowercase, whitespace and misc chars stripped
    fixed_args = args.lower()
    fixed_args = "".join(fixed_args.split())
    fixed_args = fixed_args.replace(".", "")
    fixed_args = fixed_args.replace(":", "")
    fixed_args = fixed_args.replace("'", "")

    if len(fixed_args) == 0:
        return "You need to specify a type to search for when using !search."

    typeToSearch = str(msg.content).split(' ', 1)[1].strip()
    typeToSearch = typeToSearch.lower()
    typeToSearch = "".join(typeToSearch.split())
    typeToSearch = typeToSearch.replace(".", "")
    typeToSearch = typeToSearch.replace(":", "")
    typeToSearch = typeToSearch.replace("'", "")
    typeToSearch = typeToSearch.capitalize()

    tempPokemonList = copy.deepcopy(MAIN_DATA["freePokemon"])
    tempPokemonList.sort(key=operator.itemgetter('tier','name'))

    response = "Pokemon with type: **" + typeToSearch + "**" + """

"""

    response = response + "*Mega*" + ":" + """
"""
    
    for pokemon in tempPokemonList:
        if (typeToSearch in pokemon["type"]) and (pokemon["tier"] != "0") and (pokemon["mega"] == "1"):
            if pokemon["owner"] is not None:
                response = response + "~~" + pokemon["name"] + "~~" + """
"""
            else:
                response = response + "**" + pokemon["name"] + "**" + """
"""        
    response += """
"""


    for specifiedTier in ["1","2","3","4","5"]:
        response = response + "*" + specifiedTier + "*" + ":" + """
"""
        
        for pokemon in tempPokemonList:
            if (typeToSearch in pokemon["type"]) and (pokemon["tier"] == specifiedTier) and (pokemon["mega"] == "0"):
                if pokemon["owner"] is not None:
                    response = response + "~~" + pokemon["name"] + "~~" + """
"""
                else:
                    response = response + "**" + pokemon["name"] + "**" + """
"""        
        response += """
"""
    return response


# get info about pokemon
def command_search_mega(msg):
    global MAIN_DATA

    tempPokemonList = copy.deepcopy(MAIN_DATA["freePokemon"])
    tempPokemonList.sort(key=operator.itemgetter('tier','name'))

    response = ""

    for specifiedTier in ["1","2","3"]:
        response = response + "*" + specifiedTier + "*" + ":" + """
"""
        
        for pokemon in tempPokemonList:
            if (pokemon["tier"] == specifiedTier) and (pokemon["mega"] == "1"):
                if pokemon["owner"] is not None:
                    response = response + "~~" + pokemon["name"] + "~~" + """
"""
                else:
                    response = response + "**" + pokemon["name"] + "**" + """
"""        
        response += """
"""
    return response

# get info about pokemon
def command_tiers(msg):
    global MAIN_DATA

    tempPokemonList = copy.deepcopy(MAIN_DATA["freePokemon"])
    tempPokemonList.sort(key=operator.itemgetter('tier','name'))

    response = "**Tiers:**"  + """

"""
    for specifiedTier in ["1","2"]:     
        for pokemon in tempPokemonList:
            if (pokemon["tier"] == specifiedTier):
                if pokemon["owner"] is not None:
                    response = response + "~~" + pokemon["name"] + "~~" + """ """
                else:
                    response = response + "**" + pokemon["name"] + "**" + """ """
        response = response + """

"""
    return (response)


# get info about pokemon
def command_available(msg):
    global MAIN_DATA

    # args
    args = " ".join(str(msg.content).split(' ', 1)[1:])

    # Pokemon name changed to lowercase, whitespace and misc chars stripped
    fixed_args = args.lower()
    fixed_args = "".join(fixed_args.split())
    fixed_args = fixed_args.replace(".", "")
    fixed_args = fixed_args.replace(":", "")
    fixed_args = fixed_args.replace("'", "")

    if len(fixed_args) == 0:
        return "You need to specify a type to search for when using !available."

    typeToSearch = str(msg.content).split(' ', 1)[1].strip()
    typeToSearch = typeToSearch.lower()
    typeToSearch = "".join(typeToSearch.split())
    typeToSearch = typeToSearch.replace(".", "")
    typeToSearch = typeToSearch.replace(":", "")
    typeToSearch = typeToSearch.replace("'", "")
    typeToSearch = typeToSearch.capitalize()

    tempPokemonList = copy.deepcopy(MAIN_DATA["freePokemon"])
    tempPokemonList.sort(key=operator.itemgetter('name'))

    response = "Pokemon with type: **" + typeToSearch + "**" + """

""" 
    specifiedTier = ["1","2","3","4","5"]
    for pokemon in tempPokemonList:
        if (typeToSearch in pokemon["type"]) and (pokemon["tier"] in specifiedTier):
            if pokemon["owner"] is not None:
                response = response + "~~" + pokemon["name"] + "~~" + """
"""
            else:
                response = response + "**" + pokemon["name"] + "**" + """
"""        
    response += """
"""
    return response






# get info about pokemon
def command_supply(msg):
    global MAIN_DATA

    tempPokemonList = copy.deepcopy(MAIN_DATA["freePokemon"])

    typeList = ["Normal", "Fighting", "Flying", "Poison", "Ground", "Rock", "Bug", "Ghost", "Steel", "Fire", "Water", "Grass", "Electric", "Psychic", "Ice", "Dragon", "Dark", "Fairy"]

    response = "**Supply of Viable Picks**:"  + """

```"""
    for thisType in typeList:
        totalSupply = 0.0
        stillAvailable = 0.0

        for pokemon in tempPokemonList:
            if thisType in pokemon["type"]:
                if pokemon["owner"] is not None:

                    if pokemon["tier"] is "1":
                        totalSupply += 4.0
                    elif pokemon["tier"] is "2":
                        totalSupply += 3.0
                    elif pokemon["tier"] is "3":
                        totalSupply += 2.25
                    elif pokemon["tier"] is "4":
                        totalSupply += 0.75
                    elif pokemon["tier"] is "5":
                        totalSupply += 0.15

                else:
                    if pokemon["tier"] is "1":
                        totalSupply += 4.0
                        stillAvailable += 4.0
                    elif pokemon["tier"] is "2":
                        totalSupply += 3.0
                        stillAvailable += 3.0
                    elif pokemon["tier"] is "3":
                        totalSupply += 2.25
                        stillAvailable += 2.25
                    elif pokemon["tier"] is "4":
                        totalSupply += 0.75
                        stillAvailable += 0.75
                    elif pokemon["tier"] is "5":
                        totalSupply += 0.15
                        stillAvailable+= 0.15

        ratio = stillAvailable / totalSupply
        totalSupply = 0.0
        stillAvailable = 0.0
        response = response + "" + thisType + ": "
        difference = 10 - len(thisType)
        for x in range(difference):
            response = response + " "

        ratio = ratio * 100

        response = response + str(int(ratio)) + "%" + """
"""

    response = response + "```"
    return (response)



# get info about pokemon
def command_recommendation(msg):
    global MAIN_DATA
    
    # username
    # print(str(msg.author.id))
    # print(str(msg.author.name))
    # print(str(msg.author.discriminator))

    # command
    command = str(msg.content).split(' ', 1)[0].strip()

    # args
    args = " ".join(str(msg.content).split(' ', 1)[1:])

    if MAIN_DATA["draftStarted"] == False:
        return "ERROR: You can't use this command until the draft has begun."

    typeList = ["Normal", "Fighting", "Flying", "Poison", "Ground", "Rock", "Bug", "Ghost", "Steel", "Fire", "Water", "Grass", "Electric", "Psychic", "Ice", "Dragon", "Dark", "Fairy"]

    typeChart = {}
    typeChart["Normal"] =       {"resistance": [], "weakness": ["Fighting"], "immunity": ["Ghost"] }    
    typeChart["Fighting"] =     {"resistance": ["Bug", "Dark", "Rock"], "weakness": ["Fairy", "Flying","Psychic"], "immunity": [] }    
    typeChart["Flying"] =       {"resistance": ["Bug", "Fighting", "Grass"], "weakness": ["Electric", "Ice", "Rock"], "immunity": ["Ground"] }    
    typeChart["Poison"] =       {"resistance": ["Fighting", "Poison", "Bug", "Grass", "Fairy"], "weakness": ["Ground", "Psychic"], "immunity": [] }    
    typeChart["Ground"] =       {"resistance": ["Poison", "Rock"], "weakness": ["Grass", "Ice", "Water"], "immunity": ["Electric"] }    
    typeChart["Rock"] =         {"resistance": ["Fire", "Flying", "Normal", "Poison"], "weakness": ["Fighting", "Grass", "Ground", "Steel", "Water"], "immunity": [] }    
    typeChart["Bug"] =          {"resistance": ["Fighting", "Grass", "Ground"], "weakness": ["Fire", "Flying", "Rock"], "immunity": [] }    
    typeChart["Ghost"] =        {"resistance": ["Bug", "Poison"], "weakness": ["Dark", "Ghost"], "immunity": ["Normal", "Fighting"] }    
    typeChart["Steel"] =        {"resistance": ["Bug", "Dragon", "Fairy", "Flying", "Grass", "Ice", "Normal", "Psychic", "Rock", "Steel"], "weakness": ["Fighting", "Fire", "Ground"], "immunity": ["Poison"] }    
    typeChart["Fire"] =         {"resistance": ["Bug", "Fire", "Grass", "Ice", "Steel"], "weakness": ["Ground","Rock","Water"], "immunity": [] }    
    typeChart["Water"] =        {"resistance": ["Fire", "Ice", "Water", "Steel"], "weakness": ["Electric", "Grass"], "immunity": [] }    
    typeChart["Grass"] =        {"resistance": ["Electric", "Grass", "Ground", "Water"], "weakness": ["Bug", "Fire", "Flying", "Ice", "Poison"], "immunity": [] }    
    typeChart["Electric"] =     {"resistance": ["Electric", "Flying", "Steel"], "weakness": ["Ground"], "immunity": [] }    
    typeChart["Psychic"] =      {"resistance": ["Fighting", "Psychic"], "weakness": ["Bug", "Dark", "Ghost"], "immunity": [] }    
    typeChart["Ice"] =          {"resistance": ["Ice"], "weakness": ["Fighting", "Fire", "Rock", "Steel"], "immunity": [] }    
    typeChart["Dragon"] =       {"resistance": ["Fire", "Water", "Grass", "Electric"], "weakness": ["Dragon", "Fairy", "Ice"], "immunity": [] }    
    typeChart["Dark"] =         {"resistance": ["Dark", "Ghost"], "weakness": ["Bug", "Fairy", "Fighting"], "immunity": ["Psychic"] }    
    typeChart["Fairy"] =        {"resistance": ["Bug", "Dark", "Fighting"], "weakness": ["Poison", "Steel"], "immunity": ["Dragon"] }

    tempPokemonList = copy.deepcopy(MAIN_DATA["freePokemon"])
    
    # summary of the draft thus far
    supplyOfEachType = {}
    supplyOfEachType["Normal"] = 0
    supplyOfEachType["Fighting"] = 0
    supplyOfEachType["Flying"] = 0
    supplyOfEachType["Poison"] = 0
    supplyOfEachType["Ground"] = 0
    supplyOfEachType["Rock"] = 0
    supplyOfEachType["Bug"] = 0
    supplyOfEachType["Ghost"] = 0
    supplyOfEachType["Steel"] = 0
    supplyOfEachType["Fire"] = 0
    supplyOfEachType["Water"] = 0
    supplyOfEachType["Grass"] = 0
    supplyOfEachType["Electric"] = 0
    supplyOfEachType["Psychic"] = 0
    supplyOfEachType["Ice"] = 0
    supplyOfEachType["Dragon"] = 0
    supplyOfEachType["Dark"] = 0
    supplyOfEachType["Fairy"] = 0

    for thisType in typeList:
        totalSupply = 0.0
        stillAvailable = 0.0

        for pokemon in tempPokemonList:
            if thisType in pokemon["type"]:
                if pokemon["owner"] is not None:

                    if pokemon["tier"] is "1":
                        totalSupply += 4.0
                    elif pokemon["tier"] is "2":
                        totalSupply += 3.0
                    elif pokemon["tier"] is "3":
                        totalSupply += 2.25
                    elif pokemon["tier"] is "4":
                        totalSupply += 0.75
                    elif pokemon["tier"] is "5":
                        totalSupply += 0.15

                else:
                    if pokemon["tier"] is "1":
                        totalSupply += 4.0
                        stillAvailable += 4.0
                    elif pokemon["tier"] is "2":
                        totalSupply += 3.0
                        stillAvailable += 3.0
                    elif pokemon["tier"] is "3":
                        totalSupply += 2.25
                        stillAvailable += 2.25
                    elif pokemon["tier"] is "4":
                        totalSupply += 0.75
                        stillAvailable += 0.75
                    elif pokemon["tier"] is "5":
                        totalSupply += 0.15
                        stillAvailable+= 0.15

        ratio = stillAvailable / totalSupply
        totalSupply = 0.0
        stillAvailable = 0.0
        ratio = ratio * 100
        supplyOfEachType[thisType] = ratio


    for tempUser in MAIN_DATA["users"]:
        if msg.author.id == tempUser["discord_id"]:
            # we have a match!

            # team summary stats
            numberOfEachType = {}
            numberOfEachType["Normal"] = 0
            numberOfEachType["Fighting"] = 0
            numberOfEachType["Flying"] = 0
            numberOfEachType["Poison"] = 0
            numberOfEachType["Ground"] = 0
            numberOfEachType["Rock"] = 0
            numberOfEachType["Bug"] = 0
            numberOfEachType["Ghost"] = 0
            numberOfEachType["Steel"] = 0
            numberOfEachType["Fire"] = 0
            numberOfEachType["Water"] = 0
            numberOfEachType["Grass"] = 0
            numberOfEachType["Electric"] = 0
            numberOfEachType["Psychic"] = 0
            numberOfEachType["Ice"] = 0
            numberOfEachType["Dragon"] = 0
            numberOfEachType["Dark"] = 0
            numberOfEachType["Fairy"] = 0

            teamResistanceScores = {}
            teamResistanceScores["Normal"] = 0.0
            teamResistanceScores["Fighting"] = 0.0
            teamResistanceScores["Flying"] = 0.0
            teamResistanceScores["Poison"] = 0.0
            teamResistanceScores["Ground"] = 0.0
            teamResistanceScores["Rock"] = 0.0
            teamResistanceScores["Bug"] = 0.0
            teamResistanceScores["Ghost"] = 0.0
            teamResistanceScores["Steel"] = 0.0
            teamResistanceScores["Fire"] = 0.0
            teamResistanceScores["Water"] = 0.0
            teamResistanceScores["Grass"] = 0.0
            teamResistanceScores["Electric"] = 0.0
            teamResistanceScores["Psychic"] = 0.0
            teamResistanceScores["Ice"] = 0.0
            teamResistanceScores["Dragon"] = 0.0
            teamResistanceScores["Dark"] = 0.0
            teamResistanceScores["Fairy"] = 0.0

            sunTeam = False
            rainTeam = False
            sandTeam = False

            # get an overview of the team based on its members thus far
            indexOfType = 0
            for ownedPokemon in tempUser["teamMembers"]:
                for actualPokemon in tempPokemonList:
                    if ownedPokemon == actualPokemon["name"]:
                        # we have a match

                        for eachType in actualPokemon["type"]:
                            numberOfEachType[eachType] += 1

                        # check to see if it's a weather team
                        if actualPokemon["name"] in ["Torkoal", "Ninetails"]:
                            sunTeam = True
                        if actualPokemon["name"] in ["Pelipper", "Politoed"]:
                            rainTeam = True
                        if actualPokemon["name"] in ["Tyranitar", "Hippowdon", "Gigalith"]:
                            sandTeam = True

                        # alter this team's scores based on this pokemon's typing
                        thisPokemonWeaknesses = {}
                        thisPokemonWeaknesses["Normal"] = 1.0
                        thisPokemonWeaknesses["Fighting"] = 1.0
                        thisPokemonWeaknesses["Flying"] = 1.0
                        thisPokemonWeaknesses["Poison"] = 1.0
                        thisPokemonWeaknesses["Ground"] = 1.0
                        thisPokemonWeaknesses["Rock"] = 1.0
                        thisPokemonWeaknesses["Bug"] = 1.0
                        thisPokemonWeaknesses["Ghost"] = 1.0
                        thisPokemonWeaknesses["Steel"] = 1.0
                        thisPokemonWeaknesses["Fire"] = 1.0
                        thisPokemonWeaknesses["Water"] = 1.0
                        thisPokemonWeaknesses["Grass"] = 1.0
                        thisPokemonWeaknesses["Electric"] = 1.0
                        thisPokemonWeaknesses["Psychic"] = 1.0
                        thisPokemonWeaknesses["Ice"] = 1.0
                        thisPokemonWeaknesses["Dragon"] = 1.0
                        thisPokemonWeaknesses["Dark"] = 1.0
                        thisPokemonWeaknesses["Fairy"] = 1.0

                        # for each of this pokemon's two types
                        for eachType in actualPokemon["type"]:

                            for resistance in typeChart[eachType]["resistance"]:
                                thisPokemonWeaknesses[resistance] *= 0.5

                            for weakness in typeChart[eachType]["weakness"]:
                                thisPokemonWeaknesses[weakness] *= 2.0

                            for immunity in typeChart[eachType]["immunity"]:
                                thisPokemonWeaknesses[immunity] *= 0.0

                        for eachType in typeList:
                            if thisPokemonWeaknesses[eachType] == 1.0:
                                pass
                            elif thisPokemonWeaknesses[eachType] == 2.0:
                                teamResistanceScores[eachType] -= 1.0
                            elif thisPokemonWeaknesses[eachType] == 4.0:
                                teamResistanceScores[eachType] -= 2.0
                            elif thisPokemonWeaknesses[eachType] == 0.5:
                                teamResistanceScores[eachType] += 1.0
                            elif thisPokemonWeaknesses[eachType] == 0.25:
                                teamResistanceScores[eachType] += 2.0
                            elif thisPokemonWeaknesses[eachType] == 0.0:
                                teamResistanceScores[eachType] += 2.5


            # declare an overall team resistance score based on number of exploitable weaknesses
            currentOverallTeamResistanceScore = 0.0

            if teamResistanceScores["Normal"] >= 0.0:
                pass
                currentOverallTeamResistanceScore += (teamResistanceScores["Normal"] / 3.0)
            else:
                currentOverallTeamResistanceScore += teamResistanceScores["Normal"]
            if teamResistanceScores["Fighting"] >= 0.0:
                pass
                currentOverallTeamResistanceScore += (teamResistanceScores["Fighting"] / 3.0)
            else:
                currentOverallTeamResistanceScore += teamResistanceScores["Fighting"]
            if teamResistanceScores["Flying"] >= 0.0:
                pass
                currentOverallTeamResistanceScore += (teamResistanceScores["Flying"] / 3.0)
            else:
                currentOverallTeamResistanceScore += teamResistanceScores["Flying"]
            if teamResistanceScores["Poison"] >= 0.0:
                pass
                currentOverallTeamResistanceScore += (teamResistanceScores["Poison"] / 3.0)
            else:
                currentOverallTeamResistanceScore += teamResistanceScores["Poison"]
            if teamResistanceScores["Ground"] >= 0.0:
                pass
                currentOverallTeamResistanceScore += (teamResistanceScores["Ground"] / 3.0)
            else:
                currentOverallTeamResistanceScore += teamResistanceScores["Ground"]
            if teamResistanceScores["Rock"] >= 0.0:
                pass
                currentOverallTeamResistanceScore += (teamResistanceScores["Rock"] / 3.0)
            else:
                currentOverallTeamResistanceScore += teamResistanceScores["Rock"]
            if teamResistanceScores["Bug"] >= 0.0:
                pass
                currentOverallTeamResistanceScore += (teamResistanceScores["Bug"] / 3.0)
            else:
                currentOverallTeamResistanceScore += teamResistanceScores["Bug"]
            if teamResistanceScores["Ghost"] >= 0.0:
                pass
                currentOverallTeamResistanceScore += (teamResistanceScores["Ghost"] / 3.0)
            else:
                currentOverallTeamResistanceScore += teamResistanceScores["Ghost"]
            if teamResistanceScores["Steel"] >= 0.0:
                pass
                currentOverallTeamResistanceScore += (teamResistanceScores["Steel"] / 3.0)
            else:
                currentOverallTeamResistanceScore += teamResistanceScores["Steel"]
            if teamResistanceScores["Fire"] >= 0.0:
                pass
                currentOverallTeamResistanceScore += (teamResistanceScores["Fire"] / 3.0)
            else:
                currentOverallTeamResistanceScore += teamResistanceScores["Fire"]
            if teamResistanceScores["Water"] >= 0.0:
                pass
                currentOverallTeamResistanceScore += (teamResistanceScores["Water"] / 3.0)
            else:
                currentOverallTeamResistanceScore += teamResistanceScores["Water"]
            if teamResistanceScores["Grass"] >= 0.0:
                pass
                currentOverallTeamResistanceScore += (teamResistanceScores["Grass"] / 3.0)
            else:
                currentOverallTeamResistanceScore += teamResistanceScores["Grass"]
            if teamResistanceScores["Electric"] >= 0.0:
                pass
                currentOverallTeamResistanceScore += (teamResistanceScores["Electric"] / 3.0)
            else:
                currentOverallTeamResistanceScore += teamResistanceScores["Electric"]
            if teamResistanceScores["Psychic"] >= 0.0:
                pass
                currentOverallTeamResistanceScore += (teamResistanceScores["Psychic"] / 3.0)
            else:
                currentOverallTeamResistanceScore += teamResistanceScores["Psychic"]
            if teamResistanceScores["Ice"] >= 0.0:
                pass
                currentOverallTeamResistanceScore += (teamResistanceScores["Ice"] / 3.0)
            else:
                currentOverallTeamResistanceScore += teamResistanceScores["Ice"]
            if teamResistanceScores["Dragon"] >= 0.0:
                pass
                currentOverallTeamResistanceScore += (teamResistanceScores["Dragon"] / 3.0)
            else:
                currentOverallTeamResistanceScore += teamResistanceScores["Dragon"]
            if teamResistanceScores["Dark"] >= 0.0:
                pass
                currentOverallTeamResistanceScore += (teamResistanceScores["Dark"] / 3.0)
            else:
                currentOverallTeamResistanceScore += teamResistanceScores["Dark"]
            if teamResistanceScores["Fairy"] >= 0.0:
                pass
                currentOverallTeamResistanceScore += (teamResistanceScores["Fairy"] / 3.0)
            else:
                currentOverallTeamResistanceScore += teamResistanceScores["Fairy"]

            # print("CURRENT SCORE:  " + str(currentOverallTeamResistanceScore))


            # filter out already drafted mons
            for pokemon in tempPokemonList:
                if (pokemon["owner"] is not None):
                    # print("removing " + str(pokemon["name"]))
                    tempPokemonList.remove(pokemon)

            # build list of recommendations
            listOfRecommendations = []
            for pokemon in tempPokemonList:                

                pokemon["score"] = 0.0
                
                if pokemon["tier"] == "1":
                    pokemon["score"] += 4.0
                elif pokemon["tier"] == "2":
                    pokemon["score"] += 3.0
                elif pokemon["tier"] == "3":
                    pokemon["score"] += 2.25
                else:
                    continue

                sandTypeFlag = False
                dualType = False
                if len(pokemon["type"]) == 2:
                    dualType = True


                # Reward unique type additions to give more offensive threat
                for eachType in pokemon["type"]:
                    if numberOfEachType[eachType] == 0:
                        if dualType is True:
                            pokemon["score"] += 0.25
                        else:
                            pokemon["score"] += 0.5                        
                    elif numberOfEachType[eachType] == 1:
                        if dualType is True:
                            pokemon["score"] -= 0.25
                        else:
                            pokemon["score"] -= 0.5
                    elif numberOfEachType[eachType] == 2:
                        if dualType is True:
                            pokemon["score"] -= 0.5
                        else:
                            pokemon["score"] -= 1.0    
                    else:
                        if dualType is True:
                            pokemon["score"] -= 1.0
                        else:
                            pokemon["score"] -= 2.0


                    # Reward completion of FWG and Fantasy cores
                    if eachType == "Fire" and numberOfEachType["Fire"] == 0 and numberOfEachType["Water"] >= 1 and numberOfEachType["Grass"] >= 1:
                        pokemon["score"] += 0.75
                    if eachType == "Water" and numberOfEachType["Water"] == 0 and numberOfEachType["Grass"] >= 1 and numberOfEachType["Fire"] >= 1:
                        pokemon["score"] += 0.75
                    if eachType == "Grass" and numberOfEachType["Grass"] == 0 and numberOfEachType["Fire"] >= 1 and numberOfEachType["Water"] >= 1:
                        pokemon["score"] += 0.75

                    if eachType == "Steel" and numberOfEachType["Steel"] == 0 and numberOfEachType["Dragon"] >= 1 and numberOfEachType["Fairy"] >= 1:
                        pokemon["score"] += 0.75
                    if eachType == "Dragon" and numberOfEachType["Dragon"] == 0 and numberOfEachType["Fairy"] >= 1 and numberOfEachType["Steel"] >= 1:
                        pokemon["score"] += 0.75
                    if eachType == "Fairy" and numberOfEachType["Fairy"] == 0 and numberOfEachType["Steel"] >= 1 and numberOfEachType["Dragon"] >= 1:
                        pokemon["score"] += 0.75


                    # Reward bonuses for weather
                    if eachType in ["Ground", "Fire", "Rock"] and sunTeam is True:
                        pokemon["score"] += 0.5

                    if eachType in ["Ground", "Fire", "Rock"] and rainTeam is True:
                        pokemon["score"] -= 0.25

                    if eachType in ["Water", "Bug", "Grass", "Steel", "Ice"] and rainTeam is True:
                        pokemon["score"] += 0.5

                    if eachType in ["Water", "Bug", "Grass", "Steel", "Ice"] and sunTeam is True:
                        pokemon["score"] -= 0.25

                    if eachType in ["Ground", "Rock", "Steel"]:
                        sandTypeFlag = True

                    # Reward points based on how in demand this type is, up to 1.25 points.
                    thisTypeSupply = supplyOfEachType[eachType]                    
                    thisTypeDemand = (100.0 - thisTypeSupply) * .0125

                    if dualType:
                        pokemon["score"] += (thisTypeDemand / 2.0)
                    else:
                        pokemon["score"] += (thisTypeDemand)


                if sandTypeFlag is True and sandTeam is True:
                    pokemon["score"] += 0.5


                if MAIN_DATA["draftRound"] >= 2:


                    # Check to see whether this Pokemon can patch holes in your defenses
                    
                    # representation of team with the mon added
                    modifiedResistanceScores = copy.deepcopy(teamResistanceScores)

                    # alter this team's scores based on this pokemon's typing
                    thisPokemonWeaknesses = {}
                    thisPokemonWeaknesses["Normal"] = 1.0
                    thisPokemonWeaknesses["Fighting"] = 1.0
                    thisPokemonWeaknesses["Flying"] = 1.0
                    thisPokemonWeaknesses["Poison"] = 1.0
                    thisPokemonWeaknesses["Ground"] = 1.0
                    thisPokemonWeaknesses["Rock"] = 1.0
                    thisPokemonWeaknesses["Bug"] = 1.0
                    thisPokemonWeaknesses["Ghost"] = 1.0
                    thisPokemonWeaknesses["Steel"] = 1.0
                    thisPokemonWeaknesses["Fire"] = 1.0
                    thisPokemonWeaknesses["Water"] = 1.0
                    thisPokemonWeaknesses["Grass"] = 1.0
                    thisPokemonWeaknesses["Electric"] = 1.0
                    thisPokemonWeaknesses["Psychic"] = 1.0
                    thisPokemonWeaknesses["Ice"] = 1.0
                    thisPokemonWeaknesses["Dragon"] = 1.0
                    thisPokemonWeaknesses["Dark"] = 1.0
                    thisPokemonWeaknesses["Fairy"] = 1.0

                    # for each of this pokemon's two types
                    for eachType in pokemon["type"]:

                        for resistance in typeChart[eachType]["resistance"]:
                            thisPokemonWeaknesses[resistance] *= 0.5

                        for weakness in typeChart[eachType]["weakness"]:
                            thisPokemonWeaknesses[weakness] *= 2.0

                        for immunity in typeChart[eachType]["immunity"]:
                            thisPokemonWeaknesses[immunity] *= 0.0

                    for eachType in typeList:
                        if thisPokemonWeaknesses[eachType] == 1.0:
                            pass
                        elif thisPokemonWeaknesses[eachType] == 2.0:
                            modifiedResistanceScores[eachType] -= 1.0
                        elif thisPokemonWeaknesses[eachType] == 4.0:
                            modifiedResistanceScores[eachType] -= 2.0
                        elif thisPokemonWeaknesses[eachType] == 0.5:
                            modifiedResistanceScores[eachType] += 1.0
                        elif thisPokemonWeaknesses[eachType] == 0.25:
                            modifiedResistanceScores[eachType] += 2.0
                        elif thisPokemonWeaknesses[eachType] == 0.0:
                            modifiedResistanceScores[eachType] += 2.5


                    # tally values of overall resistance after this mon is added...

                    # currentOverallTeamResistanceScore
                    newOverallTeamResistanceScore = 0.0

                    if modifiedResistanceScores["Normal"] >= 0.0:
                        pass
                        newOverallTeamResistanceScore += (modifiedResistanceScores["Normal"] / 3.0)
                    else:
                        newOverallTeamResistanceScore += modifiedResistanceScores["Normal"]
                    if modifiedResistanceScores["Fighting"] >= 0.0:
                        pass
                        newOverallTeamResistanceScore += (modifiedResistanceScores["Fighting"] / 3.0)
                    else:
                        newOverallTeamResistanceScore += modifiedResistanceScores["Fighting"]
                    if modifiedResistanceScores["Flying"] >= 0.0:
                        pass
                        newOverallTeamResistanceScore += (modifiedResistanceScores["Flying"] / 3.0)
                    else:
                        newOverallTeamResistanceScore += modifiedResistanceScores["Flying"]
                    if modifiedResistanceScores["Poison"] >= 0.0:
                        pass
                        newOverallTeamResistanceScore += (modifiedResistanceScores["Poison"] / 3.0)
                    else:
                        newOverallTeamResistanceScore += modifiedResistanceScores["Poison"]
                    if modifiedResistanceScores["Ground"] >= 0.0:
                        pass
                        newOverallTeamResistanceScore += (modifiedResistanceScores["Ground"] / 3.0)
                    else:
                        newOverallTeamResistanceScore += modifiedResistanceScores["Ground"]
                    if modifiedResistanceScores["Rock"] >= 0.0:
                        pass
                        newOverallTeamResistanceScore += (modifiedResistanceScores["Rock"] / 3.0)
                    else:
                        newOverallTeamResistanceScore += modifiedResistanceScores["Rock"]
                    if modifiedResistanceScores["Bug"] >= 0.0:
                        pass
                        newOverallTeamResistanceScore += (modifiedResistanceScores["Bug"] / 3.0)
                    else:
                        newOverallTeamResistanceScore += modifiedResistanceScores["Bug"]
                    if modifiedResistanceScores["Ghost"] >= 0.0:
                        pass
                        newOverallTeamResistanceScore += (modifiedResistanceScores["Ghost"] / 3.0)
                    else:
                        newOverallTeamResistanceScore += modifiedResistanceScores["Ghost"]
                    if modifiedResistanceScores["Steel"] >= 0.0:
                        pass
                        newOverallTeamResistanceScore += (modifiedResistanceScores["Steel"] / 3.0)
                    else:
                        newOverallTeamResistanceScore += modifiedResistanceScores["Steel"]
                    if modifiedResistanceScores["Fire"] >= 0.0:
                        pass
                        newOverallTeamResistanceScore += (modifiedResistanceScores["Fire"] / 3.0)
                    else:
                        newOverallTeamResistanceScore += modifiedResistanceScores["Fire"]
                    if modifiedResistanceScores["Water"] >= 0.0:
                        pass
                        newOverallTeamResistanceScore += (modifiedResistanceScores["Water"] / 3.0)
                    else:
                        newOverallTeamResistanceScore += modifiedResistanceScores["Water"]
                    if modifiedResistanceScores["Grass"] >= 0.0:
                        pass
                        newOverallTeamResistanceScore += (modifiedResistanceScores["Grass"] / 3.0)
                    else:
                        newOverallTeamResistanceScore += modifiedResistanceScores["Grass"]
                    if modifiedResistanceScores["Electric"] >= 0.0:
                        pass
                        newOverallTeamResistanceScore += (modifiedResistanceScores["Electric"] / 3.0)
                    else:
                        newOverallTeamResistanceScore += modifiedResistanceScores["Electric"]
                    if modifiedResistanceScores["Psychic"] >= 0.0:
                        pass
                        newOverallTeamResistanceScore += (modifiedResistanceScores["Psychic"] / 3.0)
                    else:
                        newOverallTeamResistanceScore += modifiedResistanceScores["Psychic"]
                    if modifiedResistanceScores["Ice"] >= 0.0:
                        pass
                        newOverallTeamResistanceScore += (modifiedResistanceScores["Ice"] / 3.0)
                    else:
                        newOverallTeamResistanceScore += modifiedResistanceScores["Ice"]
                    if modifiedResistanceScores["Dragon"] >= 0.0:
                        pass
                        newOverallTeamResistanceScore += (modifiedResistanceScores["Dragon"] / 3.0)
                    else:
                        newOverallTeamResistanceScore += modifiedResistanceScores["Dragon"]
                    if modifiedResistanceScores["Dark"] >= 0.0:
                        pass
                        newOverallTeamResistanceScore += (modifiedResistanceScores["Dark"] / 3.0)
                    else:
                        newOverallTeamResistanceScore += modifiedResistanceScores["Dark"]
                    if modifiedResistanceScores["Fairy"] >= 0.0:
                        pass
                        newOverallTeamResistanceScore += (modifiedResistanceScores["Fairy"] / 3.0)
                    else:
                        newOverallTeamResistanceScore += modifiedResistanceScores["Fairy"]

                    positiveDifference = newOverallTeamResistanceScore - currentOverallTeamResistanceScore

                    pokemon["score"] += (positiveDifference / 8.0)

                if pokemon["score"] >= 2.0:
                    listOfRecommendations.append(pokemon)


            listOfRecommendations.sort(key=operator.itemgetter('score'), reverse=True)

            response = "Recommendations:" + """
```"""
            maximumRange = min(20, len(listOfRecommendations))
            for x in range(maximumRange):
                difference = 24 - len(listOfRecommendations[x]["name"])

                response = response + listOfRecommendations[x]["name"]

                for z in range(difference):
                    response = response + " " 
                response = response + str(int(listOfRecommendations[x]["score"]*10.0)) + "  "
                for eachType in listOfRecommendations[x]["type"]:
                    response = response + eachType + "  "
                response = response + """
"""        

            response += "```"
            return response



def draft_iterator():
    global MAIN_DATA

    draftOccuredFlag = False

    responseList = []

    # get the id of the current drafter
    currentDrafterID = MAIN_DATA["draftOrder"][MAIN_DATA["draftCurrentPosition"]]

    # print("currentDrafterID: " + str(currentDrafterID))

    snipedPokemon = "ERROR-POKEMON"
    sniper = "ERROR-PLAYER"

    for iterUser in MAIN_DATA["users"]:
        if str(currentDrafterID) == str(iterUser["discord_id"]):
            # we found a match

            # their list is populated
            if len(iterUser["draftList"]) >= 1:

                # start by cleaning up their list, removing pokemon from them that other people have drafted
                for pokemonDraftName in iterUser["draftList"]:
                    for pokemonActual in MAIN_DATA["freePokemon"]:
                        if str(pokemonDraftName) == str(pokemonActual["name"]):

                            if pokemonActual["owner"] != None:
                                iterUser["draftList"].remove(str(pokemonDraftName))
                                writeDataFile()
                                print("ERROR: removed a draft entry at an odd time...")

                            if (pokemonActual["mega"] == "1" and iterUser["draftedMega"] == True):
                                print(iterUser["draftList"])                            
                                iterUser["draftList"].remove(str(pokemonDraftName))
                                writeDataFile()



            # if it's still populated even after being cleaned, we attempt to draft their top entry
            if len(iterUser["draftList"]) >= 1:
                
                for pokemonActual in MAIN_DATA["freePokemon"]:
                    if iterUser["draftList"][0] == pokemonActual["name"]:
                        if pokemonActual["owner"] is None:

                            # this shouldn't occur in regular execution
                            if (pokemonActual["mega"] == "1" and iterUser["draftedMega"] == True):
                                print("ERROR: Can't draft Mega for user that already has a Mega!")
                                iterUser["draftList"].remove(iterUser["draftList"][0])
                                return

                            if (pokemonActual["mega"] == "1"):
                                iterUser["draftedMega"] = True

                            # This is their first pick, so draft it now
                            
                            # update draft list
                            iterUser["draftList"].remove(iterUser["draftList"][0])
                            
                            # update owner and team members
                            iterUser["teamMembers"].append( pokemonActual["name"] )
                            pokemonActual["owner"] = str(currentDrafterID)

                            snipedPokemon = pokemonActual["name"]
                            sniper = iterUser["discord_name"]
                            draftOccuredFlag = True

                            responseDict = {}
                            responseDict["id"] = str(currentDrafterID)
                            responseDict["responseBody"] = "Congrats! You have successfully drafted " + pokemonActual["name"] + " onto your team for round " + str(MAIN_DATA["draftRound"]) + " of the draft."
                            responseList.append(responseDict)
                            writeDataFile()
                            break
            break


    # snipe warnings
    if draftOccuredFlag == True:
        for iterUser in MAIN_DATA["users"]:
            if str(currentDrafterID) != str(iterUser["discord_id"]):
                # we found a not match

                # their list is populated
                if len(iterUser["draftList"]) >= 1:

                    # start by cleaning up their list, removing pokemon from them that other people have drafted
                    for pokemonDraftName in iterUser["draftList"]:
                        if pokemonDraftName == snipedPokemon:
                            iterUser["draftList"].remove(pokemonDraftName)
                            
                            responseDict = {}
                            responseDict["id"] = str(iterUser["discord_id"])
                            responseDict["responseBody"] = "Uh-oh, you've been sniped! " + snipedPokemon + " was just drafted by " + sniper + ". You may want to reconsider your current draft list."
                            responseList.append(responseDict)
                            # print("removed a draft entry due to a snipe")
        writeDataFile()


    if draftOccuredFlag == False:
        # check to see if the user has run out of time to do their draft
        elapsedTime = datetime.now() - datetime.strptime( MAIN_DATA["timeOfLastDraft"], "%Y-%m-%d %H:%M:%S.%f" )
        if (elapsedTime > timedelta(hours = 24)):
            print("User has not drafted within the allotted time limit!")

            randomPokemonSelectedFlag = False
            while randomPokemonSelectedFlag is False:
                randomPick = random.randint(0, len(MAIN_DATA["freePokemon"])-1 )

                # If pick is legal and passable, select it
                if (MAIN_DATA["freePokemon"][randomPick]["owner"] is None) and (int(MAIN_DATA["freePokemon"][randomPick]["tier"]) <= 5) and (int(MAIN_DATA["freePokemon"][randomPick]["tier"]) >= 4):
                    randomPokemonSelectedFlag = True


            # update owner and team members
            MAIN_DATA["freePokemon"][randomPick]["owner"] = str(currentDrafterID)

            findUser = False
            for iterUser in MAIN_DATA["users"]:
                # print(currentDrafterID)
                # print(str(iterUser["discord_id"]))
                # print()


                if str(currentDrafterID) == str(iterUser["discord_id"]):
                    iterUser["teamMembers"].append( MAIN_DATA["freePokemon"][randomPick]["name"] )
                    findUser = True
                    break

            if findUser == False:
                print ("ERROR! Couldn't find user in timeout function!")
                exit()

            responseDict = {}
            responseDict["id"] = str(currentDrafterID)
            responseDict["responseBody"] = "You waited too long to draft... " + MAIN_DATA["freePokemon"][randomPick]["name"] + " has been randomly assigned to your team."
            responseList.append(responseDict)

            draftOccuredFlag = True


    if draftOccuredFlag == True:

        # draft moving forward, not on last pick
        if MAIN_DATA["draftGoingForwards"] and (int(MAIN_DATA["draftCurrentPosition"]) < len(MAIN_DATA["draftOrder"]) - 1):
            MAIN_DATA["draftCurrentPosition"] = MAIN_DATA["draftCurrentPosition"] + 1

        # draft moving forward, is on last pick
        elif MAIN_DATA["draftGoingForwards"] and (int(MAIN_DATA["draftCurrentPosition"]) == len(MAIN_DATA["draftOrder"]) - 1):
            MAIN_DATA["draftGoingForwards"] = False
            MAIN_DATA["draftRound"] = MAIN_DATA["draftRound"] + 1

        # draft moving backwards, not on first pick
        elif (not MAIN_DATA["draftGoingForwards"]) and (int(MAIN_DATA["draftCurrentPosition"]) != 0 ):
            MAIN_DATA["draftCurrentPosition"] = MAIN_DATA["draftCurrentPosition"] - 1

        # draft moving backwards, is on first pick
        elif (not MAIN_DATA["draftGoingForwards"]) and (int(MAIN_DATA["draftCurrentPosition"]) == 0 ):
            MAIN_DATA["draftGoingForwards"] = True
            MAIN_DATA["draftRound"] = MAIN_DATA["draftRound"] + 1

        else:
            print("ERROR WITH DRAFT ADVANCEMENT!!!")
            exit()

        print("The draft was advanced to the next round!")

        # Send alert to next drafter
        newDrafterID = MAIN_DATA["draftOrder"][MAIN_DATA["draftCurrentPosition"]]

        if (int(MAIN_DATA["draftRound"]) <= int(MAIN_DATA["numberOfDraftRounds"])):
            responseDict = {}
            responseDict["id"] = str(newDrafterID)
            responseDict["responseBody"] = "It's your turn to draft for round " + str(MAIN_DATA["draftRound"]) + " of " + str(MAIN_DATA["numberOfDraftRounds"]) +  ". You have 24 hours. Use !draft to do so."
            responseList.append(responseDict)

        # update time of this draft occuring
        MAIN_DATA["timeOfLastDraft"] = str(datetime.now())

        # check to see if draft is over
        if (MAIN_DATA["draftRound"] > MAIN_DATA["numberOfDraftRounds"]):
            print("THE DRAFT IS COMPLETE!")
            MAIN_DATA["draftFinished"] = True

        writeDataFile()


    return responseList




# authorize a message, ensuring user has privilege to submit it and that it is valid
def authorizeMessage(msg):
    global client
    global IMPLEMENTED_COMMANDS

    # username
    # print(str(msg.author.id))
    # print(str(msg.author.name))
    # print(str(msg.author.discriminator))

    # command
    command = str(msg.content).split(' ', 1)[0].strip()
    # print(command)

    # args
    args = " ".join(str(msg.content).split(' ', 1)[1:])
    # print(args)

    # Start filling in a response
    response = "ERROR: No response formed. **Please report this error!**"

    # TODO: Do I still need Whitelisting?
    # # reject users who have not been whitelisted
    # whitelistedUsers = open("whitelist.txt").read().splitlines()
    # if username not in whitelistedUsers:
    #     print("User: " + username + "is not whitelisted. Command rejected!")
    #     response = (
    #         """You aren't whitelisted. You must be whitelisted to use this service.
    #         If you believe this to be in error, please send a message to the admin
    #         requesting to have this issue resolved.""")
    #     return response
    # else:
    #     print("Processing command for: " + username)



    # ensure user submitted a valid command
    # if not, reject this command
    if command not in IMPLEMENTED_COMMANDS:
        print(str(msg.author.name) + " gave invalid command: " + command)
        response = "Your command: [" + command + "] was invalid. Please try [!help] for a list of commands."
        return response

    # User asks for help help
    if command == "!help":
        response = """Valid Commands:

**!help**: Display this page.

**!register**: Use to register your team for the draft. Specify a name followed by a 3 character abbreviation.
e.g. !register Miami Heatran MIH

**!draft**: Use to add a Pokemon to your draft list so it will be drafted whenever it's your turn.
e.g. !draft Charizard

**!undraft**:   Use to remove a Pokemon from your draft list so that you won't draft it.
e.g. !undraft Garbodor

**!my_team**: Use to see your team, and your current draft list.

**!all_teams**: Use to see everyone's teams, and their pick order in the draft. This will also show the player whose turn it is to draft next.

**!search_teams**: Use to search for a specific team's information, including their roster.
e.g. !search_teams ABC

**!available**: Use to see which viable Pokemon of a specific type are still available. Sorted alphabetically. Doesn't display useless Pokemon.
e.g. !available Normal

**!search**: Use to see which viable Pokemon of a specific type are still available. Sorted by approximate popularity. Doesn't display useless Pokemon.
e.g. !search Normal

**!search_mega**: Use to see which Mega-Pokemon are still available.
e.g. !search_mega

**!mystery**: ???
"""

        return response


    # if they're using a command besides register and they're not registered yet, reject their command
    # registration is denoted by having a team in their MAIN_DATA['users']['teamName']
    global MAIN_DATA

    userExistsFlag = False
    for iterUser in MAIN_DATA['users']:
        if str(msg.author.id) == iterUser["discord_id"]:
            userExistsFlag = True
            break

    if (command != "!register") and (userExistsFlag == False):
        response = "You must register a team before using other commands! Use the [!register] command."
        return response

    # # HANDLE VALID COMMANDS:

    if command == "!mystery":
        response = """https://www.youtube.com/watch?v=dQw4w9WgXcQ"""
        return response

    if command == "!register":
        response = command_register(msg)
        return response

    if command == "!draft":
        response = command_draft(msg)
        return response

    if command == "!undraft":
        response = command_undraft(msg)
        return response

    if command == "!all_teams":
        response = command_all_teams(msg)
        return response

    if command == "!my_team":
        response = command_my_team(msg)
        return response

    if command == "!search_teams":
        response = command_search_teams(msg)
        return response

    if command == "!available":
        response = command_available(msg)
        return response

    if command == "!search":
        response = command_search(msg)
        return response

    if command == "!search_mega":
        response = command_search_mega(msg)
        return response

    if command == "!tiers":
        response = command_tiers(msg)
        return response

    if command == "!supply":
        response = command_supply(msg)
        return response

    if command == "!recommendation":
        response = command_recommendation(msg)
        return response



    # reject users who are not administrators
    adminUsers = open("adminlist.txt").read().splitlines()
    if str(msg.author.id) not in adminUsers:
        print("User: " + msg.author.name + "is not an admin. Command rejected!")
        response = ("""ERROR: You lack the permissions necessary to execute that command.""")
        return response
    else:
        pass
        # print("Processing privileged command for: " + msg.author.name)


    if command == "!start_draft":
        response = admin_command_start_draft(msg)
        return response



    return "ERROR: UNIMPLEMENTED, YET VALID COMMAND."




# ASYNCHRONOUS FUNCTIONS

# Consumer Function
async def message_consumer_task():
    global MESSAGE_BUFFER

    await client.wait_until_ready()
    await client.change_presence(game=discord.Game(name="Type \'!help\'"))
    counter = 0
    # channel = discord.Object(id='lab')
    # channel = discord.Object(id="315272164632690688")

    # tempUser = discord.User(id="205108954873856009")
    # await client.send_message(tempUser, "hey")

    while not client.is_closed:

        if counter % 720 == 0:
            # print(str(counter))
            print("Bot is OK.  " + str(datetime.now()))
            counter = 0
        counter += 1

        

        # check if there are messages to process
        if not MESSAGE_BUFFER.empty():

            # The buffer wasn't empty, let's process messages
            message = await MESSAGE_BUFFER.get()
            response = authorizeMessage(message)
#             print("Response:" + """
# """ + response)
            await client.send_message(message.channel, response)

            await asyncio.sleep(1)


        else:
            # There were no messages to process, check to see if we can iterate the draft
            if MAIN_DATA["draftStarted"] == True and MAIN_DATA["draftFinished"] == False:
                # actual drafting occurs here

                # print("Running draft iterator...")
                responseList = draft_iterator()

                for responseDict in responseList:

                    print("Auto Message:\n")
                    print(str(responseDict["id"]) + " " + responseDict["responseBody"])

                    tempUser = discord.User(id = str(responseDict["id"]))
                    await client.send_message(tempUser, responseDict["responseBody"])

                
        

        await asyncio.sleep(3) # loop every few seconds
        


# this is a coroutine and should always end in an await call or return
# Producer Function
@client.event
async def on_message(msg):
    global MESSAGE_BUFFER

    # cmdtime = datetime.datetime.now()

    # Check if the message is a command. If not, we ignore it completely
    if hasattr(msg, 'content'):
        if msg.content is not None:
            if msg.content[0] == "!":
                if msg.channel.is_private == False:
                    # Ignore messages that aren't DMs
                    if msg.author.id == "274745931167956992":
                        await client.send_message(msg.channel, "<3")
                    else:
                        await client.send_message(msg.channel, "Please speak with me in a direct message, I'm shy!")
                else:
                    # The user submitted a potentially valid message in a DM, let's do some processing.

                    await MESSAGE_BUFFER.put(msg)

                    response = "*Processing...*"
                    await client.send_message(msg.channel, response)




def main():

    global MAIN_DATA
    global client

    print()
    print("pkmnDraftBot booted.")

    print("Loading data file.")
    attemptDataFileLoad()

    print("Booting the bot.")

    # https://discordapp.com/oauth2/authorize?client_id=315235415961370635&scope=bot&permissions=0
    client.loop.create_task(message_consumer_task())
    client.run(token)

    print("Shutting down the bot.")
    client.close()

main()

# if __name__ == "__main__":
#     main()
