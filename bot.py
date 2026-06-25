import discord
from discord.ext import commands
from discord import app_commands
import os
import io
import json
import random
import threading
import requests
import base64
import re  
from datetime import datetime, timedelta
from flask import Flask

# --- Flask Keep-Alive Web Server ---
# ==============================================================================
# --- FIXED FLASK KEEP-ALIVE WEB SERVER ARCHITECTURE ---
# ==============================================================================
app = Flask('')

@app.route('/')
def home():
    return "OK", 200

if not hasattr(app, "_already_running"):
    app._already_running = False

def run_web_server():
    if app._already_running:
        print("ℹ️ Flask loop bypass: Server instance already established.")
        return
        
    port = int(os.environ.get("PORT", 8080))
    try:
        app._already_running = True
        app.run(host='0.0.0.0', port=port, threaded=True, use_reloader=False)
    except Exception as e:
        print(f"⚠️ Flask Web Server Port Bind Warning: {e}")

def keep_alive():
    t = threading.Thread(target=run_web_server)
    t.daemon = True
    t.start()


# --- Configuration & Security ---
TOKEN = os.environ.get("DISCORD_TOKEN")
DATABASE_FILE = "card_league_database.json"

# --- GitHub Auto-Sync Save System Configurations ---
GITHUB_USERNAME = "DynoVR"
GITHUB_REPO = "TBA-Bot"
GITHUB_FILE_PATH = "card_league_database.json"
GH_TOKEN = os.environ.get("GH_TOKEN")

# Ordered priority mapping for sorted card ledger structures
RARITY_ORDER = ["Specialty", "Otherworldly", "Juggernaut", "Pro", "Insane", "Epic", "Great", "Average"]

# Global Tracker Container for Matchmaking Queues
ACTIVE_QUEUES = {1: [], 2: [], 3: []}

# --- Complete Consolidated Database System Template ---
DATA = {
    "season_title": "TBA League",
    "games_count": 0,
    "preseason": False,
    "teams": {},
    "players": {},
    "schedule": [],
    "playoffs": { "active": False, "best_of": 3, "rounds": {} },
    "global_cards": {},  
    "users": {},         
    "matches": {},       
    "next_match_id": 1,
    "config": {
        "pack_3_price": 50,
        "pack_5_price": 80,
        "pack_10_price": 150,
        "match_reward": 25,
        "queue_role_id": None,
        "match_role_id": None,
        "sell_prices": {
            "Average": 10,
            "Great": 20,
            "Epic": 40,
            "Insane": 75,
            "Pro": 150,
            "Juggernaut": 300,
            "Otherworldly": 750,
            "Specialty": 1500
        }
    }
}


# ==============================================================================
# --- FIXED DATABASE CLOUD ROUTING CORE ENGINE ---
# ==============================================================================

def load_data():
    global DATA
    print("🔄 Initiating master league database synchronization...")
    
    if GH_TOKEN:
        try:
            # FIXED LINK: Fully typed destination path to prevent connection resets
            url = "https://github.com"
            headers = {
                "Authorization": f"Bearer {GH_TOKEN}", 
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Discord-Bot-Data-Sync"
            }
            res = requests.get(url, headers=headers)
            
            if res.status_code == 200:
                file_data = res.json()
                content = base64.b64decode(file_data["content"]).decode("utf-8")
                loaded_json = json.loads(content)
                
                if loaded_json.get("users") or loaded_json.get("global_cards"):
                    DATA = loaded_json
                    print("☁️ Success: Permanent database successfully pulled and restored from GitHub Cloud!")
                    
                    with open(DATABASE_FILE, "w") as f:
                        json.dump(DATA, f, indent=4)
                    return
                else:
                    print("⚠️ Cloud Pull Alert: Remote file exists but appeared blank. Checking local fallback.")
            else:
                print(f"⚠️ Cloud Pull Bypass ({res.status_code}): No remote backup found or API limit hit.")
        except Exception as e:
            print(f"❌ GitHub Critical Cloud Pull Fault: {e}")

    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, "r") as f:
                local_data = json.load(f)
                if local_data.get("users") or local_data.get("global_cards"):
                    DATA = local_data
                    print("💾 Local cache database loaded successfully as fallback configuration.")
                    return
        except Exception as e:
            print(f"❌ Local Read Error: {e}")
            
    print("🚨 System Warning: No valid remote or local database detected. Initializing clean template layer.")


def save_data():
    """Saves data locally and forces an authorized backup commit to GitHub Cloud securely."""
    try:
        with open(DATABASE_FILE, "w") as f:
            json.dump(DATA, f, indent=4)
        print("💾 System state written to local cache successfully.")
    except Exception as e:
        print(f"❌ Local Write Fault: {e}")

    if not GH_TOKEN:
        print("⚠️ Warning: 'GH_TOKEN' environment key missing. Cloud sync skipped.")
        return

    try:
        # FIXED LINK: Fully typed destination path to prevent connection resets
        url = "https://github.com"
        
        headers = {
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Discord-Bot-Data-Sync"
        }
        
        get_req = requests.get(url, headers=headers)
        sha = None
        if get_req.status_code == 200:
            sha = get_req.json().get("sha")
            
        content_bytes = json.dumps(DATA, indent=4).encode('utf-8')
        encoded_content = base64.b64encode(content_bytes).decode('utf-8')
        
        payload = {
            "message": "🔄 Automated Live Database State Backup Sync",
            "content": encoded_content
        }
        if sha:
            payload["sha"] = sha
            
        put_req = requests.put(url, headers=headers, json=payload)
        
        if put_req.status_code in (200, 201):
            print("☁️ Permanent database securely backed up to GitHub Cloud successfully!")
        else:
            print(f"❌ GitHub API Sync Failed ({put_req.status_code}): {put_req.text}")
            
    except Exception as e:
        print(f"❌ GitHub Cloud Backup Loop Crash: {e}")

# --- Configuration & Security ---
TOKEN = os.environ.get("DISCORD_TOKEN")
DATABASE_FILE = "card_league_database.json"
# --- Configuration & Security ---
TOKEN = os.environ.get("DISCORD_TOKEN")
DATABASE_FILE = "card_league_database.json"

# --- GitHub Auto-Sync Save System Configurations ---
GITHUB_USERNAME = "DynoVR"
GITHUB_REPO = "TBA-Bot"
GITHUB_FILE_PATH = "card_league_database.json"
GH_TOKEN = os.environ.get("GH_TOKEN")

# Ordered priority mapping for sorted card ledger structures
RARITY_ORDER = ["Specialty", "Otherworldly", "Juggernaut", "Pro", "Insane", "Epic", "Great", "Average"]

# Global Tracker Container for Matchmaking Queues
ACTIVE_QUEUES = {1: [], 2: [], 3: []}

# --- Complete Consolidated Database System ---
DATA = {
    "season_title": "TBA League",
    "games_count": 0,
    "preseason": False,
    "teams": {},
    "players": {},
    "schedule": [],
    "playoffs": { "active": False, "best_of": 3, "rounds": {} },
    "global_cards": {},  # unique_card_id -> { name, player_id, rarity, overall, image_url }
    "users": {},         # user_id -> { coins, inventory: {unique_card_id: count}, last_weekly, wins, losses }
    "matches": {},       # match_id -> { channel_id, type, team1: [], team2: [], votes: {player_id: vote_int} }
    "next_match_id": 1,
    "config": {
        "pack_3_price": 150,
        "pack_5_price": 250,
        "pack_10_price": 400,
        "match_reward": 50,
        "queue_role_id": None,
        "match_role_id": None,
        "sell_prices": {
            "Average": 10,
            "Great": 20,
            "Epic": 40,
            "Insane": 75,
            "Pro": 150,
            "Juggernaut": 300,
            "Otherworldly": 750,
            "Specialty": 1000
        }
    }
}

def save_data():
    """Saves data locally and forces an authorized backup commit to GitHub Cloud securely."""
    # 1. Always write to the local virtual directory first
    try:
        with open(DATABASE_FILE, "w") as f:
            json.dump(DATA, f, indent=4)
        print("💾 System state written to local cache successfully.")
    except Exception as e:
        print(f"❌ Local Write Fault: {e}")

    # 2. Skip the cloud backup if your Render Environment variable is missing
    if not GH_TOKEN:
        print("⚠️ Warning: 'GH_TOKEN' environment key missing. Cloud sync skipped.")
        return

    # 3. Execute the authorized GitHub cloud transfer pipeline
    try:
        url = f"https://github.com{GITHUB_USERNAME}{GITHUB_USERNAME}{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
        
        # FIXED: Reinforced authorized request headers to authenticate with private repositories
        headers = {
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Discord-Bot-Data-Sync"
        }
        
        # Look up if the file already exists to grab its mandatory version tracking 'sha' code
        get_req = requests.get(url, headers=headers)
        sha = None
        if get_req.status_code == 200:
            sha = get_req.json().get("sha")
        
        # Encode your master dictionary into clean base64 data streams
        content_bytes = json.dumps(DATA, indent=4).encode('utf-8')
        encoded_content = base64.b64encode(content_bytes).decode('utf-8')
        
        payload = {
            "message": "🔄 Automated Live Database State Backup Sync",
            "content": encoded_content
        }
        if sha:
            payload["sha"] = sha
            
        # Pushing the file updates up to your live repo
        put_req = requests.put(url, headers=headers, json=payload)
        
        if put_req.status_code in (200, 201):
            print("☁️ Permanent database securely backed up to GitHub Cloud successfully!")
        else:
            print(f"❌ GitHub API Sync Failed ({put_req.status_code}): {put_req.text}")
            
    except Exception as e:
        print(f"❌ GitHub Cloud Backup Loop Crash: {e}")

def verify_user(user_id_str, username="Unknown"):
    if user_id_str not in DATA["users"]:
        DATA["users"][user_id_str] = {
            "name": username, "coins": 150, "inventory": {},
            "last_weekly": None, "wins": 0, "losses": 0
        }

# --- Permission Check Decorators ---
def is_staff():
    async def predicate(ctx):
        if ctx.author.id == ctx.guild.owner_id:
            return True
        staff_role_id = DATA["config"].get("staff_role_id")
        if staff_role_id:
            return any(str(role.id) == str(staff_role_id) for role in ctx.author.roles)
        return any(role.name.lower() == "staff" for role in ctx.author.roles)
    return commands.check(predicate)

# --- Bot Initialization ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

bot.remove_command("help")

from discord.ext import tasks

# Track processed message IDs so players never receive duplicate coin payouts
if "processed_neatque_matches" not in DATA:
    DATA["processed_neatque_matches"] = []

# ==============================================================================
# --- AUTOMATED BACKGROUND AUDIT SEARCH ENGINE ---
# ==============================================================================

@tasks.loop(seconds=30)
async def automatic_neatque_scanner():
    """Background Task: Actively processes text and columns inside explicit NeatQue result rooms."""
    await bot.wait_until_ready()
    
    for guild in bot.guilds:
        try:
            await guild.chunk(cache=True)
        except:
            pass
            
        for channel in guild.text_channels:
            channel_name = channel.name.lower()
            
            # 🎯 FIXED: Direct target filter matching your exact Discord channel names
            is_target_channel = (
                "ranked-que" in channel_name or 
                "ranked-1s" in channel_name or
                "queue" in channel_name or 
                "match" in channel_name
            )
            
            if is_target_channel:
                try:
                    # Scan the last 15 messages posted in that channel arena
                    async for message in channel.history(limit=15):
                        if str(message.id) in DATA["processed_neatque_matches"]:
                            continue
                            
                        is_neat = "neat" in message.author.name.lower() or message.author.id == 857633321064595466
                        is_webhook = message.webhook_id is not None
                        is_bot = message.author.bot
                        
                        if is_neat or is_webhook or is_bot:
                            text_to_scan = ""
                            
                            if message.content:
                                text_to_scan += message.content + "\n"
                                
                            if message.embeds:
                                for embed in message.embeds:
                                    if embed.title: text_to_scan += embed.title + "\n"
                                    if embed.description: text_to_scan += embed.description + "\n"
                                    for field in embed.fields: text_to_scan += f" {field.name} {field.value} \n"

                            clean_text_payload = text_to_scan.lower()

                            # Strict check: Must announce a final winner, skip the lobby waiting queues
                            if "winner" not in clean_text_payload or "potential" in clean_text_payload:
                                continue

                            winning_user_ids = []
                            losing_user_ids = []
                            
                            # Extract native account identifiers out of the horizontal column tracks
                            winners_found = re.findall(r"<@!?(\d+)>(?=[^<>\n]*\+)", text_to_scan)
                            losers_found = re.findall(r"<@!?(\d+)>(?=[^<>\n]*\-)", text_to_scan)
                            
                            # String Nickname Match Fallback
                            if not winners_found and not losers_found:
                                for line in text_to_scan.split("\n"):
                                    line = line.strip()
                                    if not line or ("+" not in line and "-" not in line):
                                        continue
                                        
                                    has_plus = "+" in line
                                    has_minus = "-" in line
                                    
                                    clean_line = re.sub(r"\([^\)]+\)", "", line)  
                                    clean_line = re.sub(r"[\+\-]\s*\d+[\d\.]*", "", clean_line)  
                                    clean_line = clean_line.replace("@", "").strip()  
                                    
                                    if not clean_line or len(clean_line) < 2:
                                        continue
                                        
                                    member = discord.utils.get(guild.members, display_name=clean_line) or \
                                             discord.utils.get(guild.members, name=clean_line)
                                             
                                    if not member:
                                        search_text = clean_line.lower()
                                        for m in guild.members:
                                            if search_text in m.display_name.lower() or search_text in m.name.lower():
                                                member = m
                                                break
                                                
                                    if member:
                                        p_id_str = str(member.id)
                                        if has_plus and p_id_str not in winning_user_ids:
                                            winning_user_ids.append(p_id_str)
                                        elif has_minus and p_id_str not in losing_user_ids:
                                            losing_user_ids.append(p_id_str)
                            else:
                                winning_user_ids = winners_found
                                losing_user_ids = losers_found
                                
                            if winning_user_ids or losing_user_ids:
                                reward = DATA["config"].get("match_reward", 25)
                                awarded_mentions = []
                                
                                for p_id in winning_user_ids:
                                    p_str = str(p_id)
                                    verify_user(p_str, f"User {p_str}")
                                    DATA["users"][p_str]["coins"] += reward
                                    DATA["users"][p_str]["wins"] += 1
                                    awarded_mentions.append(f"<@{p_str}>")
                                    
                                for p_id in losing_user_ids:
                                    p_str = str(p_id)
                                    verify_user(p_str, f"User {p_str}")
                                    DATA["users"][p_str]["losses"] += 1
                                    
                                DATA["processed_neatque_matches"].append(str(message.id))
                                save_data()
                                
                                if awarded_mentions:
                                    await channel.send(
                                        f"🪙 **NeatQueue Automated Link Synced!** Final match result parsed successfully.\n"
                                        f"The following winners have been credited with **{reward} coins**: "
                                        f"{', '.join(awarded_mentions)}"
                                    )
                except Exception as e:
                    pass


# ==============================================================================
# --- BOT INITIALIZER AND EVENT HOOKS ---
# ==============================================================================

@bot.event
async def on_ready():
    print(f"🏒 Bot Online: Connected as {bot.user.name} ({bot.user.id})")
    
    # Start your background loop safely
    if not automatic_neatque_scanner.is_running():
        automatic_neatque_scanner.start()
        print("🚀 Automated NeatQueue background scanner engine started safely.")
        
    # GLOBAL SYNC: Registers all slash commands cleanly to Discord
    try:
        synced = await bot.tree.sync()
        print(f"🌲 Successfully synchronized {len(synced)} application slash commands globally.")
    except Exception as e:
        print(f"❌ Application Command Tree Sync Fault: {e}")

@bot.command(name="forcesync")
async def forcesync(ctx):
    """Bypasses all caches and forces absolute registration of every hybrid command."""
    await ctx.defer()
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Master Force Sync Complete! Registered **{len(synced)}** slash layouts globally.")
    except Exception as e:
        await ctx.send(f"❌ Force Sync Crashed: {e}")

# ==============================================================================
# --- BOT RUNNER EXECUTOR (THE VERY BOTTOM OF YOUR FILE) ---
# ==============================================================================

# Launch the local Flask server to keep Render web health checks green
keep_alive()

# Launch the primary bot client thread instance safely
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ Critical System Initialization Fault: 'DISCORD_TOKEN' environment key is blank.")

@bot.command(name="forcesync")
async def forcesync(ctx):
    """Bypasses all caches and forces absolute registration of every hybrid command."""
    await ctx.defer()
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Master Force Sync Complete! Registered **{len(synced)}** slash layouts to Discord servers.")
    except Exception as e:
        await ctx.send(f"❌ Force Sync Crashed: {e}")


# ==============================================================================
# --- SYSTEM MANAGEMENT & HELP MODULES ---
# ==============================================================================

@bot.hybrid_command(name="setstaffrole", description="Owner Command: Configure which server role acts as bot staff admin")
@commands.has_permissions(administrator=True)
async def setstaffrole(ctx, role: discord.Role):
    DATA["config"]["staff_role_id"] = str(role.id)
    save_data()
    await ctx.send(f"🛡️ **Staff Role Configured!** Users with the role {role.mention} can now execute administration nodes.")

@bot.hybrid_command(name="setmatchreward", description="Staff Command: Configure coin prize value awarded to winning match pools")
@is_staff()
async def setmatchreward(ctx, amount: int):
    DATA["config"]["match_reward"] = max(0, amount)
    save_data()
    await ctx.send(f"🪙 **Match Reward Updated!** Winning players will now receive `{amount}` coins per victory.")

@bot.hybrid_command(name="help", description="Public Command: Display full blueprint command reference deck index manual")
async def help_command(ctx):
    embed = discord.Embed(title="🏒 League System Command Directory", color=discord.Color.blue())
    embed.add_field(name="🌐 Public Card Commands", value="`/catalog [page]` - View master card list\n`/inventory [player]` - Inspect owned profile card vault\n`/buypack <size>` - Purchase 3, 5, or 10 random players\n`/claimweekly` - Claim free 3-pack weekly box reward\n`/trade <target> <your_card_id> <their_card_id>` - Swap card assets safely\n`/leaderboard` - Check competitive win ratings standings", inline=False)
    embed.add_field(name="⚔️ Matchmaking Commands", value="`/setupqueue <size>` - Deploy interactive match waiting panel\n`Buttons` - Join/Leave queue pool interface nodes", inline=False)
    embed.add_field(name="🛡️ Staff Administration (Requires Staff Role/Owner)", value="`/setstaffrole <role>` - Update staff role reference mapping\n`/setmatchreward <coins>` - Change match victory payout amount\n`/addcard <player> <rarity> <overall> [image_url]` - Initialize new custom card ID profile\n`/editcard <card_id> <rarity> <overall> [image_url]` - Modify precise attributes parameters on a card instance\n`/removecard <card_id>` - Delete specific card profile permanently\n`/editcoins <give/take> <player> <amount>` - Change balance values safely\n`/cancelmatch <match_id>` - Terminate an active game room instances layer\n`/substitute <match_id> <old_player> <new_player>` - Swap players mid-match series", inline=False)
    await ctx.send(embed=embed)

# ==============================================================================
# --- CARD SYSTEM ENGINE ---
# ==============================================================================

@bot.hybrid_command(name="addcard", description="Staff Command: Initialize a new player card instance profile into catalog records")
@is_staff()
@app_commands.choices(rarity=[app_commands.Choice(name=r, value=r) for r in RARITY_ORDER])
async def addcard(ctx, player: discord.Member, rarity: str, overall: int, image_url: str = None):
    # Generates a clean random string identifier tag for that explicit card instance version
    card_id = f"{player.name.lower()}_{rarity.lower()}_{random.randint(100, 999)}"
    DATA["global_cards"][card_id] = {
        "id": card_id, "name": player.display_name, "player_id": str(player.id),
        "rarity": rarity, "overall": max(1, min(overall, 99)), "image_url": image_url or ""
    }
    save_data()
    await ctx.send(f"✅ Created Card Profile ID: `{card_id}` for **{player.display_name}**! [{rarity} | {overall} OVR]")

@bot.hybrid_command(name="editcard", description="Staff Command: Modify the rarity, overall, or picture assets of a precise unique card identity code")
@is_staff()
@app_commands.choices(rarity=[app_commands.Choice(name=r, value=r) for r in RARITY_ORDER])
async def editcard(ctx, card_id: str, rarity: str, overall: int, image_url: str = None):
    if card_id not in DATA["global_cards"]:
        return await ctx.send(f"❌ Error: Card reference identifier code `{card_id}` does not exist in master catalog paths.")
    
    card = DATA["global_cards"][card_id]
    card["rarity"] = rarity
    card["overall"] = max(1, min(overall, 99))
    if image_url: 
        card["image_url"] = image_url
        
    save_data()
    await ctx.send(f"🔧 Successfully configured precise updates onto Card `{card_id}`! New properties: [{rarity} | {overall} OVR]")


@bot.hybrid_command(name="removecard", description="Staff Command: Erase a precise card target ID permanently out of the league data trees")
@is_staff()
async def removecard(ctx, card_id: str):
    if card_id not in DATA["global_cards"]:
        return await ctx.send("❌ Error: Target card identity target index missing.")
        
    card_name = DATA["global_cards"][card_id]["name"]
    rarity = DATA["global_cards"][card_id]["rarity"]
    del DATA["global_cards"][card_id]
    
    for u_id in DATA["users"]:
        if card_id in DATA["users"][u_id]["inventory"]:
            del DATA["users"][u_id]["inventory"][card_id]
            
    save_data()
    await ctx.send(f"🗑️ Successfully deleted version **[{rarity}] {card_name}** (`{card_id}`) from all active server inventory registries.")


# ==============================================================================
# --- CARD PACK DRAW ENGINE & STORE SYSTEMS ---
# ==============================================================================

# ==============================================================================
# --- INTERACTIVE CARD LIQUIDATION ENGINE & STORE SYSTEMS ---
# ==============================================================================

@bot.hybrid_command(name="changecardprice", description="Staff Command: Configure how much currency a player receives when selling a specific rarity")
@is_staff()
@app_commands.choices(rarity=[app_commands.Choice(name=r, value=r) for r in RARITY_ORDER])
async def changecardprice(ctx, rarity: str, new_sell_price: int):
    if new_sell_price < 0:
        return await ctx.send("❌ **Fault:** Sell price valuations cannot evaluate to negative metrics.")

    # Safeguard underlying nested layout keys
    if "config" not in DATA: DATA["config"] = {}
    if "sell_prices" not in DATA["config"]: DATA["config"]["sell_prices"] = {}

    DATA["config"]["sell_prices"][rarity] = new_sell_price
    save_data()
    
    await ctx.send(f"🏷️ **Rarity Market Configured!** Selling a **[{rarity}]** card asset will now credit players with `{new_sell_price}` coins.")


class SellQuantityModal(discord.ui.Modal):
    """Secure popup textbox frame to input explicit quantity parameters for liquidation transactions."""
    quantity_input = discord.ui.TextInput(
        label="Quantity to Sell",
        placeholder="Enter a whole number (e.g. 1, 2, 5)...",
        min_length=1,
        max_length=4,
        required=True
    )

    def __init__(self, card_id: str, card_name: str, rarity: str, owned_count: int, unit_price: int):
        super().__init__(title=f"Sell: {card_name}")
        self.card_id = card_id
        self.card_name = card_name
        self.rarity = rarity
        self.owned_count = owned_count
        self.unit_price = unit_price

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        raw_val = self.quantity_input.value.strip()

        # Enforce structural sanitization bounds
        if not raw_val.isdigit():
            return await interaction.response.send_message("❌ **Transaction Denied:** Please enter a valid, positive whole number.", ephemeral=True)

        qty_to_sell = int(raw_val)
        if qty_to_sell <= 0:
            return await interaction.response.send_message("❌ **Transaction Denied:** Liquidation amount parameters must be greater than 0.", ephemeral=True)

        # Cross-reference live possession counts to eliminate item duplication loops
        current_owned = DATA["users"][user_id]["inventory"].get(self.card_id, 0)
        if qty_to_sell > current_owned:
            return await interaction.response.send_message(
                f"❌ **Vault Mismatch:** You chose to liquidate `{qty_to_sell}` copies, but you only own `{current_owned}` of this card profile item.",
                ephemeral=True
            )

        # Process ledger financial transfer settlements
        total_payout = qty_to_sell * self.unit_price
        DATA["users"][user_id]["inventory"][self.card_id] -= qty_to_sell
        DATA["users"][user_id]["coins"] += total_payout
        
        save_data()

        embed = discord.Embed(title="💰 Vault Assets Liquidated!", color=discord.Color.green())
        embed.description = (
            f"Successfully sold **{qty_to_sell}x** **[{self.rarity}] {self.card_name}**!\n\n"
            f"• **Unit Valuation Price:** `{self.unit_price}` coins\n"
            f"• **Total Earnings Deposited:** `+{total_payout}` coins 🪙\n"
            f"• **Remaining Balance:** `{DATA['users'][user_id]['coins']}` coins"
        )
        await interaction.response.send_message(embed=embed, ephemeral=False)


class SellCardDropdown(discord.ui.Select):
    """Dynamic inventory mapping interface listing owned cards ready for market trade pipelines."""
    def __init__(self, options_list):
        super().__init__(placeholder="Select which player card you want to liquidate...", min_values=1, max_values=1, options=options_list)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        card_id = self.values[0]

        # Ensure account files still register target assets
        if card_id not in DATA["global_cards"] or DATA["users"][user_id]["inventory"].get(card_id, 0) <= 0:
            return await interaction.response.send_message("❌ **Error:** Asset target missing or already sold.", ephemeral=True)

        card = DATA["global_cards"][card_id]
        rarity = card["rarity"]
        owned_count = DATA["users"][user_id]["inventory"][card_id]

        # Calculate live price metrics out of config data trees
        sell_prices_dict = DATA["config"].get("sell_prices", {})
        unit_price = sell_prices_dict.get(rarity, 10)  # Default fallback price setting if unset

        # Open the quantity select popup terminal screen form input node
        modal = SellQuantityModal(
            card_id=card_id, 
            card_name=card["name"], 
            rarity=rarity, 
            owned_count=owned_count, 
            unit_price=unit_price
        )
        await interaction.response.send_modal(modal)


class SellCardView(discord.ui.View):
    def __init__(self, options_list):
        super().__init__(timeout=60.0)
        self.add_item(SellCardDropdown(options_list))


@bot.hybrid_command(name="sellcard", description="Public Command: Select and liquidate duplicate player cards for economy coins")
async def sellcard(ctx):
    user_id = str(ctx.author.id)
    verify_user(user_id, ctx.author.display_name)

    inventory_ledger = DATA["users"][user_id].get("inventory", {})
    valid_owned_cards = []

    # Map cards currently in user inventory
    for cid, count in inventory_ledger.items():
        if count > 0 and cid in DATA["global_cards"]:
            valid_owned_cards.append((cid, DATA["global_cards"][cid], count))

    if not valid_owned_cards:
        return await ctx.send("🎒 **Vault Empty:** You do not own any player card assets inside your vault directory right now.")

    # Sort items by structural system configs mapping to present cleanly
    valid_owned_cards.sort(key=lambda x: (RARITY_ORDER.index(x[1]["rarity"]) if x[1]["rarity"] in RARITY_ORDER else 99, -x[1]["overall"]))

    sell_prices_dict = DATA["config"].get("sell_prices", {})
    dropdown_options = []

    # Build active dropdown interaction options lists (Discord caps selections layout to 25 items max per field view node row)
    for cid, card, count in valid_owned_cards[:25]:
        price = sell_prices_dict.get(card["rarity"], 10)
        dropdown_options.append(discord.SelectOption(
            label=f"{card['name']} ({card['overall']} OVR)",
            description=f"Rarity: {card['rarity']} | Owned: x{count} | Payout: {price} coins/ea",
            value=cid,
            emoji="🎴"
        ))

    embed = discord.Embed(
        title="🏦 League Player Liquidation Asset Market", 
        description="Select a player item from the dropdown deck directory menu layer below to access the quantity settlement ledger box.",
        color=discord.Color.green()
    )
    embed.set_footer(text="Trading window terminal closes automatically after 60 seconds of inactivity.")

    view = SellCardView(dropdown_options)
    await ctx.send(embed=embed, view=view, ephemeral=True)

def draw_random_cards(count: int) -> list:
    """Helper algorithm to select card IDs based on probability distributions."""
    if not DATA["global_cards"]:
        return []

    # Group baseline catalog cards by their active rarity tier
    grouped = {rarity: [] for rarity in RARITY_ORDER}
    for card_id, card_data in DATA["global_cards"].items():
        if card_data["rarity"] in grouped:
            grouped[card_data["rarity"]].append(card_id)

    weights_map = {
        "Average": 45.0, 
        "Great": 25.0, 
        "Epic": 15.0, 
        "Insane": 8.0, 
        "Pro": 4.0, 
        "Juggernaut": 2.0, 
        "Otherworldly": 0.8, 
        "Specialty": 0.2
    }
    
    drawn = []
    for _ in range(count):
        valid_r = [r for r in RARITY_ORDER if grouped[r]]
        
        if not valid_r:
            drawn.append(random.choice(list(DATA["global_cards"].keys())))
            continue
            
        weights = [weights_map[r] for r in valid_r]
        sel_r = random.choices(valid_r, weights=weights, k=1)[0]
        drawn.append(random.choice(grouped[sel_r]))
        
    return drawn



@bot.hybrid_command(name="buypack", description="Public Command: Spend coins to draw player items packs")
@app_commands.choices(pack_size=[
    app_commands.Choice(name="3 Players", value=3), 
    app_commands.Choice(name="5 Players", value=5), 
    app_commands.Choice(name="10 Players", value=10)
])
async def buypack(ctx, pack_size: int):
    if not DATA["global_cards"]: 
        return await ctx.send("❌ Store Closed: Card profiles directories uninitialized.")
        
    u_id = str(ctx.author.id)
    verify_user(u_id, ctx.author.display_name)
    
    cost = DATA["config"].get(f"pack_{pack_size}_price", 150)
    if DATA["users"][u_id]["coins"] < cost:
        return await ctx.send(f"❌ Low Balance: Pack requires {cost} coins. Balance: {DATA['users'][u_id]['coins']}")
        
    DATA["users"][u_id]["coins"] -= cost
    pulled = draw_random_cards(pack_size)
    
    lines = []
    for c_id in pulled:
        card = DATA["global_cards"][c_id]
        DATA["users"][u_id]["inventory"][c_id] = DATA["users"][u_id]["inventory"].get(c_id, 0) + 1
        lines.append(f"• [{card['rarity']}] {card['name']} ({card['overall']} OVR) - ID: {c_id}")
        
    save_data()
    embed = discord.Embed(title="🎉 Box Opening Sequence Complete!", description="\n".join(lines), color=discord.Color.gold())
    await ctx.send(embed=embed)


@bot.hybrid_command(name="claimweekly", description="Public Command: Claim free weekly card starter drop package")
async def claimweekly(ctx):
    if not DATA["global_cards"]: 
        return await ctx.send("❌ Empty directories.")
        
    u_id = str(ctx.author.id)
    verify_user(u_id, ctx.author.display_name)
    
    now = datetime.now()
    last = DATA["users"][u_id].get("last_weekly")
    
    if last and now < datetime.fromisoformat(last) + timedelta(days=7):
        rem = (datetime.fromisoformat(last) + timedelta(days=7)) - now
        return await ctx.send(f"⏳ Cooldown Active: Try again in {rem.days} days and {rem.seconds // 3600} hours.")
        
    pulled = draw_random_cards(3)
    lines = []
    for c_id in pulled:
        card = DATA["global_cards"][c_id]
        DATA["users"][u_id]["inventory"][c_id] = DATA["users"][u_id]["inventory"].get(c_id, 0) + 1
        lines.append(f"🎁 [{card['rarity']}] {card['name']} ({card['overall']} OVR)")
        
    DATA["users"][u_id]["last_weekly"] = now.isoformat()

    # ==============================================================================
# --- LEDGER VAULTS MODULES ---
# ==============================================================================

@bot.hybrid_command(name="catalog", description="Public Command: Inspect card master directory records matrix")
async def catalog(ctx, page: int = 1):
    if not DATA["global_cards"]: 
        return await ctx.send("📂 Master database catalog uninitialized.")
        
    # Sort master cards from rarest to most common, and highest overall to lowest
    sorted_cards = sorted(
        DATA["global_cards"].items(), 
        key=lambda x: (RARITY_ORDER.index(x[1]["rarity"]), -x[1]["overall"])
    )
    
    per_page = 8
    max_p = max(1, (len(sorted_cards) + per_page - 1) // per_page)
    page = max(1, min(page, max_p))
    
    start_idx = (page - 1) * per_page
    end_idx = page * per_page
    
    lines = []
    for card_id, c in sorted_cards[start_idx:end_idx]:
        lines.append(f"• {c['name']} ({c['overall']} OVR) - [{c['rarity']}] | ID: `{card_id}`")
        
    embed = discord.Embed(
        title="🏒 Master Cards Blueprint Directory Catalog", 
        description="\n".join(lines), 
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Page {page}/{max_p} | Total Item Profiles: {len(sorted_cards)}")
    await ctx.send(embed=embed)


@bot.hybrid_command(name="inventory", description="Public Command: View owned personal cards vault storage")
async def inventory(ctx, player: discord.Member = None):
    t = player or ctx.author
    t_id = str(t.id)
    verify_user(t_id, t.display_name)
    
    inv = DATA["users"][t_id]["inventory"]
    valid = [c_id for c_id, count in inv.items() if count > 0 and c_id in DATA["global_cards"]]
    
    if not valid: 
        return await ctx.send(f"📂 {t.display_name} holds an empty collection.")
        
    sorted_inv = sorted(
        valid, 
        key=lambda x: (RARITY_ORDER.index(DATA["global_cards"][x]["rarity"]), -DATA["global_cards"][x]["overall"])
    )
    
    lines = []
    for c_id in sorted_inv:
        card_data = DATA["global_cards"][c_id]
        lines.append(f"• {card_data['name']} ({card_data['overall']} OVR) - [{card_data['rarity']}] x{inv[c_id]} | ID: `{c_id}`")
        
    embed = discord.Embed(
        title=f"🎒 Vault Storage: {t.display_name}", 
        description="\n".join(lines), 
        color=discord.Color.purple()
    )
    embed.add_field(name="Coins Wallet", value=f"{DATA['users'][t_id]['coins']} 🪙", inline=False)
    await ctx.send(embed=embed)

    save_data()
    await ctx.send(embed=discord.Embed(title="📅 Weekly Rewards Allocated!", description="\n".join(lines), color=discord.Color.green()))

    grouped = {r: [] for r in RARITY_ORDER}
    for c_id, c in DATA["global_cards"].items(): grouped[c["rarity"]].append(c_id)

# ==============================================================================
# --- INTERACTION TRADING MODULES ---
# ==============================================================================

class TradeView(discord.ui.View):
    def __init__(self, sender, receiver, s_card, r_card):
        super().__init__(timeout=120)
        self.sender = sender
        self.receiver = receiver
        self.s_card = s_card
        self.r_card = r_card

    @discord.ui.button(label="Accept Trade", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receiver.id: 
            return await interaction.response.send_message("❌ Target party authorization bind error.", ephemeral=True)
            
        s_id, r_id = str(self.sender.id), str(self.receiver.id)
        s_inv = DATA["users"][s_id]["inventory"]
        r_inv = DATA["users"][r_id]["inventory"]
        
        if s_inv.get(self.s_card, 0) < 1 or r_inv.get(self.r_card, 0) < 1:
            return await interaction.response.send_message("❌ Items mismatch: Assets transferred positions outside tracking blocks.", ephemeral=True)
            
        s_inv[self.s_card] -= 1
        r_inv[self.r_card] -= 1
        
        s_inv[self.r_card] = s_inv.get(self.r_card, 0) + 1
        r_inv[self.s_card] = r_inv.get(self.s_card, 0) + 1
        
        save_data()
        self.stop()
        await interaction.response.edit_message(content=f"✅ Trade Executed! Swapped items successfully between {self.sender.mention} and {self.receiver.mention}.", view=None)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in (self.sender.id, self.receiver.id): 
            return await interaction.response.send_message("❌ Access Restricted: You are not a participant in this transaction loop.", ephemeral=True)
            
        self.stop()
        await interaction.response.edit_message(content="🛑 Trade Cancelled. Propose transaction rejected.", view=None)


@bot.hybrid_command(name="trade", description="Public Command: Initiate an asset swap transaction with another user")
async def trade(ctx, target_player: discord.Member, your_card_id: str, their_card_id: str):
    if target_player == ctx.author: 
        return await ctx.send("❌ Self cycle blocked.")
        
    s_id, r_id = str(ctx.author.id), str(target_player.id)
    verify_user(s_id, ctx.author.display_name)
    verify_user(r_id, target_player.display_name)
    
    if your_card_id not in DATA["global_cards"] or their_card_id not in DATA["global_cards"]:
        return await ctx.send("❌ Error: One or both card identity ID strings do not exist.")
        
    if DATA["users"][s_id]["inventory"].get(your_card_id, 0) < 1: 
        return await ctx.send("❌ Error: You do not own that item asset identifier.")
        
    if DATA["users"][r_id]["inventory"].get(their_card_id, 0) < 1: 
        return await ctx.send("❌ Error: Target user does not own requested item asset.")
        
    view = TradeView(ctx.author, target_player, your_card_id, their_card_id)
    await ctx.send(f"🤝 {target_player.mention}, {ctx.author.mention} wants to swap their {DATA['global_cards'][your_card_id]['name']} ({your_card_id}) for your {DATA['global_cards'][their_card_id]['name']} ({their_card_id}). Do you accept?", view=view)

# ==============================================================================
# --- INTERACTION TRADING MODULES ---
# ==============================================================================

class TradeView(discord.ui.View):
    def __init__(self, sender, receiver, s_card, r_card):
        super().__init__(timeout=120)
        self.sender = sender
        self.receiver = receiver
        self.s_card = s_card
        self.r_card = r_card

    @discord.ui.button(label="Accept Trade", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receiver.id: 
            return await interaction.response.send_message("❌ Target party authorization bind error.", ephemeral=True)
            
        s_id, r_id = str(self.sender.id), str(self.receiver.id)
        s_inv = DATA["users"][s_id]["inventory"]
        r_inv = DATA["users"][r_id]["inventory"]
        
        if s_inv.get(self.s_card, 0) < 1 or r_inv.get(self.r_card, 0) < 1:
            return await interaction.response.send_message("❌ Items mismatch: Assets transferred positions outside tracking blocks.", ephemeral=True)
            
        s_inv[self.s_card] -= 1
        r_inv[self.r_card] -= 1
        
        s_inv[self.r_card] = s_inv.get(self.r_card, 0) + 1
        r_inv[self.s_card] = r_inv.get(self.s_card, 0) + 1
        
        save_data()
        self.stop()
        await interaction.response.edit_message(content=f"✅ Trade Executed! Swapped items successfully between {self.sender.mention} and {self.receiver.mention}.", view=None)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in (self.sender.id, self.receiver.id): 
            return await interaction.response.send_message("❌ Access Restricted: You are not a participant in this transaction loop.", ephemeral=True)
            
        self.stop()
        await interaction.response.edit_message(content="🛑 Trade Cancelled. Propose transaction rejected.", view=None)

# ==============================================================================
# --- STAFF CONFIGURATION & REWARD ADMINISTRATIVE UTILITIES ---
# ==============================================================================

@bot.hybrid_command(name="editmatchreward", description="Staff Command: Calibrate the global currency payout size awarded to winning teams")
@is_staff()
async def editmatchreward(ctx, new_reward: int):
    DATA["config"]["match_reward"] = max(0, new_reward)
    save_data()
    await ctx.send(f"🪙 **Match Payout Settings Saved!** Future match series victories will award `{new_reward}` coins per player.")

# ==============================================================================
# --- FINAL UNIVERSAL NEATQUEUE MULTI-LAYER SCRAPER ENGINE ---
# ==============================================================================

@bot.event
async def on_message_edit(before, after):
    # 1. Ignore if the message wasn't sent by NeatQueue
    if after.author.id != 857633321064595466 and after.author.name != "NeatQueue":
        return

    # 2. Check if the updated message contains embeds
    if after.embeds:
        embed = after.embeds[0]
        
        # 3. Verify it changed from an open queue into a winner result card
        if embed.title and "Winner For Queue" in embed.title:
            
            # Use the unique match number in the title (like Queue#2815) to prevent double payouts
            match_id_match = re.search(r"(Queue#\d+)", embed.title)
            match_unique_id = match_id_match.group(1) if match_id_match else str(after.id)
            
            if "processed_neatque_matches" not in DATA:
                DATA["processed_neatque_matches"] = []
                
            if match_unique_id in DATA["processed_neatque_matches"]:
                return # Match already paid out, skip it

            # Extract the embedded text blocks
            text_to_scan = embed.description or ""
            if not text_to_scan and embed.fields:
                text_to_scan = "\n".join([f"{f.name} {f.value}" for f in embed.fields])
                
            lines = text_to_scan.split("\n")
            
            winning_user_ids = []
            losing_user_ids = []
            
            # 4. Scan line by line to locate user mentions and score signs (+/- followed by a number)
            for line in lines:
                match_user = re.search(r"<@!?(\d+)>", line)
                if match_user:
                    user_id_str = match_user.group(1)
                    
                    # Target explicit positive values (like +1, +31.2, +50, etc.)
                    if re.search(r"\+\d+", line):
                        winning_user_ids.append(user_id_str)
                    # Target explicit negative values (like -14.8, -16.0, etc.)
                    elif re.search(r"-\d+", line):
                        losing_user_ids.append(user_id_str)
            
            # 5. Distribute coins if winners are found
            if winning_user_ids:
                reward_amount = DATA["config"].get("match_reward", 50)
                awarded_mentions = []
                
                for p_id in winning_user_ids:
                    verify_user(p_id, f"User {p_id}")
                    DATA["users"][p_id]["coins"] += reward_amount
                    DATA["users"][p_id]["wins"] += 1
                    awarded_mentions.append(f"<@{p_id}>")
                    
                for p_id in losing_user_ids:
                    verify_user(p_id, f"User {p_id}")
                    DATA["users"][p_id]["losses"] += 1
                
                # Lock this match ID so it can never be processed again
                DATA["processed_neatque_matches"].append(match_unique_id)
                
                # Push modifications to your local JSON and GitHub database
                save_data()
                
                # Post validation details back to the queue channel
                               # Post validation details back to the queue channel safely
                if awarded_mentions:
                    try:
                        await after.channel.send(
                            f"🪙 **NeatQueue Edit Link Synced!** Match results registered.\n"
                            f"The following winners have been credited with **{reward_amount} coins**: "
                            f"{', '.join(awarded_mentions)}"
                        )
                    except discord.errors.Forbidden:
                        print(f"⚠️ Missing Permissions: Could not send success message in #{after.channel.name}, but coins were successfully saved to the cloud!")


# --- Start Services ---
# ==============================================================================
# --- BOT RUNNER EXECUTOR (THE VERY BOTTOM OF YOUR FILE) ---
# ==============================================================================

# 1. Start the Flask keep-alive web server
keep_alive()

# 2. CRITICAL SYNC: Load your database BEFORE logging into Discord
# This prevents requests.get from freezing your live Discord gateway session
load_data()

# 3. Launch the primary bot client thread instance safely
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ Critical System Initialization Fault: 'DISCORD_TOKEN' environment key is blank.")



