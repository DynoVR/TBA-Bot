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
        "wheel_Bronze_price": 100,
        "wheel_Silver_price": 250,
        "wheel_Gold_price": 500,
        "match_reward": 50,
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
        if DB_URL and DB_KEY:
            try:
                headers = {"X-Master-Key": DB_KEY, "X-Bin-Meta": "false"}
                res = requests.get(DB_URL, headers=headers)
                if res.status_code == 200: DATA = res.json()
            except Exception as e: print(f"❌ Force pull inside verify_user failed: {e}")

    if "users" not in DATA: DATA["users"] = {}
    if user_id_str not in DATA["users"]:
        DATA["users"][user_id_str] = {
            "name": username, "coins": 150, "inventory": {}, "card_cooldowns": {},
            "last_weekly": None, "last_cpu_boss": None, "wins": 0, "losses": 0
        }
    elif "last_cpu_boss" not in DATA["users"][user_id_str]:
        DATA["users"][user_id_str]["last_cpu_boss"] = None

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
    
    embed.add_field(name="🌐 Public Card Commands", value=(
        "`/catalog` - View master card list directory with scroll pages\n"
        "`/inventory [player]` - Inspect owned profile card vault and coin balance\n"
        "`/buypack <size>` - Purchase random card player packs from the shop\n"
        "`/claimweekly` - Claim your free weekly starter card box reward\n"
        "`/trade <target>` - Open the visual multi-card interactive trade deck\n"
        "`/challenge <opponent> <wager>` - Issue a 3v3 hidden card arena duel stake"
    ), inline=False)
    
    embed.add_field(name="🛡️ Staff Administration (Requires Staff Role/Owner)", value=(
        "`/setstaffrole <role>` - Update staff role reference permissions mapping\n"
        "`/setmatchreward <coins>` - Change standard match victory payout amount\n"
        "`/addcard <rarity> <overall> [player] [specialty_title] [image_url]` - Create a new card template\n"
        "`/editcard <card_id> <rarity> <overall> [image_url]` - Modify existing card stats parameters\n"
        "`/removecard <card_id>` - Delete a specific card profile permanently from records\n"
        "`/editcoins <action> <player> <amount>` - Safely give or take coins from wallets\n"
        "`/setpackprice <size> <new_price>` - Configure the store purchase cost of card packs"
    ), inline=False)
    
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
        # 1. Defer immediately to prevent "Interaction Failed" for slash commands
        await ctx.defer()
    
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
        
        # 2. Build and send the final response listing the pulled cards
        response_text = f"🎉 **{ctx.author.display_name}**, you claimed your weekly package!\n\n" + "\n".join(lines)
        await ctx.send(response_text)
    
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
    # FIXED: Defers the response instantly to prevent the 3-second timeout crash
    await ctx.defer()
    
    if not DATA["global_cards"]: 
        return await ctx.send("📂 Master database catalog uninitialized.")
        
    sorted_cards = sorted(
        DATA["global_cards"].items(), 
        key=lambda x: (RARITY_ORDER.index(x[1]["rarity"]) if x[1]["rarity"] in RARITY_ORDER else 99, -x[1]["overall"])
    )
    
    view = CatalogPaginationView(sorted_cards)
    # Use followups/context send safely after deferrals
    await ctx.send(embed=view.make_card_embed(), view=view)


@bot.hybrid_command(name="inventory", description="Public Command: View owned personal cards vault storage via buttons and jump slots")
async def inventory(ctx, player: discord.Member = None):
    # FIXED: Defers the response instantly to prevent the 3-second timeout crash
    await ctx.defer()
    
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
# --- ADVANCED INTERACTIVE MULTI-CARD SELECTION TRADING GRID ---
# ==============================================================================

class SenderCardSelect(discord.ui.Select):
    """Dropdown menu listing the sender's cards to add to the offer."""
    def __init__(self, sender_id, valid_cards):
        options = []
        for cid, card, count in valid_cards[:25]:  # Discord caps selection options at 25 items max
            options.append(discord.SelectOption(
                label=f"{card['name']} ({card['overall']} OVR)",
                description=f"Rarity: {card['rarity']} | Owned: x{count} | ID: {cid}",
                value=cid,
                emoji="📤"
            ))
        super().__init__(placeholder="➕ Select cards from YOUR vault to OFFER...", min_values=1, max_values=min(5, len(options) if options else 1), options=options if options else [discord.SelectOption(label="No cards available", value="none")])

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.sender.id:
            return await interaction.response.send_message("❌ You are not the initiator of this trade offer.", ephemeral=True)
        if "none" in self.values:
            return await interaction.response.defer()
            
        self.view.s_offered_cards = self.values
        await self.view.update_trade_display(interaction)


class ReceiverCardSelect(discord.ui.Select):
    """Dropdown menu listing the receiver's cards to request."""
    def __init__(self, receiver_id, valid_cards):
        options = []
        for cid, card, count in valid_cards[:25]:
            options.append(discord.SelectOption(
                label=f"{card['name']} ({card['overall']} OVR)",
                description=f"Rarity: {card['rarity']} | Owned: x{count} | ID: {cid}",
                value=cid,
                emoji="📥"
            ))
        super().__init__(placeholder="➕ Select cards from THEIR vault to REQUEST...", min_values=1, max_values=min(5, len(options) if options else 1), options=options if options else [discord.SelectOption(label="No cards available", value="none")])

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.sender.id:
            return await interaction.response.send_message("❌ You are not the initiator of this trade offer.", ephemeral=True)
        if "none" in self.values:
            return await interaction.response.defer()
            
        self.view.r_requested_cards = self.values
        await self.view.update_trade_display(interaction)


class AdvancedTradeView(discord.ui.View):
    def __init__(self, sender, receiver, sender_cards, receiver_cards):
        super().__init__(timeout=180.0)
        self.sender = sender
        self.receiver = receiver
        self.s_offered_cards = []   # Keeps track of clicked cards to swap
        self.r_requested_cards = [] # Keeps track of clicked cards to request
        
        # Add the two dynamic dropdown inventory loaders into separate interaction rows
        self.add_item(SenderCardSelect(sender.id, sender_cards))
        self.add_item(ReceiverCardSelect(receiver.id, receiver_cards))

    def build_trade_embed(self):
        embed = discord.Embed(
            title="🤝 Interactive Multi-Card League Trade Dashboard",
            description=f"**Proposer:** {self.sender.mention}\n**Target Party:** {self.receiver.mention}\n\n*Use the dropdown menus below to select your items. You can choose multiple entries at once.*",
            color=0x3498db
        )
        
        # Generate the text list for the Sender's side of the box
        if self.s_offered_cards:
            s_lines = []
            for cid in self.s_offered_cards:
                c = DATA["global_cards"][cid]
                s_lines.append(f"• **[{c['rarity']}]** {c['name']} ({c['overall']} OVR)")
            s_text = "\n".join(s_lines)
        else:
            s_text = "*No cards selected yet.*"
            
        # Generate the text list for the Receiver's side of the box
        if self.r_requested_cards:
            r_lines = []
            for cid in self.r_requested_cards:
                c = DATA["global_cards"][cid]
                r_lines.append(f"• **[{c['rarity']}]** {c['name']} ({c['overall']} OVR)")
            r_text = "\n".join(r_lines)
        else:
            r_text = "*No cards selected yet.*"
            
        embed.add_field(name=f"📤 {self.sender.display_name} is Offering:", value=s_text, inline=False)
        embed.add_field(name=f"📥 Requested From {self.receiver.display_name}:", value=r_text, inline=False)
        embed.set_footer(text="Only the sender can alter the menu selections. Target party clicks Accept to execute.")
        return embed

    async def update_trade_display(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.build_trade_embed(), view=self)

    @discord.ui.button(label="Accept Trade", style=discord.ButtonStyle.success, row=2)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receiver.id:
            return await interaction.response.send_message("❌ Authorization Failure: Only the target player can accept this swap.", ephemeral=True)
            
        if not self.s_offered_cards and not self.r_requested_cards:
            return await interaction.response.send_message("❌ Transaction Denied: Cannot execute an empty trade offer.", ephemeral=True)
            
        s_id, r_id = str(self.sender.id), str(self.receiver.id)
        s_inv = DATA["users"][s_id]["inventory"]
        r_inv = DATA["users"][r_id]["inventory"]
        
        # FINAL SECURITY CHECK: Ensure items haven't been sold mid-trade
        for cid in self.s_offered_cards:
            if s_inv.get(cid, 0) < self.s_offered_cards.count(cid):
                return await interaction.response.send_message(f"❌ **Trade Aborted:** {self.sender.display_name} no longer owns enough copies of `{cid}`.", ephemeral=True)
        for cid in self.r_requested_cards:
            if r_inv.get(cid, 0) < self.r_requested_cards.count(cid):
                return await interaction.response.send_message(f"❌ **Trade Aborted:** You no longer own enough copies of `{cid}`.", ephemeral=True)
                
        # Deduct items from inventories
        for cid in self.s_offered_cards: s_inv[cid] -= 1
        for cid in self.r_requested_cards: r_inv[cid] -= 1
        
        # Add items to new owners
        for cid in self.s_offered_cards: r_inv[cid] = r_inv.get(cid, 0) + 1
        for cid in self.r_requested_cards: s_inv[cid] = s_inv.get(cid, 0) + 1
        
        save_data()
        self.stop()
        
        success_embed = discord.Embed(title="✅ Transaction Settled!", color=discord.Color.green())
        success_embed.description = f"The bulk multi-card deal between {self.sender.mention} and {self.receiver.mention} has been fully settled and backed up to cloud memory records!"
        await interaction.response.edit_message(embed=success_embed, view=None)

    @discord.ui.button(label="Decline Offer", style=discord.ButtonStyle.danger, row=2)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in (self.sender.id, self.receiver.id):
            return await interaction.response.send_message("❌ Access Denied: You are not a participant in this deal.", ephemeral=True)
            
        self.stop()
        await interaction.response.edit_message(content="🛑 **Trade Cancelled.** The proposal has been declined and dissolved.", embed=None, view=None)


@bot.hybrid_command(name="trade", description="Public Command: Open the visual multi-card trading dashboard menu")
@app_commands.describe(target_player="The user you want to swap items with")
async def trade(ctx, target_player: discord.Member):
    if target_player == ctx.author:
        return await ctx.send("❌ Self-trading is blocked.")
        
    s_id, r_id = str(ctx.author.id), str(target_player.id)
    verify_user(s_id, ctx.author.display_name)
    verify_user(r_id, target_player.display_name)
    
    # Extract sender inventory cards list matrix records
    s_valid_cards = []
    for cid, count in DATA["users"][s_id].get("inventory", {}).items():
        if count > 0 and cid in DATA["global_cards"]:
            s_valid_cards.append((cid, DATA["global_cards"][cid], count))
            
    # Extract receiver inventory cards list matrix records
    r_valid_cards = []
    for cid, count in DATA["users"][r_id].get("inventory", {}).items():
        if count > 0 and cid in DATA["global_cards"]:
            r_valid_cards.append((cid, DATA["global_cards"][cid], count))
            
    # Enforce basic inventory checks to avoid opening empty screens
    if not s_valid_cards and not r_valid_cards:
        return await ctx.send("🎒 **Vault Alert:** Neither player owns card assets ready for trading lanes.")
        
    # Sort options by rarity mapping priority metrics so they look neat in lists
    s_valid_cards.sort(key=lambda x: (RARITY_ORDER.index(x[1]["rarity"]) if x[1]["rarity"] in RARITY_ORDER else 99, -x[1]["overall"]))
    r_valid_cards.sort(key=lambda x: (RARITY_ORDER.index(x[1]["rarity"]) if x[1]["rarity"] in RARITY_ORDER else 99, -x[1]["overall"]))
    
    view = AdvancedTradeView(ctx.author, target_player, s_valid_cards, r_valid_cards)
    await ctx.send(f"🤝 {target_player.mention}, {ctx.author.mention} opened an interactive trade desk with you!", embed=view.build_trade_embed(), view=view)


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
                reward_amount = DATA["config"].get("match_reward", 75)
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

class BattleRosterSelect(discord.ui.Select):
    """Dropdown menu allowing a combatant to draft non-fatigued cards into their lineup."""
    def __init__(self, placeholder, valid_cards, player_side, user_id_str):
        options = []
        now = datetime.now()
        user_cooldowns = DATA["users"].get(user_id_str, {}).get("card_cooldowns", {})

        for cid, card, count in valid_cards[:25]:
            cooldown_timestamps = user_cooldowns.get(cid, [])
            active_cooldowns = []
            for ts_str in cooldown_timestamps:
                try:
                    ts = datetime.fromisoformat(ts_str)
                    if now < ts + timedelta(hours=24):
                        active_cooldowns.append(ts_str)
                except Exception:
                    continue
            
            uses_left = count - len(active_cooldowns)
            
            if uses_left <= 0:
                options.append(discord.SelectOption(
                    label=f"{card['name']} ({card['overall']} OVR)",
                    description=f"❌ LOCKED: On 24-hour stamina cooldown.",
                    value=f"cooldown_{cid}",
                    emoji="⏳"
                ))
            else:
                options.append(discord.SelectOption(
                    label=f"{card['name']} ({card['overall']} OVR)",
                    description=f"Available Uses: {uses_left}/{count} | ID: {cid}",
                    value=cid,
                    emoji="⚔️"
                ))

        super().__init__(placeholder=placeholder, min_values=3, max_values=3, options=options if options else [discord.SelectOption(label="No cards owned", value="none")])
        self.player_side = player_side
        self.user_id_str = user_id_str

    async def callback(self, interaction: discord.Interaction):
        if "none" in self.values:
            return await interaction.response.send_message("❌ You don't have enough cards to battle!", ephemeral=True)
            
        for val in self.values:
            if val.startswith("cooldown_"):
                return await interaction.response.send_message("❌ **Stamina Fatigue:** That card is resting on cooldown! Rotate your roster slots.", ephemeral=True)

        if self.player_side == "challenger" and interaction.user.id != self.view.challenger.id:
            return await interaction.response.send_message("❌ This dropdown is reserved for the challenger.", ephemeral=True)
        if self.player_side == "target" and interaction.user.id != self.view.target.id:
            return await interaction.response.send_message("❌ This dropdown is reserved for the opponent.", ephemeral=True)

        if self.player_side == "challenger":
            self.view.challenger_lineup = self.values
            await interaction.response.send_message("🔒 **Your combat roster is locked in secretly!** Ready for round allocations.", ephemeral=True)
        else:
            self.view.target_lineup = self.values
            await interaction.response.send_message("🔒 **Your combat roster is locked in secretly!** Ready for round allocations.", ephemeral=True)
            
        await self.view.check_draft_status(interaction)

class AdvancedBattleArenaView(discord.ui.View):
    def __init__(self, challenger, target, c_cards, t_cards, wager):
        # FIXED: Set total view timeout gate wrapper tracking mechanisms
        super().__init__(timeout=60.0)
        self.challenger = challenger
        self.target = target
        self.c_cards = c_cards
        self.t_cards = t_cards
        self.wager = wager
        self.message = None # Bound reference hook to update the timeout message layout
        
        # Game State Variables
        self.state = "ACCEPT_PHASE"
        self.challenger_lineup = []
        self.target_lineup = []
        
        self.current_round = 1
        self.challenger_rolled = False
        self.target_rolled = False
        
        self.challenger_score = 0
        self.target_score = 0
        self.round_history_log = []

        # Deploy Initial Acceptance Buttons
        self.accept_btn = discord.ui.Button(label="⚔️ Accept Challenge", style=discord.ButtonStyle.success, row=0)
        self.accept_btn.callback = self.accept_challenge_callback
        self.decline_btn = discord.ui.Button(label="🛑 Decline Offer", style=discord.ButtonStyle.danger, row=0)
        self.decline_btn.callback = self.decline_challenge_callback
        self.add_item(self.accept_btn)
        self.add_item(self.decline_btn)

    async def on_timeout(self):
        """Automated referee checking loop that executes instantly if the 1-minute timer runs out."""
        if not self.message:
            return
            
        c_id_str, t_id_str = str(self.challenger.id), str(self.target.id)
        self.clear_items()
        
        if self.state == "ACCEPT_PHASE":
            embed = discord.Embed(title="⏳ Challenge Expired", description=f"The match invitation issued to {self.target.mention} was ignored for 1 minute and dissolved.", color=discord.Color.red())
            try: await self.message.edit(embed=embed, view=None)
            except Exception: pass
            
        elif self.state == "DRAFT_PHASE":
            embed = discord.Embed(title="⏳ Lobby Cancelled", description="Roster selection timed out. One or both players failed to draft their cards within 1 minute.", color=discord.Color.red())
            try: await self.message.edit(embed=embed, view=None)
            except Exception: pass
            
        elif self.state == "COMBAT_PHASE":
            # Determine who skipped casting their dice slots
            if self.challenger_rolled and not self.target_rolled:
                # Target player goes AFK -> Challenger wins via Forfeit (FF)
                DATA["users"][c_id_str]["coins"] += (self.wager * 2)
                DATA["users"][c_id_str]["wins"] += 1
                DATA["users"][t_id_str]["losses"] += 1
                save_data()
                embed = discord.Embed(title="🏁 Match Settled by Forfeit", color=discord.Color.green())
                embed.description = f"⏱️ **{self.target.display_name}** failed to roll within 60 seconds!\n\n🎉 **{self.challenger.mention}** wins by forfeit and claims the **{self.wager * 2} coins** pot jackpot!"
                
            elif self.target_rolled and not self.challenger_rolled:
                # Challenger player goes AFK -> Target wins via Forfeit (FF)
                DATA["users"][t_id_str]["coins"] += (self.wager * 2)
                DATA["users"][t_id_str]["wins"] += 1
                DATA["users"][c_id_str]["losses"] += 1
                save_data()
                embed = discord.Embed(title="🏁 Match Settled by Forfeit", color=discord.Color.green())
                embed.description = f"⏱️ **{self.challenger.display_name}** failed to roll within 60 seconds!\n\n🎉 **{self.target.mention}** wins by forfeit and claims the **{self.wager * 2} coins** pot jackpot!"
                
            else:
                # Neither player clicked roll -> Mutual cancellation refund loop triggers
                DATA["users"][c_id_str]["coins"] += self.wager
                DATA["users"][t_id_str]["coins"] += self.wager
                save_data()
                embed = discord.Embed(title="❌ Match Dissolved", description="⏱️ Neither player rolled within 60 seconds! The showdown has been cancelled and wagers have been refunded.", color=discord.Color.red())
                
            try: await self.message.edit(embed=embed, view=None)
            except Exception: pass

    async def accept_challenge_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message("❌ You are not the target of this challenge card.", ephemeral=True)
            
        c_id, t_id = str(self.challenger.id), str(self.target.id)
        if DATA["users"][c_id]["coins"] < self.wager or DATA["users"][t_id]["coins"] < self.wager:
            return await interaction.response.send_message("❌ **Transaction Fault:** One of the combatants no longer has enough coins.", ephemeral=True)

        self.state = "DRAFT_PHASE"
        self.clear_items()
        self.timeout = 60.0 # Reset the 1-minute timer clock for the draft phase
        
        self.add_item(BattleRosterSelect(f"👉 {self.challenger.display_name}: Select 3 Hidden Cards", self.c_cards, "challenger", c_id))
        self.add_item(BattleRosterSelect(f"👉 {self.target.display_name}: Select 3 Hidden Cards", self.t_cards, "target", t_id))
        
        embed = discord.Embed(title="🏟️ Arena Showdown: Roster Draft Selection", color=0xCD7F32)
        embed.description = (
            f"⚔️ **Challenge Accepted!**\n"
            f"💰 Wager Stake Size: `{self.wager}` coins per side.\n\n"
            f"Both players must use the dropdown menus below to secretly select **3 cards** into their battle lineup.\n"
            f"*Cards remain completely hidden from your opponent until rolls fire!*"
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def decline_challenge_callback(self, interaction: discord.Interaction):
        if interaction.user.id not in (self.challenger.id, self.target.id):
            return await interaction.response.send_message("❌ You are not part of this duel.", ephemeral=True)
        self.stop()
        await interaction.response.edit_message(content=f"🛑 Challenge declined by {interaction.user.display_name}. Arena room dissolved.", embed=None, view=None)

    async def check_draft_status(self, interaction: discord.Interaction):
        if len(self.challenger_lineup) == 3 and len(self.target_lineup) == 3:
            self.state = "COMBAT_PHASE"
            self.clear_items()
            self.timeout = 60.0 # Reset the 1-minute timer clock for the combat loop
            
            self.roll_btn = discord.ui.Button(label="🎲 Roll Dice", style=discord.ButtonStyle.primary, row=0)
            self.roll_btn.callback = self.roll_dice_callback
            self.add_item(self.roll_btn)
            
            await self.render_combat_screen(interaction)

    async def render_combat_screen(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"🏟️ TBA Arena Showdown: Round {self.current_round} of 3", color=0xCD7F32)
        
        c_status = "🎲 READY TO ROLL" if not self.challenger_rolled else "✅ LOCKED IN"
        t_status = "🎲 READY TO ROLL" if not self.target_rolled else "✅ LOCKED IN"
        
        embed.description = (
            f"🏃‍♂️ **{self.challenger.display_name}:** {c_status}\n"
            f"🛡️ **{self.target.display_name}:** {t_status}\n\n"
            f"💡 *Both players must click the **Roll Dice** button below to execute combat calculations for this round!*"
        )
        
        if self.round_history_log:
            embed.add_field(name="📜 Arena Combat Timeline Logs", value="\n".join(self.round_history_log), inline=False)
            
        await interaction.message.edit(embed=embed, view=self)

    async def roll_dice_callback(self, interaction: discord.Interaction):
        if interaction.user.id == self.challenger.id:
            if self.challenger_rolled:
                return await interaction.response.send_message("❌ You have already cast your dice parameters for this round slot.", ephemeral=True)
            self.challenger_rolled = True
            await interaction.response.send_message("🎲 **Dice cast! Waiting on opponent...**", ephemeral=True)
        elif interaction.user.id == self.target.id:
            if self.target_rolled:
                return await interaction.response.send_message("❌ You have already cast your dice parameters for this round slot.", ephemeral=True)
            self.target_rolled = True
            await interaction.response.send_message("🎲 **Dice cast! Waiting on challenger...**", ephemeral=True)
        else:
            return await interaction.response.send_message("❌ Spectators cannot interfere with arena roll gates.", ephemeral=True)

        if self.challenger_rolled and self.target_rolled:
            self.timeout = 60.0 # Reset the 1-minute timer back to full for the next round slot
            await self.process_combat_round(interaction)
        else:
            await self.render_combat_screen(interaction)

    async def process_combat_round(self, interaction: discord.Interaction):
        c_id_str, t_id_str = str(self.challenger.id), str(self.target.id)
        
        if self.current_round == 1:
            if DATA["users"][c_id_str]["coins"] < self.wager or DATA["users"][t_id_str]["coins"] < self.wager:
                self.clear_items()
                return await interaction.message.edit(content="❌ **Combat Aborted:** Financial liquidity failure mid-round setup.", embed=None, view=None)
            
            DATA["users"][c_id_str]["coins"] -= self.wager
            DATA["users"][t_id_str]["coins"] -= self.wager

        idx = self.current_round - 1
        c_cid = self.challenger_lineup[idx]
        t_cid = self.target_lineup[idx]
                # Process exact index slot details
        idx = self.current_round - 1
        c_cid = self.challenger_lineup[idx]
        t_cid = self.target_lineup[idx]
        
        c_card = DATA["global_cards"][c_cid]
        t_card = DATA["global_cards"][t_cid]
        
        c_roll = random.randint(1, 20)
        t_roll = random.randint(1, 20)
        
        c_total = c_card["overall"] + c_roll
        t_total = t_card["overall"] + t_roll
        
        r_winner = ""
        if c_total > t_total:
            self.challenger_score += 1
            r_winner = self.challenger.display_name
        elif t_total > c_total:
            self.target_score += 1
            r_winner = self.target.display_name
        else:
            if random.choice([True, False]):
                self.challenger_score += 1
                r_winner = f"{self.challenger.display_name} (Direct Tiebreaker)"
            else:
                self.target_score += 1
                r_winner = f"{self.target.display_name} (Direct Tiebreaker)"

        self.round_history_log.append(
            f"🥊 **ROUND {self.current_round} REVEAL:**\n"
            f"🏃‍♂️ {self.challenger.display_name}: **{c_card['name'].upper()}** ({c_card['overall']} OVR + {c_roll} Roll = `{c_total}`)\n"
            f"🛡️ {self.target.display_name}: **{t_card['name'].upper()}** ({t_card['overall']} OVR + {t_roll} Roll = `{t_total}`)\n"
            f"👑 Round Winner: **{r_winner}**\n"
        )

        self.challenger_rolled = False
        self.target_rolled = False
        
        if self.challenger_score == 2 or self.target_score == 2:
            self.state = "END"
            self.clear_items()
            await self.finalize_arena_showdown(interaction)
        elif self.current_round < 3:
            self.current_round += 1
            await self.render_combat_screen(interaction)
        else:
            self.state = "END"
            self.clear_items()
            await self.finalize_arena_showdown(interaction)

    async def finalize_arena_showdown(self, interaction: discord.Interaction):
        c_id_str, t_id_str = str(self.challenger.id), str(self.target.id)
        
        if self.challenger_score > self.target_score:
            champ = self.challenger
            DATA["users"][c_id_str]["coins"] += (self.wager * 2)
            DATA["users"][c_id_str]["wins"] += 1
            DATA["users"][t_id_str]["losses"] += 1
        else:
            champ = self.target
            DATA["users"][t_id_str]["coins"] += (self.wager * 2)
            DATA["users"][t_id_str]["wins"] += 1
            DATA["users"][c_id_str]["losses"] += 1

        now_iso = datetime.now().isoformat()
        for i in range(self.current_round):
            c_cid = self.challenger_lineup[i]
            t_cid = self.target_lineup[i]
            
            if "card_cooldowns" not in DATA["users"][c_id_str]: 
                DATA["users"][c_id_str]["card_cooldowns"] = {}
            if c_cid not in DATA["users"][c_id_str]["card_cooldowns"]: 
                DATA["users"][c_id_str]["card_cooldowns"][c_cid] = []
            DATA["users"][c_id_str]["card_cooldowns"][c_cid].append(now_iso)
            
            if "card_cooldowns" not in DATA["users"][t_id_str]: 
                DATA["users"][t_id_str]["card_cooldowns"] = {}
            if t_cid not in DATA["users"][t_id_str]["card_cooldowns"]: 
                DATA["users"][t_id_str]["card_cooldowns"][t_cid] = []
            DATA["users"][t_id_str]["card_cooldowns"][t_cid].append(now_iso)

        save_data()

        embed = discord.Embed(title="🏆 TBA Stadium Arena Combat: Grand Finale", color=0xFFD700)
        embed.description = "\n".join(self.round_history_log)
        
        knockout_footer = ""
        if self.current_round < 3:
            knockout_footer = "\n\n⚡ **EARLY KNOCKOUT VICTORY!** The match ended in 2 rounds. Both players' unused 3rd cards saved their stamina and remain available for battles!"

        embed.add_field(
            name="🏁 CHAMPIONSHIP AWARD DECLARATION", 
            value=f"🎉 **{champ.display_name}** has won the showdown series block match and claimed the entire jackpot prize pool of `{self.wager * 2}` coins! 🪙{knockout_footer}", 
            inline=False
        )
        await interaction.message.edit(embed=embed, view=None)


@bot.hybrid_command(name="challenge", description="Public Command: Wager coins and challenge another player to a 3v3 hidden card showdown")
@app_commands.describe(opponent="The user you want to fight", wager="Coin stake value amount to bet")
async def challenge(ctx, opponent: discord.Member, wager: int):
    if opponent == ctx.author:
        return await ctx.send("❌ You cannot battle yourself!")
    if wager <= 0:
        return await ctx.send("❌ The bet stake wager value parameters must be greater than 0.")

    c_id, t_id = str(ctx.author.id), str(opponent.id)
    verify_user(c_id, ctx.author.display_name)
    verify_user(t_id, opponent.display_name)

    if DATA["users"][c_id]["coins"] < wager:
        return await ctx.send(f"❌ You don't have enough coins! Current Balance: `{DATA['users'][c_id]['coins']}` coins.")
    if DATA["users"][t_id]["coins"] < wager:
        return await ctx.send(f"❌ {opponent.display_name} doesn't have enough coins to match that bet stake wager size.")

    c_valid = [(cid, DATA["global_cards"][cid], count) for cid, count in DATA["users"][c_id].get("inventory", {}).items() if count > 0 and cid in DATA["global_cards"]]
    t_valid = [(cid, DATA["global_cards"][cid], count) for cid, count in DATA["users"][t_id].get("inventory", {}).items() if count > 0 and cid in DATA["global_cards"]]

    if len(c_valid) < 3 or len(t_valid) < 3:
        return await ctx.send("❌ **Battle Denied:** Both players must possess at least 3 valid cards in their inventory vaults to compete.")

    # FIXED DIRECT TUPLE ACCESSING
    c_valid.sort(key=lambda x: (RARITY_ORDER.index(x[1]["rarity"]) if x[1]["rarity"] in RARITY_ORDER else 99, -x[1]["overall"]))
    t_valid.sort(key=lambda x: (RARITY_ORDER.index(x[1]["rarity"]) if x[1]["rarity"] in RARITY_ORDER else 99, -x[1]["overall"]))

    embed = discord.Embed(title="⚔️ Battle Stadium Challenge Issued!", color=0xCD7F32)
    embed.description = f"🏟️ {opponent.mention}, {ctx.author.mention} has challenged you to an arena showdown card match series!\n\n💰 **Wager Stake size:** `{wager}` coins per player (`{wager * 2}` total pot)\n\n*Click the button below to accept the match and access the hidden draft rooms.*"
    
    view = AdvancedBattleArenaView(ctx.author, opponent, c_valid, t_valid, wager)
    view.message = await ctx.send(embed=embed, view=view)

# ==============================================================================
# --- EXHIBITION STADIUM: VS CPU BOSS MODE ENGINE ---
# ==============================================================================

class CPUBossArenaView(discord.ui.View):
    def __init__(self, player, p_cards, cpu_name, cpu_lineup, wager):
        super().__init__(timeout=120.0)
        self.player = player
        # FIXED: Feeds a secondary pointer to satisfy the shared dropdown verification check
        self.challenger = player  
        self.p_cards = p_cards
        self.cpu_name = cpu_name
        self.cpu_lineup = cpu_lineup
        self.wager = wager
        self.message = None
        
        self.challenger_lineup = [] # FIXED: Ensures selection storage matches multiplayer arrays
        self.player_lineup = []
        self.current_round = 1
        self.player_score = 0
        self.cpu_score = 0
        self.round_history_log = []

        self.add_item(BattleRosterSelect(f"👉 Select 3 Cards to fight {cpu_name}", p_cards, "challenger", str(player.id)))

    async def on_timeout(self):
        if self.message:
            embed = discord.Embed(title="⏳ Exhibition Hall Abandoned", description="You took too long to draft or roll against the CPU boss. Lobby dissolved.", color=discord.Color.red())
            try: await self.message.edit(embed=embed, view=None)
            except Exception: pass

    async def check_draft_status(self, interaction: discord.Interaction):
        # We manually map challenger choices straight over since CPU selections are automated
        if len(self.challenger_lineup) == 3:
            self.player_lineup = self.challenger_lineup
            self.clear_items()
            
            # Deduct wager entry stake safely
            p_id_str = str(self.player.id)
            DATA["users"][p_id_str]["coins"] -= self.wager
            
            # Setup interactive Single-Player sync buttons
            self.roll_btn = discord.ui.Button(label="🎲 Roll Against CPU", style=discord.ButtonStyle.primary, row=0)
            self.roll_btn.callback = self.player_roll_callback
            self.add_item(self.roll_btn)
            
            await self.render_combat_screen(interaction)

    async def render_combat_screen(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"🏟️ VS {self.cpu_name.upper()} | Round {self.current_round} of 3", color=0x3498db)
        embed.description = f"👤 **Player Status:** Ready to Roll!\n🤖 **CPU Status:** Waiting for your move...\n\nClick the button below to clash weights!"
        if self.round_history_log:
            embed.add_field(name="📜 Exhibition Combat Logs", value="\n".join(self.round_history_log), inline=False)
        await interaction.message.edit(embed=embed, view=self)

    async def player_roll_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.player.id:
            return await interaction.response.send_message("❌ This is a private exhibition hall match loop.", ephemeral=True)
            
        self.timeout = 60.0
        p_id_str = str(self.player.id)
        
        idx = self.current_round - 1
        p_cid = self.player_lineup[idx]
        cpu_card = self.cpu_lineup[idx] # Raw loaded dictionary
        
        p_card = DATA["global_cards"][p_cid]
        
        # Stamina stamping allocation rules applied
        now_iso = datetime.now().isoformat()
        if "card_cooldowns" not in DATA["users"][p_id_str]: DATA["users"][p_id_str]["card_cooldowns"] = {}
        if p_cid not in DATA["users"][p_id_str]["card_cooldowns"]: DATA["users"][p_id_str]["card_cooldowns"][p_cid] = []
        DATA["users"][p_id_str]["card_cooldowns"][p_cid].append(now_iso)

        p_roll = random.randint(1, 20)
        cpu_roll = random.randint(1, 20)
        
        p_total = p_card["overall"] + p_roll
        cpu_total = cpu_card["overall"] + cpu_roll
        
        r_winner = ""
        if p_total > cpu_total:
            self.player_score += 1
            r_winner = self.player.display_name
        elif cpu_total > p_total:
            self.cpu_score += 1
            r_winner = self.cpu_name
        else:
            if random.choice([True, False]):
                self.player_score += 1
                r_winner = self.player.display_name
            else:
                self.cpu_score += 1
                r_winner = self.cpu_name

        self.round_history_log.append(
            f"🥊 **ROUND {self.current_round} SUMMARY:**\n"
            f"👤 {self.player.display_name}: **{p_card['name']}** ({p_card['overall']} OVR + {p_roll} Roll = `{p_total}`)\n"
            f"🤖 {self.cpu_name}: **{cpu_card['name']}** ({cpu_card['overall']} OVR + {cpu_roll} Roll = `{cpu_total}`)\n"
            f"👑 Winner: **{r_winner}**\n"
        )

        if self.player_score == 2 or self.cpu_score == 2:
            self.clear_items()
            await self.finalize_exhibition(interaction)
        elif self.current_round < 3:
            self.current_round += 1
            await self.render_combat_screen(interaction)
        else:
            self.clear_items()
            await self.finalize_exhibition(interaction)

    async def finalize_exhibition(self, interaction: discord.Interaction):
        p_id_str = str(self.player.id)
        
        if self.player_score > self.cpu_score:
            winnings = self.wager * 2
            DATA["users"][p_id_str]["coins"] += winnings
            DATA["users"][p_id_str]["wins"] += 1
            DATA["users"][p_id_str]["last_cpu_boss"] = datetime.now().date().isoformat()
            result_title = "🎉 STADIUM BOSS DEFEATED!"
            result_desc = f"Congratulations! You smashed the CPU lineup and claimed the **{winnings} coins** reward pot! 🪙"
        else:
            DATA["users"][p_id_str]["losses"] += 1
            result_title = "💀 ARENA CRUSHED"
            result_desc = f"The {self.cpu_name} out-rolled your squad. You lost your `{self.wager}` coins wager stake entry."

        save_data()
        
        embed = discord.Embed(title=result_title, description=f"{result_desc}\n\n" + "\n".join(self.round_history_log), color=0x2ecc71 if self.player_score > self.cpu_score else 0xe74c3c)
        await interaction.message.edit(embed=embed, view=None)

@bot.hybrid_command(name="vsbot", description="Public Command: Fight a daily rotating automated CPU boss card team to earn coins")
async def vsbot(ctx):
    if not DATA["global_cards"]: return await ctx.send("❌ Master database catalog records are uninitialized.")
    
    p_id = str(ctx.author.id)
    verify_user(p_id, ctx.author.display_name)
    
    # Check 24-hour daily boss challenge lock limits
    today_iso = datetime.now().date().isoformat()
    if DATA["users"][p_id].get("last_cpu_boss") == today_iso:
        return await ctx.send("⏳ **Lockout Active:** You already defeated today's CPU Boss! Come back tomorrow for a fresh team.")
        
    wager = 50
    if DATA["users"][p_id]["coins"] < wager:
        return await ctx.send(f"❌ Vault Error: You need at least `{wager}` coins to challenge the arena box.")

    p_valid = [(cid, DATA["global_cards"][cid], count) for cid, count in DATA["users"][p_id].get("inventory", {}).items() if count > 0 and cid in DATA["global_cards"]]
    if len(p_valid) < 3:
        return await ctx.send("❌ **Battle Denied:** You need at least 3 cards in your binder to enter the exhibition modes.")

    # FIXED SORT LAYOUT: x[1] correctly grabs the inner dictionary index data so it can read keys like 'rarity' and 'overall' safely
    p_valid.sort(key=lambda x: (RARITY_ORDER.index(x[1]["rarity"]) if x[1]["rarity"] in RARITY_ORDER else 99, -x[1]["overall"]))

    # AUTOMATED SQUAD GENERATION ROUTINE: Pick 3 random cards from the global deck catalog
    all_card_ids = list(DATA["global_cards"].keys())
    cpu_ids = random.choices(all_card_ids, k=3)
    cpu_lineup = [DATA["global_cards"][cid] for cid in cpu_ids]
    
    cpu_boss_names = ["The Steel Anchor Bot", "Cyber Netmind Blocker", "The Frozen Titan AI", "Glitch Blade Skater"]
    cpu_name = random.choice(cpu_boss_names)

    embed = discord.Embed(title="🏒 Exhibition Hall: Daily Boss Encounter", color=0x3498db)
    embed.description = f"🥊 **Boss Identity:** {cpu_name}\n🪙 **Entry Stake Cost:** `{wager}` Coins\n💰 **Winnings Payout Pot:** `{wager * 2}` Coins\n\n*Select your 3 non-fatigued card deck targets below to lock handles!*"
    
    view = CPUBossArenaView(ctx.author, p_valid, cpu_name, cpu_lineup, wager)
    view.message = await ctx.send(embed=embed, view=view)

# ==============================================================================
# --- RETAIL STORE: PREMIUM TIERED WHEEL SPIN MODULES ---
# ==============================================================================

@bot.hybrid_command(name="setwheelprice", description="Staff Command: Configure the coin purchase price of Bronze, Silver, or Gold prize wheels")
@is_staff()
@app_commands.choices(wheel_tier=[
    app_commands.Choice(name="Bronze Wheel", value="Bronze"),
    app_commands.Choice(name="Silver Wheel", value="Silver"),
    app_commands.Choice(name="Gold Wheel", value="Gold")
])
async def setwheelprice(ctx, wheel_tier: str, new_price: int):
    if new_price < 0:
        return await ctx.send("❌ **Input Error:** Wheel spin prices cannot be negative values.")
        
    if "config" not in DATA: 
        DATA["config"] = {}
    
    # Securely saves using the clean shorthand text matching tokens
    DATA["config"][f"wheel_{wheel_tier}_price"] = new_price
    save_data()
    
    embed = discord.Embed(title="⚙️ Store Configuration Updated", color=0x3498db)
    embed.description = f"Successfully updated the cost of the **{wheel_tier} Prize Wheel** to `{new_price}` coins 🪙."
    await ctx.send(embed=embed)


import random

# Exact Rarity Configuration (Adjust these percentages to change your drop rates)
WHEEL_ODDS = {
    "Bronze": {
        "Average": 45,
        "Great": 40,
        "Epic": 35,
        "Insane": 25,
        "Pro": 10,
        "Juggernaut": 3,
        "Otherworldly": 0.19,
        "Specialty": 0.01
    },
    "Silver": {
        # "Average" is strictly excluded per your rules
        "Great": 45,
        "Epic": 40,
        "Insane": 35,
        "Pro": 15,
        "Juggernaut": 5,
        "Otherworldly": 1,
        "Specialty": 0.1
    },
    "Gold": {
        # Only Insane and higher ranks allowed
        "Insane": 50,
        "Pro": 30,
        "Juggernaut": 14,
        "Otherworldly": 5,
        "Specialty": 1
    }
}

@bot.hybrid_command(name="wheelspin", description="Public Command: Spend coins to buy a Bronze, Silver, or Gold prize wheel card roll")
@app_commands.choices(wheel_tier=[
    app_commands.Choice(name="Bronze Wheel - Basic Odds", value="Bronze"),
    app_commands.Choice(name="Silver Wheel - No Average Cards", value="Silver"),
    app_commands.Choice(name="Gold Wheel - Insane Tier and Higher Only!", value="Gold")
])
async def wheelspin(ctx, wheel_tier: str):
    if not DATA["global_cards"]: 
        return await ctx.send("❌ Error: Master blueprint records are empty.")
    
    u_id = str(ctx.author.id)
    verify_user(u_id, ctx.author.display_name)
    
    if "config" not in DATA: 
        DATA["config"] = {}
        
    tier_defaults = {"Bronze": 100, "Silver": 250, "Gold": 500}
    cost = DATA["config"].get(f"wheel_{wheel_tier}_price", tier_defaults.get(wheel_tier, 100))
    
    if DATA["users"][u_id]["coins"] < cost:
        return await ctx.send(f"❌ Store Error: Insufficient funds. The {wheel_tier} Wheel costs `{cost}` coins (Your wallet holds: `{DATA['users'][u_id]['coins']}`).")

    pool = []
    weights = []
    tier_odds = WHEEL_ODDS.get(wheel_tier, {})

    for cid, c in DATA["global_cards"].items():
        r = c["rarity"]
        
        # Enforce your wheel boundary rules
        if wheel_tier == "Silver" and r == "Average":
            continue
        elif wheel_tier == "Gold" and r in ["Average", "Great", "Epic"]:
            continue
            
        # Add to matching pool if the rarity has a weight set
        if r in tier_odds and tier_odds[r] > 0:
            pool.append((cid, c))
            weights.append(tier_odds[r])

    if not pool:
        return await ctx.send("❌ Configuration Error: No cards found matching this tier's drop filters.")

    DATA["users"][u_id]["coins"] -= cost
    
    # Securely draws 1 card tuple utilizing the relative rarity weights
    chosen_item = random.choices(pool, weights=weights, k=1)[0]
    chosen_id, card = chosen_item
    
    DATA["users"][u_id]["inventory"][chosen_id] = DATA["users"][u_id]["inventory"].get(chosen_id, 0) + 1
    save_data()

    r_color = RARITY_COLORS.get(card['rarity'], 0x3498db)
    r_emoji = get_rarity_emoji(card['rarity'])

    embed = discord.Embed(title=f"🎡 {wheel_tier.upper()} PRIZE WHEEL SETTLED", color=r_color)
    embed.description = f"🎯 The wheel spins, sparks fly, and click-clacks down onto a matching prize sector allocation!\n\n🛍️ **Item Deposited into your Inventory Vault:**"
    embed.add_field(name=f"{r_emoji} {card['name'].upper()}", value=f"```\nOVERALL: {card['overall']} OVR\nRARITY:  {card['rarity']}\nCARD ID: {chosen_id}\n```", inline=False)
    embed.add_field(name="🏦 Updated Wallet Balance", value=f"`{DATA['users'][u_id]['coins']}` coins 🪙", inline=False)
    
    if card.get("image_url"):
        embed.set_image(url=card["image_url"])
        
    await ctx.send(embed=embed)

# ==============================================================================
# --- THE GUESSING GAUNTLET: HIGHER OR LOWER CARD GAME ---
# ==============================================================================

class GuessingGauntletView(discord.ui.View):
    def __init__(self, player, current_card_id, wager):
        super().__init__(timeout=60.0)
        self.player = player
        self.current_card_id = current_card_id
        self.wager = wager
        self.multiplier = 1.0
        self.streak = 0
        self.message = None

    async def on_timeout(self):
        if self.message:
            u_id_str = str(self.player.id)
            # Automatic cash out on timeout to protect user coins
            final_payout = int(self.wager * self.multiplier)
            if self.streak > 0:
                DATA["users"][u_id_str]["coins"] += final_payout
                save_data()
                embed = discord.Embed(title="⏳ Gauntlet Timed Out", description=f"{self.player.mention}, you took too long to guess! The referee automatically cashed you out with your streak multiplier.\n\n💰 **Final Payout:** `{final_payout}` coins 🪙", color=discord.Color.orange())
            else:
                embed = discord.Embed(title="⏳ Gauntlet Timed Out", description=f"{self.player.mention}, your game timed out before making any guesses. Your initial wager has been lost.", color=discord.Color.red())
            try: await self.message.edit(embed=embed, view=None)
            except Exception: pass

    def make_game_embed(self, next_card_reveal=None, result_text=""):
        card = DATA["global_cards"][self.current_card_id]
        r_color = RARITY_COLORS.get(card['rarity'], 0x3498db)
        r_emoji = get_rarity_emoji(card['rarity'])
        
        embed = discord.Embed(title="🎯 The Guessing Gauntlet", color=r_color)
        embed.description = f"👤 **Player:** {self.player.mention}\n💰 **Initial Wager:** `{self.wager}` coins\n📈 **Current Multiplier:** `{self.multiplier:.1f}x`\n🔥 **Current Win Streak:** `{self.streak}` rounds\n💵 **Current Value if Cashed Out:** `{int(self.wager * self.multiplier)}` coins\n\n"
        
        if result_text:
            embed.description += f"{result_text}\n\n"

        embed.add_field(
            name="🎴 CURRENT CARD ON THE BOARD",
            value=f"```\nNAME:    {card['name'].upper()}\nOVERALL: {card['overall']} OVR\nRARITY:  {card['rarity']}\n```",
            inline=False
        )
        
        embed.set_footer(text="Will the next card drawn from the catalog be HIGHER or LOWER OVR?")
        if card.get("image_url"):
            embed.set_thumbnail(url=card["image_url"])
        return embed

    async def process_guess(self, interaction: discord.Interaction, guess: str):
        if interaction.user.id != self.player.id:
            return await interaction.response.send_message("❌ This game matrix belongs to another player.", ephemeral=True)

        self.timeout = 60.0
        u_id_str = str(self.player.id)
        
        # Draw the next random target card from the catalog
        all_card_ids = list(DATA["global_cards"].keys())
        next_card_id = random.choice(all_card_ids)
        
        current_card = DATA["global_cards"][self.current_card_id]
        next_card = DATA["global_cards"][next_card_id]
        
        curr_ovr = current_card["overall"]
        next_ovr = next_card["overall"]
        
        next_emoji = get_rarity_emoji(next_card['rarity'])
        reveal_string = f"📋 **Drawn Card:** {next_emoji} **{next_card['name'].upper()}** (`{next_ovr} OVR` - {next_card['rarity']})"

        # Handle exact tie scenario based on custom request
        if next_ovr == curr_ovr:
            result_text = f"⚖️ **ROUND TIE!** {reveal_string}\nBoth cards share the exact same `{next_ovr}` OVR rating. No multiplier gains or wager losses incurred!"
            self.current_card_id = next_card_id
            return await interaction.response.edit_message(embed=self.make_game_embed(result_text=result_text), view=self)

        # Check win/loss parameters
        is_win = False
        if guess == "higher" and next_ovr > curr_ovr:
            is_win = True
        elif guess == "lower" and next_ovr < curr_ovr:
            is_win = True

        if is_win:
            self.streak += 1
            # Add dynamic incremental scale multiplier additions
            self.multiplier += 0.4
            result_text = f"✅ **CORRECT!** {reveal_string}\nYour win streak increases! Multiplier increased to `{self.multiplier:.1f}x`."
            self.current_card_id = next_card_id
            await interaction.response.edit_message(embed=self.make_game_embed(result_text=result_text), view=self)
        else:
            # Player guessed incorrectly -> Wager fully consumed
            self.clear_items()
            self.stop()
            result_text = f"❌ **WRONG GUESS!** {reveal_string}\nYou guessed `{guess.upper()}` but the card layout broke your streak chain. Your wager has been lost!"
            embed = discord.Embed(title="💀 Gauntlet Broken", description=result_text, color=discord.Color.red())
            await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="🔼 Higher", style=discord.ButtonStyle.primary, row=0)
    async def higher_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_guess(interaction, "higher")

    @discord.ui.button(label="🔽 Lower", style=discord.ButtonStyle.secondary, row=0)
    async def lower_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_guess(interaction, "lower")

    @discord.ui.button(label="🏦 Cash Out", style=discord.ButtonStyle.success, row=0)
    async def cash_out_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player.id:
            return await interaction.response.send_message("❌ This game matrix belongs to another player.", ephemeral=True)
            
        if self.streak == 0:
            return await interaction.response.send_message("❌ You must win at least 1 round successfully before cashing out!", ephemeral=True)

        self.clear_items()
        self.stop()
        
        u_id_str = str(self.player.id)
        final_winnings = int(self.wager * self.multiplier)
        
        # Credit wallet profits cleanly
        DATA["users"][u_id_str]["coins"] += final_winnings
        save_data()
        
        embed = discord.Embed(title="🏦 Vault Cash Out Successful!", color=discord.Color.green())
        embed.description = f"🎉 {self.player.mention} decided to walk away with their earnings!\n\n🔥 **Final Streak:** `{self.streak}` rounds\n📈 **Final Multiplier:** `{self.multiplier:.1f}x`\n💰 **Total Payout Returned:** `{final_winnings}` coins 🪙"
        await interaction.response.edit_message(embed=embed, view=None)


@bot.hybrid_command(name="gauntlet", description="Public Command: Wager coins on a card higher-or-lower guessing game streak")
@app_commands.describe(wager="Coin stake value amount to bet")
async def gauntlet(ctx, wager: int):
    if not DATA["global_cards"]: 
        return await ctx.send("❌ Error: Master blueprint records are empty.")
    if wager <= 0:
        return await ctx.send("❌ Input Error: Your wager amount parameters must be greater than 0.")

    u_id_str = str(ctx.author.id)
    verify_user(u_id_str, ctx.author.display_name)
    
    if DATA["users"][u_id_str]["coins"] < wager:
        return await ctx.send(f"❌ Store Error: Insufficient funds. Your wallet holds: `{DATA['users'][u_id_str]['coins']}` coins.")

    # Deduct upfront wager safely out of local memory tracks
    DATA["users"][u_id_str]["coins"] -= wager
    save_data()

    # Draw starter base setup card target completely at random from catalog
    all_card_ids = list(DATA["global_cards"].keys())
    starter_card_id = random.choice(all_card_ids)

    view = GuessingGauntletView(ctx.author, starter_card_id, wager)
    view.message = await ctx.send(embed=view.make_game_embed(), view=view)

# --- Start Services ---
if __name__ == "__main__":
    keep_alive()
    load_data()
    if TOKEN:
        print("🤖 Connecting client to Discord Gateway panels...")
        bot.run(TOKEN)
    else:
        print("❌ Critical System Initialization Fault: 'DISCORD_TOKEN' environment key is blank.")




