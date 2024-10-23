# main.py

import os
import sys
import logging
import asyncio
import aiohttp
from dotenv import load_dotenv
import discord
from web3 import Web3
from web3.middleware import geth_poa_middleware
from discord.ext import commands, tasks

load_dotenv()

log_format = '%(asctime)s|%(name)s|%(levelname)s: %(message)s'
logger = logging.getLogger("DFKGasBot")
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.INFO, format=log_format, stream=sys.stdout)

rpc_address = ['https://subnets.avax.network/defi-kingdoms/dfk-chain/rpc', 'https://kaia.rpc.defikingdoms.com/']


class DFKGasBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, intents=discord.Intents.default(), **kwargs)

        self.cv_base_fee_gwei = 0
        self.sd_base_fee_gwei = 0
        self.gas_comparison_string = ""

        self.chain_info = {
            "avalanchedfk": "0xCF329b34049033dE26e4449aeBCb41f1992724D3",
            "klaytn": "0x2C081F2EE4aC7C695CAf6ae0fCB83Ca4EdD0F61f"
        }

    async def get_current_gas(self):
        base_fees = []
        for rpc in rpc_address:
            w3 = Web3(Web3.HTTPProvider(rpc))
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            base_fee = w3.eth.get_block("pending").baseFeePerGas
            base_fees.append(float(Web3.from_wei(base_fee, 'gwei')))
        return base_fees

    async def fetch(self, client, params):
        url = f"https://api.dexscreener.io/latest/dex/pairs/{params['chainId']}/{params['pairAddress']}"
        async with client.get(url) as resp:
            return await resp.json()

    async def get_prices(self, chain_id):
        pair_address = self.chain_info[chain_id]
        params = {'chainId': chain_id, 'pairAddress': pair_address}
        async with aiohttp.ClientSession() as client:
            return await self.fetch(client, params)

    async def compare_realm(self, cv_base_fee_gwei, sd_base_fee_gwei):
        try:
            JEWEL = await self.get_prices("avalanchedfk")
            KLAY = await self.get_prices("klaytn")
            jewel_price = float(JEWEL['pair']['priceUsd'])
            klay_price = float(KLAY['pair']['priceUsd'])

            cv_margin = (cv_base_fee_gwei * jewel_price) / (sd_base_fee_gwei * klay_price)

            if cv_margin > 1:
                pct = round((cv_margin - 1) * 100)
                activity_string = f"CV Gas $: +{pct}% vs SD"
            elif cv_margin < 1:
                pct = round((1 - cv_margin) * 100)
                activity_string = f"CV Gas $: -{pct}% vs SD"
            else:
                activity_string = "CV Gas $: +/- 0% vs SD"
        except Exception:
            return ""
        return activity_string

    async def on_ready(self):
        logger.info(f"{self.user} Online")
        self.update_gas_prices.start()
        self.price_info.start()

    @tasks.loop(seconds=15)
    async def update_gas_prices(self):
        self.cv_base_fee_gwei, self.sd_base_fee_gwei = await self.get_current_gas()
        self.gas_comparison_string = await self.compare_realm(self.cv_base_fee_gwei, self.sd_base_fee_gwei)

    @tasks.loop(seconds=12)
    async def price_info(self):
        activity_string = f"Base Fee: {round(self.cv_base_fee_gwei, 1)} gwei"
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=activity_string))

        await asyncio.sleep(6)

        activity_string = self.gas_comparison_string
        if activity_string != "":
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=activity_string))


bot = DFKGasBot(command_prefix="|")

bot.run(os.getenv("TOKEN"))
