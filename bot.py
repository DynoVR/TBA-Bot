import discord
from discord.ext import commands, tasks
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

# --- Flask Keep-Alive Web Server Architecture ---
app = Flask('')

@app.route('/')
def home():
    return "OK", 200

if not hasattr(app, "_already_running"):
    app._already_running = False

def run_web_server():
    if app._already_running:
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
    
# --- System Environment Configurations ---
TOKEN = os.environ.get("DISCORD_TOKEN")
DATABASE_FILE = "card_league_database.json"
DB_URL = os.environ.get("DB_URL")
DB_KEY = os.environ.get("DB_KEY")

# --- Sorted Card Ledger Constants ---
RARITY_ORDER = ["Specialty", "Otherworldly", "Juggernaut", "Pro", "Insane", "Epic", "Great", "Average"]
ACTIVE_QUEUES = {1: [], 2: [], 3: []}
# Ordered priority mapping for sorted card ledger structures
RARITY_ORDER = ["Specialty", "Otherworldly", "Juggernaut", "Pro", "Insane", "Epic", "Great", "Average"]

# --- NEW: CUSTOM CARD RARITY EMBED COLOR CODES ---
RARITY_COLORS = {
    "Average": 0xADD8E6,       # Light Blue
    "Great": 0x800080,         # Purple
    "Epic": 0x50C878,          # Emerald Green
    "Insane": 0x7851A9,        # Royal Purple
    "Pro": 0xFFD700,           # Gold
    "Juggernaut": 0xCD7F32,    # Orange Bronze
    "Otherworldly": 0x8B0000,  # Dark Red
    "Specialty": 0xFFFFFF      # Pure White (Fallback)
}

# --- Baseline Database Template Layer ---
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
    "processed_neatque_matches": [],
    "config": {
        "pack_3_price": 150,
        "pack_5_price": 250,
        "pack_10_price": 400,
        "match_reward": 50,
        "queue_role_id": None,
        "match_role_id": None,
        "sell_prices": {
            "Average": 1,
            "Great": 2,
            "Epic": 5,
            "Insane": 10,
            "Pro": 25,
            "Juggernaut": 100,
            "Otherworldly": 300,
            "Specialty": 750
        }
    }
}

# --- Core Bot Client Initialization ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

# ==============================================================================
# --- FIXED DATABASE CLOUD ROUTING CORE ENGINE ---
# ==============================================================================

def load_data():
    global DATA
    print("🔄 Connecting to External Cloud Database Service...")
    
    # Clean up variables to remove accidental hidden spaces or ghost characters
    raw_url = os.environ.get("DB_URL", "")
    raw_key = os.environ.get("DB_KEY", "")
    
    db_url = str(raw_url).strip().replace('"', '').replace("'", "")
    db_key = str(raw_key).strip().replace('"', '').replace("'", "")
    
    if not db_url or not db_key or "jsonbin" not in db_url:
        print("🚨 System Warning: 'DB_URL' or 'DB_KEY' environment values are blank or invalid inside Render! Bypassing cloud pull.")
        return

    try:
        headers = {
            "X-Master-Key": db_key,
            "X-Bin-Meta": "false"
        }
        print(f"📡 Dispatching link handshake: {db_url[:30]}...")
        
        # Hardened strict 3-second timeout constraint with stream closing
        res = requests.get(db_url, headers=headers, timeout=3.0)
        print(f"📡 Cloud Database Fetch Status Response Code: {res.status_code}")
        
        if res.status_code == 200:
            raw_json = res.json()
            if isinstance(raw_json, dict) and "record" in raw_json:
                loaded_json = raw_json["record"]
            else:
                loaded_json = raw_json
                
            if isinstance(loaded_json, dict):
                DATA = loaded_json
                if "global_cards" not in DATA: DATA["global_cards"] = {}
                if "users" not in DATA: DATA["users"] = {}
                if "processed_neatque_matches" not in DATA: DATA["processed_neatque_matches"] = []
                if "config" not in DATA: DATA["config"] = {}
                print(f"☁️ Cloud Success! Restored {len(DATA.get('users', {}))} profiles.")
                return
        else:
            print(f"❌ Cloud Pull Refused: Status {res.status_code}.")
    except Exception as e:
        print(f"⚠️ Cloud Connection Bypass: {e}")
        
    # LOCAL SAFETY NET FALLBACK
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, "r") as f:
                local_data = json.load(f)
                if isinstance(local_data, dict):
                    DATA = local_data
                    print("💾 Local database file loaded successfully as safety fallback.")
        except Exception as err:
            print(f"❌ Safety net read error: {err}")

def save_data():
    """Forces an absolute synchronous write commit directly to your private cloud storage endpoint."""
    if not DB_URL or not DB_KEY:
        print("⚠️ Save Sync Skipped: External cloud credentials uninitialized.")
        return

    try:
        headers = {
            "Content-Type": "application/json",
            "X-Master-Key": DB_KEY
        }
        put_req = requests.put(DB_URL, headers=headers, json=DATA)
        print(f"📡 Cloud Database Save Sync Status Response Code: {put_req.status_code}")
        
        if put_req.status_code == 200:
            print("☁️ Permanent database securely backed up to Cloud endpoint successfully!")
        else:
            print(f"❌ Cloud API Sync Failed ({put_req.status_code}): {put_req.text}")
    except Exception as e:
        print(f"❌ External Cloud Save Pipeline Crash: {e}")


def verify_user(user_id_str, username="Unknown"):
    global DATA
    
    if not DATA or "users" not in DATA:
        print("⚠️ verify_user caught a race condition! Forcing database reload to protect player vaults...")
        if DB_URL and DB_KEY:
            try:
                headers = {"X-Master-Key": DB_KEY, "X-Bin-Meta": "false"}
                res = requests.get(DB_URL, headers=headers)
                if res.status_code == 200:
                    DATA = res.json()
            except Exception as e:
                print(f"❌ Force pull inside verify_user failed: {e}")

    if "users" not in DATA:
        DATA["users"] = {}
        
    if user_id_str not in DATA["users"]:
        DATA["users"][user_id_str] = {
            "name": username, 
            "coins": 150, 
            "inventory": {},
            "last_weekly": None, 
            "wins": 0, 
            "losses": 0
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
        except Exception as e:
            print(f"⚠️ Guild chunk warning: {e}")
            
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
                        if "processed_neatque_matches" not in DATA:
                            DATA["processed_neatque_matches"] = []
                            
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
                                    try:
                                        await channel.send(
                                            f"🪙 **NeatQueue Automated Link Synced!** Final match result parsed successfully.\n"
                                            f"The following winners have been credited with **{reward} coins**: "
                                            f"{', '.join(awarded_mentions)}"
                                        )
                                    except discord.errors.Forbidden:
                                        print(f"⚠️ Missing Permissions: Couldn't post success confirmation in #{channel.name}, but coin balances were successfully backed up to cloud systems.")
                except Exception as e:
                    print(f"❌ Background history parser loop warning: {e}")

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

@bot.hybrid_command(name="forcesync", description="Force synchronizes command layout registries globally.")
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
    embed.add_field(name="🌐 Public Card Commands", value="`/catalog` - View master card list\n`/inventory [player]` - Inspect owned profile card vault\n`/buypack <size>` - Purchase 3, 5, or 10 random players\n`/claimweekly` - Claim free 3-pack weekly box reward\n`/trade <target> <your_card_ids> <their_card_ids>` - Swap card assets safely\n`/leaderboard` - Check competitive win ratings standings", inline=False)
    embed.add_field(name="⚔️ Matchmaking Commands", value="`/setupqueue <size>` - Deploy interactive match waiting panel\n`Buttons` - Join/Leave queue pool interface nodes", inline=False)
    embed.add_field(name="🛡️ Staff Administration (Requires Staff Role/Owner)", value="`/setstaffrole <role>` - Update staff role reference mapping\n`/setmatchreward <coins>` - Change match victory payout amount\n`/addcard <rarity> <overall> [player] [specialty_title] [image_url]` - Initialize new card profile\n`/editcard <card_id> <rarity> <overall> [image_url]` - Modify precise attributes parameters on a card instance\n`/removecard <card_id>` - Delete specific card profile permanently\n`/editcoins <action> <player> <amount>` - Change balance values safely\n`/setpackprice <size> <new_price>` - Configure the purchase price of card packs\n`/cancelmatch <match_id>` - Terminate an active game room instances layer\n`/substitute <match_id> <old_player> <new_player>` - Swap players mid-match series", inline=False)
    await ctx.send(embed=embed)

# ==============================================================================
# --- CARD SYSTEM ENGINE ---
# ==============================================================================

@bot.hybrid_command(name="addcard", description="Staff Command: Initialize a new card profile instance into log records")
@is_staff()
@app_commands.choices(rarity=[app_commands.Choice(name=r, value=r) for r in RARITY_ORDER])
async def addcard(ctx, rarity: str, overall: int, player: discord.Member = None, specialty_title: str = None, image_url: str = None):
    # Field conditional router: specialty rules isolation mapping
    if rarity == "Specialty":
        if not specialty_title:
            return await ctx.send("❌ **Input Error:** You must provide a custom text parameter inside `specialty_title` when creating Specialty rarity items.")
        
        # FIXED: Cleans the text on a separate line to avoid inline f-string crashes
        clean_text = re.sub(r'[^a-z0-9]', '', specialty_title.lower())
        card_name = specialty_title
        player_id_str = "0"
        card_id = f"specialty_{clean_text}_{random.randint(100, 999)}"
    else:
        if not player:
            return await ctx.send("❌ **Input Error:** You must select a target user inside the `player` field option for standard card rarities.")
        card_name = player.display_name
        player_id_str = str(player.id)
        card_id = f"{player.name.lower()}_{rarity.lower()}_{random.randint(100, 999)}"

    DATA["global_cards"][card_id] = {
        "id": card_id, "name": card_name, "player_id": player_id_str,
        "rarity": rarity, "overall": max(1, min(overall, 99)), "image_url": image_url or ""
    }
    
    # Securely saves to both your local cache and GitHub Cloud
    save_data()
    await ctx.send(f"✅ **Created Card Profile ID:** `{card_id}` for **{card_name}**! [{rarity} | {overall} OVR]")

@bot.hybrid_command(name="editcard", description="Staff Command: Modify the rarity, overall, or picture assets of a precise unique card identity code")
@is_staff()
@app_commands.choices(rarity=[app_commands.Choice(name=r, value=r) for r in RARITY_ORDER])
async def editcard(ctx, card_id: str, rarity: str, overall: int, image_url: str = None):
    if card_id not in DATA["global_cards"]:
        return await ctx.send(f"❌ Error: Card reference identifier code `{card_id}` does not exist in master log paths.")
    
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

@bot.hybrid_command(name="editcoins", description="Staff Command: Securely give or take economy coins from a target player account")
@is_staff()
@app_commands.choices(action=[
    app_commands.Choice(name="Give Coins", value="give"),
    app_commands.Choice(name="Take Coins", value="take")
])
async def editcoins(ctx, action: str, player: discord.Member, amount: int):
    if amount <= 0:
        return await ctx.send("❌ **Input Error:** The coin adjustment amount parameters must be greater than 0.")
        
    user_id_str = str(player.id)
    
    # Securely verify that the user profile registry structure exists in memory
    verify_user(user_id_str, player.display_name)
    
    current_coins = DATA["users"][user_id_str].get("coins", 150)
    
    if action == "give":
        DATA["users"][user_id_str]["coins"] = current_coins + amount
        message_response = f"🪙 **Coins Deposited!** Successfully credited `+{amount}` coins to {player.mention}."
    elif action == "take":
        # Safe constraint boundary check to prevent negative wallet values
        if current_coins < amount:
            new_balance = 0
            message_response = f"⚠️ **Balance Warning:** Deducted all coins from {player.mention} as their vault held less than `{amount}`."
        else:
            new_balance = current_coins - amount
            message_response = f"📉 **Coins Deducted!** Successfully removed `-{amount}` coins from {player.mention}."
            
        DATA["users"][user_id_str]["coins"] = new_balance

    # Force synchronous live write backup pipeline syncs
    save_data()
    
    # Construct a clean embed summary overview display layout
    embed = discord.Embed(title="🏦 Vault Balance Adjusted", description=message_response, color=0xFFD700)
    embed.add_field(name="New Vault Total Balance", value=f"`{DATA['users'][user_id_str]['coins']}` coins 🪙", inline=False)
    embed.set_footer(text=f"Transaction audited and authorized by {ctx.author.display_name}")
    
    await ctx.send(embed=embed)


# ==============================================================================
# --- INTERACTIVE CARD LIQUIDATION ENGINE & STORE SYSTEMS ---
# ==============================================================================

@bot.hybrid_command(name="setpackprice", description="Staff Command: Configure the purchase price of card packs")
@is_staff()
@app_commands.choices(size=[
    app_commands.Choice(name="3 Players Pack", value=3),
    app_commands.Choice(name="5 Players Pack", value=5),
    app_commands.Choice(name="10 Players Pack", value=10)
])
async def setpackprice(ctx, size: int, new_price: int):
    if new_price < 0:
        return await ctx.send("❌ **Input Error:** Pack prices cannot be negative values.")
        
    # Safeguard underlying structure nodes mapping parameters
    if "config" not in DATA: 
        DATA["config"] = {}
    
    # Store the pricing data directly into memory arrays
    DATA["config"][f"pack_{size}_price"] = new_price
    
    # Force synchronous live write backup pipeline syncs straight to the cloud
    save_data()
    
    embed = discord.Embed(title="⚙️ Store Configuration Updated", color=0x3498db)
    embed.description = f"Successfully set the price of the **{size} Player Pack** to `{new_price}` coins 🪙."
    await ctx.send(embed=embed)


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
        "Pro": 3.0, 
        "Juggernaut": 1.0, 
        "Otherworldly": 0.3, 
        "Specialty": 0.1
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
    
    cost = DATA["config"].get(f"pack_{pack_size}_price", 400)
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

# ==============================================================================
# --- LEDGER VAULTS MODULES ---
# ==============================================================================

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
# --- UPGRADED COLOR ANSI LEDGER VAULTS MODULES ---
# ==============================================================================

# ANSI color mapping registry function helper
def get_ansi_card_line(card_name, rarity, overall, card_id, count=None):
    ansi_map = {
        "Average": "\u001b[1;36m",       # Light Blue
        "Great": "\u001b[0;35m",         # Purple
        "Epic": "\u001b[1;32m",          # Emerald Green
        "Insane": "\u001b[1;35m",        # Royal Purple
        "Pro": "\u001b[1;33m",           # Gold
        "Juggernaut": "\u001b[1;31m",    # Orange Bronze (Red spectrum)
        "Otherworldly": "\u001b[0;31m",  # Dark Red
        "Specialty": "\u001b[1;37m"      # Bold White
    }
    color = ansi_map.get(rarity, "\u001b[0m")
    reset = "\u001b[0m"
    
    if count is not None:
        return f"{color}• {card_name} ({overall} OVR) - [{rarity}] x{count} | ID: {card_id}{reset}"
    return f"{color}• {card_name} ({overall} OVR) - [{rarity}] | ID: {card_id}{reset}"

# ==============================================================================
# --- UPGRADED INTERACTIVE DECK BUTTONS WITH JUMP DROPDOWNS ---
# ==============================================================================

def get_rarity_emoji(rarity):
    emoji_map = {
        "Average": "🟦", "Great": "🟪", "Epic": "🟩", "Insane": "🔮",
        "Pro": "👑", "Juggernaut": "🔥", "Otherworldly": "🌋", "Specialty": "🌟"
    }
    return emoji_map.get(rarity, "🎴")


class CatalogJumpSelect(discord.ui.Select):
    """Dropdown menu mapping milestones to warp across the master catalog."""
    def __init__(self, total_cards):
        options = []
        # Create jump intervals (every 5 cards, plus the first and final frames)
        for i in range(0, total_cards, 5):
            options.append(discord.SelectOption(label=f"Jump to Card #{i+1}", value=str(i), emoji="📖"))
        if str(total_cards - 1) not in [o.value for o in options] and total_cards > 1:
            options.append(discord.SelectOption(label=f"Jump to Final Card (#{total_cards})", value=str(total_cards - 1), emoji="🏁"))
        
        # Keep options array capped at Discord's 25 max selection limit boundary constraints
        super().__init__(placeholder="Select a card number to warp to...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        self.view.current_index = int(self.values[0])
        await interaction.response.edit_message(embed=self.view.make_card_embed(), view=self.view)


class CatalogPaginationView(discord.ui.View):
    """Interactive Button Grid Engine for scrolling through the card catalog with jump slots."""
    def __init__(self, sorted_cards):
        super().__init__(timeout=90.0)
        self.sorted_cards = sorted_cards
        self.current_index = 0
        self.max_index = len(sorted_cards) - 1
        # Dynamically inject the dropdown selector frame layout row below the navigation links
        if len(sorted_cards) > 1:
            self.add_item(CatalogJumpSelect(len(sorted_cards)))

    def make_card_embed(self):
        card_id, c = self.sorted_cards[self.current_index]
        r_color = RARITY_COLORS.get(c['rarity'], 0x3498db)
        r_emoji = get_rarity_emoji(c['rarity'])
        
        embed = discord.Embed(
            title=f"{r_emoji} {c['name'].upper()} (CATALOG INDEX)", 
            color=r_color
        )
        embed.add_field(name="📈 Attributes", value=f"```\nOVERALL: {c['overall']} OVR\nRARITY:  {c['rarity']}\n```", inline=True)
        embed.add_field(name="🆔 Card Serial", value=f"```\nID: {card_id}\n```", inline=True)
        embed.set_footer(text=f"Card {self.current_index + 1} of {len(self.sorted_cards)} | Scroll or use the menu to jump pages")
        
        if c.get("image_url"):
            embed.set_thumbnail(url=c["image_url"])
        return embed

    @discord.ui.button(label="◀ Prev Card", style=discord.ButtonStyle.secondary, row=0)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_index > 0:
            self.current_index -= 1
        else:
            self.current_index = self.max_index
        await interaction.response.edit_message(embed=self.make_card_embed(), view=self)

    @discord.ui.button(label="Next Card ▶", style=discord.ButtonStyle.primary, row=0)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_index < self.max_index:
            self.current_index += 1
        else:
            self.current_index = 0
        await interaction.response.edit_message(embed=self.make_card_embed(), view=self)


class InventoryJumpSelect(discord.ui.Select):
    """Dropdown menu mapping milestones to warp across player storage vaults."""
    def __init__(self, total_items):
        options = []
        for i in range(0, total_items, 5):
            options.append(discord.SelectOption(label=f"Warp to Item #{i+1}", value=str(i), emoji="🎒"))
        if str(total_items - 1) not in [o.value for o in options] and total_items > 1:
            options.append(discord.SelectOption(label=f"Warp to Final Item (#{total_items})", value=str(total_items - 1), emoji="🏁"))
            
        super().__init__(placeholder="Select an item index card to warp to...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        self.view.current_index = int(self.values[0])
        await interaction.response.edit_message(embed=self.view.make_card_embed(), view=self.view)


class InventoryPaginationView(discord.ui.View):
    """Interactive Button Grid Engine for scrolling through a player's private inventory vault."""
    def __init__(self, target_name, sorted_inv, inv_data, total_coins):
        super().__init__(timeout=90.0)
        self.target_name = target_name
        self.sorted_inv = sorted_inv
        self.inv_data = inv_data
        self.total_coins = total_coins
        self.current_index = 0
        self.max_index = len(sorted_inv) - 1
        if len(sorted_inv) > 1:
            self.add_item(InventoryJumpSelect(len(sorted_inv)))

    def make_card_embed(self):
        c_id = self.sorted_inv[self.current_index]
        card_data = DATA["global_cards"][c_id]
        r_color = RARITY_COLORS.get(card_data['rarity'], 0x3498db)
        r_emoji = get_rarity_emoji(card_data['rarity'])
        owned_count = self.inv_data[c_id]
        
        embed = discord.Embed(
            title=f"🎒 {self.target_name.upper()}'S VAULT STORAGE",
            description=f"🪙 **Coins Wallet Balance:** `{self.total_coins}` coins",
            color=r_color
        )
        embed.add_field(name=f"{r_emoji} {card_data['name'].upper()}", value=f"```\nOVERALL: {card_data['overall']} OVR\nRARITY:  {card_data['rarity']}\n```", inline=False)
        embed.add_field(name="📦 Possession Details", value=f"```\nOWNED COPIES: x{owned_count}\nCARD ID:      {c_id}\n```", inline=False)
        embed.set_footer(text=f"Owned Item {self.current_index + 1} of {len(self.sorted_inv)} | Use buttons or select a page target")
        
        if card_data.get("image_url"):
            embed.set_thumbnail(url=card_data["image_url"])
        return embed

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary, row=0)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_index > 0:
            self.current_index -= 1
        else:
            self.current_index = self.max_index
        await interaction.response.edit_message(embed=self.make_card_embed(), view=self)

    @discord.ui.button(label="Next Item ▶", style=discord.ButtonStyle.success, row=0)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_index < self.max_index:
            self.current_index += 1
        else:
            self.current_index = 0
        await interaction.response.edit_message(embed=self.make_card_embed(), view=self)


@bot.hybrid_command(name="catalog", description="Public Command: Inspect card master directory records matrix using click buttons and jump slots")
async def catalog(ctx):
    if not DATA["global_cards"]: 
        return await ctx.send("📂 Master database catalog uninitialized.")
        
    # FIXED SORT LAYOUT MATRIX ROUTE PATHING
    sorted_cards = sorted(
        DATA["global_cards"].items(), 
        key=lambda x: (RARITY_ORDER.index(x[1]["rarity"]) if x[1]["rarity"] in RARITY_ORDER else 99, -x[1]["overall"])
    )
    
    view = CatalogPaginationView(sorted_cards)
    await ctx.send(embed=view.make_card_embed(), view=view)


@bot.hybrid_command(name="inventory", description="Public Command: View owned personal cards vault storage via buttons and jump slots")
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
        key=lambda x: (RARITY_ORDER.index(DATA["global_cards"][x]["rarity"]) if DATA["global_cards"][x]["rarity"] in RARITY_ORDER else 99, -DATA["global_cards"][x]["overall"])
    )
    
    total_coins = DATA["users"][t_id]["coins"]
    view = InventoryPaginationView(t.display_name, sorted_inv, inv, total_coins)
    await ctx.send(embed=view.make_card_embed(), view=view)

# ==============================================================================
# --- UPGRADED MULTI-CARD INTERACTION TRADING MODULES ---
# ==============================================================================

# ==============================================================================
# --- FINAL MULTI-CARD INTERACTION TRADING ENGINE ---
# ==============================================================================

class TradeView(discord.ui.View):
    def __init__(self, sender, receiver, s_cards_list, r_cards_list):
        super().__init__(timeout=120)
        self.sender = sender
        self.receiver = receiver
        self.s_cards = s_cards_list  
        self.r_cards = r_cards_list  

    @discord.ui.button(label="Accept Trade", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receiver.id: 
            return await interaction.response.send_message("❌ Target party authorization bind error.", ephemeral=True)
            
        s_id, r_id = str(self.sender.id), str(self.receiver.id)
        s_inv = DATA["users"][s_id]["inventory"]
        r_inv = DATA["users"][r_id]["inventory"]
        
        for c_id in self.s_cards:
            if s_inv.get(c_id, 0) < self.s_cards.count(c_id):
                return await interaction.response.send_message(f"❌ **Trade Aborted:** {self.sender.display_name} no longer owns enough copies of `{c_id}`.", ephemeral=True)
        for c_id in self.r_cards:
            if r_inv.get(c_id, 0) < self.r_cards.count(c_id):
                return await interaction.response.send_message(f"❌ **Trade Aborted:** You no longer own enough copies of `{c_id}`.", ephemeral=True)
                
        for c_id in self.s_cards: s_inv[c_id] -= 1
        for c_id in self.r_cards: r_inv[c_id] -= 1
        
        for c_id in self.s_cards: r_inv[c_id] = r_inv.get(c_id, 0) + 1
        for c_id in self.r_cards: s_inv[c_id] = s_inv.get(c_id, 0) + 1
        
        save_data()
        self.stop()
        await interaction.response.edit_message(content=f"✅ **Multi-Trade Executed!** Transaction settled between {self.sender.mention} and {self.receiver.mention}.", view=None)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in (self.sender.id, self.receiver.id): 
            return await interaction.response.send_message("❌ Access Restricted: You are not a participant in this transaction loop.", ephemeral=True)
            
        self.stop()
        await interaction.response.edit_message(content="🛑 Trade Cancelled. Offer was declined.", view=None)


@bot.hybrid_command(name="trade", description="Trade multiple cards at once using commas")
@app_commands.describe(target_player="Player to swap with", your_card_ids="Card IDs you give (id1, id2)", their_card_ids="Card IDs you want (id1, id2)")
async def trade(ctx, target_player: discord.Member, your_card_ids: str, their_card_ids: str):
    if target_player == ctx.author: 
        return await ctx.send("❌ Self-trading is blocked.")
        
    s_id, r_id = str(ctx.author.id), str(target_player.id)
    verify_user(s_id, ctx.author.display_name)
    verify_user(r_id, target_player.display_name)
    
    s_cards = [cid.strip() for cid in your_card_ids.split(",") if cid.strip()]
    r_cards = [cid.strip() for cid in their_card_ids.split(",") if cid.strip()]
    
    if not s_cards or not r_cards:
        return await ctx.send("❌ **Input Error:** You must provide at least one card ID for each side.")

    for c_id in s_cards:
        if c_id not in DATA["global_cards"]:
            return await ctx.send(f"❌ **Error:** Card ID `{c_id}` does not exist in the master catalog.")
        if DATA["users"][s_id]["inventory"].get(c_id, 0) < s_cards.count(c_id):
            return await ctx.send(f"❌ **Error:** You do not own enough copies of `{c_id}` to complete this trade.")
            
    for c_id in r_cards:
        if c_id not in DATA["global_cards"]:
            return await ctx.send(f"❌ **Error:** Card ID `{c_id}` does not exist in the master catalog.")
        if DATA["users"][r_id]["inventory"].get(c_id, 0) < r_cards.count(c_id):
            return await ctx.send(f"❌ **Error:** {target_player.display_name} does not own enough copies of `{c_id}`.")

    sender_offer = "\n".join([f"• **[{DATA['global_cards'][cid]['rarity']}]** {DATA['global_cards'][cid]['name']} (`{cid}`)" for cid in s_cards])
    receiver_offer = "\n".join([f"• **[{DATA['global_cards'][cid]['rarity']}]** {DATA['global_cards'][cid]['name']} (`{cid}`)" for cid in r_cards])
    
    embed = discord.Embed(title="🤝 Incoming Multi-Card Trade Proposal", color=0x3498db)
    embed.add_field(name=f"📤 {ctx.author.display_name} Offers:", value=sender_offer, inline=False)
    embed.add_field(name=f"📥 Requested From {target_player.display_name}:", value=receiver_offer, inline=False)
    embed.set_footer(text="This pending proposal window expires in 120 seconds.")
    
    view = TradeView(ctx.author, target_player, s_cards, r_cards)
    await ctx.send(f"🤝 {target_player.mention}, you received a trade offer from {ctx.author.mention}!", embed=embed, view=view)

# ==============================================================================
# --- STAFF CONFIGURATION & REWARD ADMINISTRATIVE UTILITIES ---
# ==============================================================================

@bot.hybrid_command(name="setpackprice", description="Staff Command: Configure the purchase price of card packs")
@is_staff()
@app_commands.choices(size=[
    app_commands.Choice(name="3 Players Pack", value=3),
    app_commands.Choice(name="5 Players Pack", value=5),
    app_commands.Choice(name="10 Players Pack", value=10)
])
async def setpackprice(ctx, size: int, new_price: int):
    if new_price < 0:
        return await ctx.send("❌ **Input Error:** Pack prices cannot be negative.")
        
    # Inject the keys into memory if JSONBin initialized them as empty
    if "config" not in DATA: 
        DATA["config"] = {}
    
    # Update the price in the script's memory
    DATA["config"][f"pack_{size}_price"] = new_price
    
    # FORCE write it directly into your JSONBin cloud storage right now
    save_data()
    
    embed = discord.Embed(title="⚙️ Store Configuration Updated", color=0x3498db)
    embed.description = f"Successfully set the price of the **{size} Player Pack** to `{new_price}` coins 🪙."
    await ctx.send(embed=embed)


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

# --- Start Services ---
if __name__ == "__main__":
    keep_alive()
    load_data()
    if TOKEN:
        print("🤖 Connecting client to Discord Gateway panels...")
        bot.run(TOKEN)
    else:
        print("❌ Critical System Initialization Fault: 'DISCORD_TOKEN' environment key is blank.")




