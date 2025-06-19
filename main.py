import discord
from discord import app_commands
import requests
import os
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot activo y funcionando"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

PRESENCE_TYPES = {
    0: "Offline",
    1: "Online",
    2: "In Game",
    3: "In Studio",
    4: "Alt farming"
}

ALL_MODS = {
    "Chase": [22808138, 4782733628, 7447190808],
    "Orion": [547598710, 5728889572, 4652232128, 7043591647, 5728889572, 4149966999, 7209929547],
    "LisNix": [162442297, 702354331],
    "Nwr": [307212658, 5097000699, 4923561416, 4531785383],
    "Gorilla": [514679433, 2431747703, 4531785383],
    "Typhon": [2428373515],
    "Vic": [839818760],
    "Erin": [2465133159],
    "Unknown": [7547477786, 7574577126, 2043525911, 5816563976, 240526951, 4531785383,
                1160595313, 7876617827, 7693766866, 2568824396, 7604102307, 7587479685, 2505902503],
}

class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        print(f"Bot {self.user} ({self.user.id})")

    async def setup_hook(self):
        await self.tree.sync()

client = MyClient()

@client.tree.command(name="mods", description="Shows if a mod is online")
async def mods(interaction: discord.Interaction):
    await interaction.response.defer()

    all_user_ids = list({uid for ids in ALL_MODS.values() for uid in ids})
    response = requests.post("https://presence.roblox.com/v1/presence/users", json={"userIds": all_user_ids})
    if response.status_code != 200:
        await interaction.followup.send("Error")
        return

    presences = response.json().get("userPresences", [])
    presence_dict = {user["userId"]: user["userPresenceType"] for user in presences}

    message_lines = []

    for mod_name, user_ids in ALL_MODS.items():
        message_lines.append(f"**{mod_name}**")
        for uid in user_ids:
            presence_code = 4 if uid == 2505902503 else presence_dict.get(uid, 0)
            user_info = requests.get(f"https://users.roblox.com/v1/users/{uid}")
            username = user_info.json().get("name", "Unknown") if user_info.status_code == 200 else "Unknown"

            if presence_code == 1:
                line = f"```ini[Online]: {username}```"
            elif presence_code == 2:
                line = f"```diff+ In Game: {username}```"
            elif presence_code == 3:
                line = f"```fixIn Studio: {username}```"
            elif presence_code == 4:
                line = f"```diff- Alt Farming: {username}```"
            else:
                line = f"```diff- Offline: {username}```"

            message_lines.append(line)
        message_lines.append("")

    final_message = "\n".join(message_lines)
    await interaction.followup.send(final_message)

keep_alive()
client.run(os.getenv("BOT_TOKEN"))
