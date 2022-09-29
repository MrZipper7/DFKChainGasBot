# main.py

import os, sys, logging
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

rpc_address = 'https://subnets.avax.network/defi-kingdoms/dfk-chain/rpc'

intents = discord.Intents.default()
client = discord.Client(intents=intents)

async def getCurrentGas():
    w3 = Web3(Web3.HTTPProvider(rpc_address))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    baseFee = w3.eth.getBlock("pending").baseFeePerGas
    return round(Web3.fromWei(baseFee, 'gwei'), 1)

@client.event
async def on_ready():
    logger.info(f"{client.user} Online")
    priceInfo.start()

@tasks.loop(seconds=15)
async def priceInfo():
    baseFeeGwei = await getCurrentGas()
    activity_string = f"Base Fee: {baseFeeGwei} gwei"
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=activity_string))

client.run(os.getenv("TOKEN"))
