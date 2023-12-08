# main.py

import os, sys, logging
import asyncio, aiohttp
from dotenv import load_dotenv
import discord
from web3 import Web3
from web3.middleware import geth_poa_middleware
from discord.ext import tasks

load_dotenv()

log_format = '%(asctime)s|%(name)s|%(levelname)s: %(message)s'
logger = logging.getLogger("DFKGasBot")
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.INFO, format=log_format, stream=sys.stdout)

rpc_address = ['https://subnets.avax.network/defi-kingdoms/dfk-chain/rpc', 'https://klaytn.rpc.defikingdoms.com/']

intents = discord.Intents.default()
client = discord.Client(intents=intents)

async def getCurrentGas():
    baseFees = []
    for rpc in rpc_address:
        w3 = Web3(Web3.HTTPProvider(rpc))
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        baseFee = w3.eth.getBlock("pending").baseFeePerGas
        baseFees.append(float(round(Web3.fromWei(baseFee, 'gwei'), 1)))
    
    return baseFees

async def fetch(client, params):
    url = f"https://api.dexscreener.io/latest/dex/pairs/{params['chainId']}/{params['pairAddress']}"
    async with client.get(url) as resp:
        return await resp.json()

async def getPrices(params):
    async with aiohttp.ClientSession() as client:
        r = await fetch(client, params)
        return r
        
async def getJEWEL():
    chainId = "avalanchedfk"
    pairAddress = "0xCF329b34049033dE26e4449aeBCb41f1992724D3"
    params = {'chainId': chainId, 'pairAddress': pairAddress}
    r = await getPrices(params)
    return r

async def getKLAY():
    chainId = "klaytn"
    pairAddress = "0x2C081F2EE4aC7C695CAf6ae0fCB83Ca4EdD0F61f"
    params = {'chainId': chainId, 'pairAddress': pairAddress}
    r = await getPrices(params)
    return r

async def compareRealm(cvBaseFeeGwei, sdBaseFeeGwei):
    activity_string = ""
    try:
        JEWEL = await getJEWEL()
        KLAYTN = await getKLAY()
        jewelPrice = float(JEWEL['pair']['priceUsd'])
        klayPrice = float(KLAYTN['pair']['priceUsd'])
        
        cvMargin = round((cvBaseFeeGwei * jewelPrice) / (sdBaseFeeGwei * klayPrice) , 2)
        
        if cvMargin == 1:
            activity_string = "Realm Fee: CV and SD are same"
        elif cvMargin > 1:
            pct = round((cvMargin - 1) * 100)
            activity_string = f"Realm Fee: CV higher by {pct}%"
        else:
            # margin less than 1
            pct = round((1- cvMargin) * 100)
            activity_string = f"Realm Fee: CV cheaper by {pct}%"         
    except Exception:
        return ""
    
    return activity_string
    
@client.event
async def on_ready():
    logger.info(f"{client.user} Online")
    priceInfo.start()

@tasks.loop(seconds=15)
async def priceInfo():
    (cvBaseFeeGwei, sdBaseFeeGwei) = await getCurrentGas()
    activity_string = f"Base Fee: {cvBaseFeeGwei} gwei"
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=activity_string))

    await asyncio.sleep(7)
    
    activity_string = await compareRealm(cvBaseFeeGwei, sdBaseFeeGwei) 
    if activity_string != "":
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=activity_string))
        
        
client.run(os.getenv("TOKEN"))
