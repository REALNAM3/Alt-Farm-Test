import discord
from discord import app_commands
import requests
import asyncio
import datetime
import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

PRESENCE_TYPES = {
    0: "Offline",
    1: "Online",
    2: "In Game",
    3: "In Studio",
}

ALL_MODS = {
    "Chase": [22808138, 4782733628, 7447190808, 3196162848],
    "Orion": [547598710, 5728889572, 4652232128, 7043591647, 4149966999, 7209929547, 7043958628, 7418525152],
    "LisNix": [162442297, 702354331],
    "Nwr": [307212658, 5097000699, 4923561416],
    "Gorilla": [514679433, 2431747703, 4531785383],
    "Typhon": [2428373515],
    "Vic": [839818760],
    "Erin": [2465133159],
    "Ghost": [7558211130],
    "Unknown": [7547477786, 7574577126, 2043525911, 5816563976, 240526951, 7587479685,
                1160595313, 7876617827, 7693766866, 2568824396, 7604102307],
}

class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.checking_task = None
        self.checking_user_id = None

    async def on_ready(self):
        print(f"Bot {self.user} ({self.user.id})")

    async def setup_hook(self):
        await self.tree.sync()

    async def build_mod_status(self) -> str:
        all_user_ids = list({uid for ids in ALL_MODS.values() for uid in ids})
        response = requests.post("https://presence.roblox.com/v1/presence/users", json={"userIds": all_user_ids})
        if response.status_code != 200:
            return "Error."

        presences = response.json().get("userPresences", [])
        presence_dict = {user["userId"]: user["userPresenceType"] for user in presences}

        message_lines = []
        any_in_game = False

        for mod_name, user_ids in ALL_MODS.items():
            message_lines.append(f"**{mod_name}**")
            for uid in user_ids:
                presence_code = presence_dict.get(uid, 0)
                user_info = requests.get(f"https://users.roblox.com/v1/users/{uid}")
                username = user_info.json().get("name", "Unknown") if user_info.status_code == 200 else "Unknown"

                if presence_code == 1:
                    line = f"```ini\n[Online]: {username}\n```"
                elif presence_code == 2:
                    line = f"```diff\n+ In Game: {username}\n```"
                    any_in_game = True
                elif presence_code == 3:
                    line = f"```fix\nIn Studio: {username}\n```"
                else:
                    line = f"```diff\n- Offline: {username}\n```"
                message_lines.append(line)
            message_lines.append("")

        status_line = "**Status: Unalt Farmable**" if any_in_game else "**Status: Farmable**"
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        message_lines.append(status_line)
        message_lines.append(f"*Last update: {timestamp}*")

        final_message = "\n".join(message_lines)
        if len(final_message) > 2000:
            final_message = final_message[:1990] + "\n[Truncado por límite de Discord]"
        return final_message

client = MyClient()

@client.tree.command(name="mods", description="Shows if a mod is online")
async def mods(interaction: discord.Interaction):
    await interaction.response.defer()
    content = await client.build_mod_status()
    await interaction.followup.send(content)

@client.tree.command(name="checkmods", description="Checks mods every 10 seconds")
async def checkmods(interaction: discord.Interaction):
    await interaction.response.send_message("Started checking every 10 seconds...", ephemeral=True)
    monitor_msg = await interaction.channel.send("Loading mod status...")

    client.checking_user_id = interaction.user.id

    async def periodic_check(msg):
        try:
            while True:
                content = await client.build_mod_status()
                try:
                    await msg.edit(content=content)
                except discord.HTTPException as e:
                    print(f"Error editing message: {e}")
                    break
                await asyncio.sleep(10)
        except asyncio.CancelledError:
            await msg.edit(content="Stopped checking")

    if client.checking_task is None or client.checking_task.done():
        client.checking_task = asyncio.create_task(periodic_check(monitor_msg))
    else:
        await interaction.followup.send("There is no active checking")

@client.tree.command(name="stopcheck", description="Stops the check from the command /checkmods")
async def stopcheck(interaction: discord.Interaction):
    if client.checking_task and not client.checking_task.done():
        if interaction.user.id != client.checking_user_id:
            await interaction.response.send_message("Only the person who activated it can stop it.", ephemeral=True)
            return

        client.checking_task.cancel()
        client.checking_task = None
        client.checking_user_id = None
        await interaction.response.send_message("Stopped checking")
    else:
        await interaction.response.send_message("There is no currently checking")

keep_alive()
client.run(os.getenv("BOT_TOKEN"))
