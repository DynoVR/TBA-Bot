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
app = Flask('')

@app.route('/')
def home():
    return "OK", 200

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

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
        url = f"https://github.com{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
        
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

def load_data():
    global DATA
    # 1. Attempt to read locally first
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, "r") as f:
                DATA = json.load(f)
                print("💾 Local database loaded successfully.")
                return
        except Exception as e:
            print(f"Local Read Error: {e}")

    # 2. If local file is missing, pull the permanent copy directly from GitHub Cloud!
    if GH_TOKEN:
        try:
            url = f"https://github.com{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
            headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
            res = requests.get(url, headers=headers)
            
            if res.status_code == 200:
                file_data = res.json()
                content = base64.b64decode(file_data["content"]).decode("utf-8")
                DATA = json.loads(content)
                print("☁️ Permanent database successfully pulled and restored from GitHub Cloud!")
                
                with open(DATABASE_FILE, "w") as f:
                    json.dump(DATA, f, indent=4)
            else:
                print(f"⚠️ Cloud Pull Failed ({res.status_code}): No remote backup found yet.")
        except Exception as e:
            print(f"GitHub Cloud Pull Fault: {e}")

def verify_user(user_id_str, username="Unknown"):
    if user_id_str not in DATA["users"]:
        DATA["users"][user_id_str] = {
            "name": username, "coins": 100, "inventory": {},
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
    """Background Task: Actively polls server channels to auto-reward match winners."""
    await bot.wait_until_ready()
    
    for guild in bot.guilds:
        try:
            await guild.chunk(cache=True)
        except:
            pass
            
        for channel in guild.text_channels:
            channel_name = channel.name.lower()
            
            # Target channels created by queue loops (e.g. #queue-123, #match-456, #active-queue)
            if "queue" in channel_name or "match" in channel_name or "game" in channel_name:
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
                                    
                            if "winner" not in text_to_scan.lower():
                                continue
                                
                            winning_user_ids = []
                            losing_user_ids = []
                            
                            winners_found = re.findall(r"<@!?(\d+)>(?=[^<>\n]*\+)", text_to_scan)
                            losers_found = re.findall(r"<@!?(\d+)>(?=[^<>\n]*\-)", text_to_scan)
                            
                            if not winners_found and not losers_found:
                                for line in text_to_scan.split("\n"):
                                    if "+" in line:
                                        plain_win = re.findall(r"@([^+\-\n\s\(]+)", line)
                                        for name in plain_win:
                                            m = discord.utils.get(guild.members, display_name=name) or discord.utils.get(guild.members, name=name)
                                            if m: winning_user_ids.append(str(m.id))
                                    elif "-" in line:
                                        plain_loss = re.findall(r"@([^+\-\n\s\(]+)", line)
                                        for name in plain_loss:
                                            m = discord.utils.get(guild.members, display_name=name) or discord.utils.get(guild.members, name=name)
                                            if m: losing_user_ids.append(str(m.id))
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
                                        f"🪙 **NeatQueue Auto-Automation Active!** Scanned match scorecard.\n"
                                        f"The following winners have been automatically credited with **{reward} coins**: "
                                        f"{', '.join(awarded_mentions)}"
                                    )
                except Exception as e:
                    pass


# ==============================================================================
# --- BOT INITIALIZER AND EVENT HOOKS ---
# ==============================================================================

@bot.event
async def on_ready():
    load_data()
    keep_alive()
    print(f"🏒 Bot Online: Connected as {bot.user}")
    
    if not automatic_neatque_scanner.is_running():
        automatic_neatque_scanner.start()
        print("🚀 Automated Background Match Scanner Started (30s Interval Loop Active).")
        
    try:
        await bot.tree.sync()
        print("🔄 Slash commands linked.")
    except Exception as e:
        print(f"Sync Error: {e}")

            
    try:
        await bot.tree.sync()
        print("🔄 Slash layout modules linked seamlessly.")
    except Exception as e:
        print(f"Sync Error: {e}")

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
    
    cost = DATA["config"].get(f"pack_{pack_size}_price", 100)
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
async def on_message(message: discord.Message):
    # 1. Prevent loop traps
    if message.author == bot.user:
        return

    # 2. Open gate check for NeatQueue, webhooks, or bots
    is_neat = "neat" in message.author.name.lower() or message.author.id == 857633321064595466
    is_external = message.webhook_id is not None or message.author.bot

    if is_neat or is_external:
        text_to_scan = ""
        
        if message.content:
            text_to_scan += message.content + "\n"
            
        # Deep matrix scan across ALL possible hidden string pockets inside NeatQueue's template layout
        if message.embeds:
            for embed in message.embeds:
                if embed.title: 
                    text_to_scan += f" [TITLE] {embed.title}\n"
                if embed.description: 
                    text_to_scan += f" [DESC] {embed.description}\n"
                if embed.author and embed.author.name:
                    text_to_scan += f" [AUTH] {embed.author.name}\n"
                if embed.footer and embed.footer.text:
                    text_to_scan += f" [FOOT] {embed.footer.text}\n"
                for field in embed.fields:
                    text_to_scan += f" [FIELD_NAME] {field.name} [FIELD_VALUE] {field.value}\n"

        clean_text_payload = text_to_scan.lower()

        # Gatekeeper: Halt if this isn't an official winning summary report
        if "winner" not in clean_text_payload and "queue" not in clean_text_payload:
            return

        winning_user_ids = []
        losing_user_ids = []

        # Download and compile live server name cache tables instantly
        if message.guild:
            try:
                await message.guild.query_members(limit=250, cache=True)
            except Exception as e:
                print(f"Member cache fault: {e}")

        # ADVANCED STEREOSCOPIC ID EXTRACTOR
        # Captures underlying Discord account number keys (<@12345678>) directly out of horizontal string lines
        winners_found = re.findall(r"<@!?(\d+)>(?=[^<>\n]*\+)", text_to_scan)
        losers_found = re.findall(r"<@!?(\d+)>(?=[^<>\n]*\-)", text_to_scan)

        # FALLBACK: Plain character string parser if NeatQueue prints usernames instead of mentions
        if not winners_found and not losers_found:
            for line in text_to_scan.split("\n"):
                if "+" in line:
                    plain_win = re.findall(r"@([^+\-\n\s\(]+)", line)
                    for name in plain_win:
                        member = discord.utils.get(message.guild.members, display_name=name) or discord.utils.get(message.guild.members, name=name)
                        if member: 
                            winning_user_ids.append(str(member.id))
                elif "-" in line:
                    plain_loss = re.findall(r"@([^+\-\n\s\(]+)", line)
                    for name in plain_loss:
                        member = discord.utils.get(message.guild.members, display_name=name) or discord.utils.get(message.guild.members, name=name)
                        if member: 
                            losing_user_ids.append(str(member.id))
        else:
            winning_user_ids = winners_found
            losing_user_ids = losers_found

        # 3. Apply database ledger rewards deposits
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

            # Save balances back permanently to GitHub cloud storage
            save_data()

            if awarded_mentions:
                await message.channel.send(
                    f"🪙 **NeatQueue Automated Link Synced!** Match column data processed.\n"
                    f"The following winners have been credited with **{reward} coins**: "
                    f"{', '.join(awarded_mentions)}"
                )

        await bot.process_commands(message)


# --- Start Services ---
keep_alive()
bot.run(TOKEN)


