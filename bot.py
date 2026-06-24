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
GITHUB_REPO = "hockey-bot"
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
    """Saves data locally and automatically syncs it back to your GitHub Repo permanently."""
    try:
        with open(DATABASE_FILE, "w") as f:
            json.dump(DATA, f, indent=4)
    except Exception as e:
        print(f"Local Save Error: {e}")

    if not GH_TOKEN:
        return

    try:
        url = f"https://github.com{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
        headers = {"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        
        get_req = requests.get(url, headers=headers)
        sha = get_req.json().get("sha") if get_req.status_code == 200 else None
        
        content_bytes = json.dumps(DATA, indent=4).encode('utf-8')
        encoded_content = base64.b64encode(content_bytes).decode('utf-8')
        
        payload = {"message": "🔄 Automated Live Database State Backup Sync", "content": encoded_content}
        if sha: 
            payload["sha"] = sha
            
        put_req = requests.put(url, headers=headers, json=payload)
        if put_req.status_code in (200, 201):
            print("💾 Database securely backed up to GitHub Repository successfully!")
        else:
            print(f"GitHub Sync Failed: {put_req.text}")
    except Exception as e:
        print(f"GitHub Cloud Sync Fault: {e}")

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

@bot.event
async def on_ready():
    load_data()
    keep_alive()
    print(f"🏒 Bot Online: Connected as {bot.user}")
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
# --- DYNAMIC MATCHMAKING QUEUE & VOTING RESOLUTION FRAMEWORK ---
# ==============================================================================

# ==============================================================================
# --- COMPETITIVE MATCHMAKING QUEUE ENGINE ---
# ==============================================================================

def make_queue_embed(q_type: int) -> discord.Embed:
    """Helper generator to render the active waiting pool display layout."""
    player_ids = ACTIVE_QUEUES.get(q_type, [])
    capacity = q_type * 2
    
    if player_ids:
        player_list_str = "\n".join(f"• <@{p_id}>" for p_id in player_ids)
    else:
        player_list_str = "_No players currently waiting in this bracket pool._"
        
    embed = discord.Embed(
        title=f"🏒 {q_type}v{q_type} Competitive Matchmaking Queue",
        description="Select an action node trigger below to manage your registration slot inside the active waiting roster tree.",
        color=discord.Color.blue()
    )
    embed.add_field(name=f"👥 Registered Competitors ({len(player_ids)}/{capacity})", value=player_list_str, inline=False)
    embed.set_footer(text="Match series initialization automatically triggers once player allocation bounds are full.")
    return embed


# ==============================================================================
# --- AUTOMATED SELF-REPORTING MATCH VOTING SYSTEM ---
# ==============================================================================

class MatchVoteView(discord.ui.View):
    def __init__(self, match_id: str):
        super().__init__(timeout=None)
        self.match_id = match_id

    async def check_series_resolution(self, interaction: discord.Interaction):
        match = DATA["matches"][self.match_id]
        t1_votes = len(match["votes_t1"])
        t2_votes = len(match["votes_t2"])
        required_threshold = match["vote_threshold"]

        if t1_votes >= required_threshold:
            await self.resolve_match_victory(interaction, winner_team=1)
        elif t2_votes >= required_threshold:
            await self.resolve_match_victory(interaction, winner_team=2)

    async def resolve_match_victory(self, interaction: discord.Interaction, winner_team: int):
        match = DATA["matches"][self.match_id]
        win_ids = match["team1"] if winner_team == 1 else match["team2"]
        lose_ids = match["team2"] if winner_team == 1 else match["team1"]
        reward = DATA["config"].get("match_reward", 25)

        for p_id in win_ids:
            p_str = str(p_id)
            verify_user(p_str, f"Player {p_str}")
            DATA["users"][p_str]["coins"] += reward
            DATA["users"][p_str]["wins"] += 1

        for p_id in lose_ids:
            p_str = str(p_id)
            verify_user(p_str, f"Player {p_str}")
            DATA["users"][p_str]["losses"] += 1

        m_role_id = DATA["config"].get("match_role_id")
        m_role = interaction.guild.get_role(int(m_role_id)) if m_role_id else None
        if m_role:
            for p_id in (win_ids + lose_ids):
                member = interaction.guild.get_member(p_id)
                if member: 
                    await member.remove_roles(m_role)

        channel = interaction.guild.get_channel(match["channel_id"])
        del DATA["matches"][self.match_id]
        save_data()

        await interaction.channel.send(f"🎉 **Match Series Clear!** Consensus reached. Team {winner_team} wins the match! Competitors awarded `{reward}` coins.")
        if channel:
            await channel.delete(reason=f"Automated System Resolution completed via user vote.")

    @discord.ui.button(label="Vote Team 1 (Home) Won", style=discord.ButtonStyle.success, custom_id="vote_team_1_btn")
    async def vote_t1(self, interaction: discord.Interaction, button: discord.ui.Button):
        m_str = self.match_id
        if m_str not in DATA["matches"]:
            return await interaction.response.send_message("❌ This active match has already been resolved.", ephemeral=True)

        match = DATA["matches"][m_str]
        all_players = match["team1"] + match["team2"]

        if interaction.user.id not in all_players:
            return await interaction.response.send_message("❌ Access Restricted: Only active competitors can vote.", ephemeral=True)

        u_id = interaction.user.id
        if u_id in match["votes_t1"] or u_id in match["votes_t2"]:
            return await interaction.response.send_message("⚠️ You have already submitted a vote for this match.", ephemeral=True)

        match["votes_t1"].append(u_id)
        save_data()

        await interaction.response.send_message(f"🗳️ Vote recorded for **Team 1**. Standings: (🟢 {len(match['votes_t1'])} / 🔵 {len(match['votes_t2'])})", ephemeral=False)
        await self.check_series_resolution(interaction)

    @discord.ui.button(label="Vote Team 2 (Away) Won", style=discord.ButtonStyle.danger, custom_id="vote_team_2_btn")
    async def vote_t2(self, interaction: discord.Interaction, button: discord.ui.Button):
        m_str = self.match_id
        if m_str not in DATA["matches"]:
            return await interaction.response.send_message("❌ This active match has already been resolved.", ephemeral=True)

        match = DATA["matches"][m_str]
        all_players = match["team1"] + match["team2"]

        if interaction.user.id not in all_players:
            return await interaction.response.send_message("❌ Access Restricted: Only active competitors can vote.", ephemeral=True)

        u_id = interaction.user.id
        if u_id in match["votes_t1"] or u_id in match["votes_t2"]:
            return await interaction.response.send_message("⚠️ You have already submitted a vote for this match.", ephemeral=True)

        match["votes_t2"].append(u_id)
        save_data()

        await interaction.response.send_message(f"🗳️ Vote recorded for **Team 2**. Standings: (🟢 {len(match['votes_t1'])} / 🔵 {len(match['votes_t2'])})", ephemeral=False)
        await self.check_series_resolution(interaction)


# ==============================================================================
# --- COMPETITIVE MATCHMAKING QUEUE ENGINE ---
# ==============================================================================

def make_queue_embed(q_type: int) -> discord.Embed:
    player_ids = ACTIVE_QUEUES.get(q_type, [])
    capacity = q_type * 2
    
    if player_ids:
        player_list_str = "\n".join(f"• <@{p_id}>" for p_id in player_ids)
    else:
        player_list_str = "_No players currently waiting in this bracket pool._"
        
    embed = discord.Embed(
        title=f"🏒 {q_type}v{q_type} Competitive Matchmaking Queue",
        description="Select an action node trigger below to manage your registration slot inside the active waiting roster tree.",
        color=discord.Color.blue()
    )
    embed.add_field(name=f"👥 Registered Competitors ({len(player_ids)}/{capacity})", value=player_list_str, inline=False)
    embed.set_footer(text="Match series initialization automatically triggers once player allocation bounds are full.")
    return embed


class QueueView(discord.ui.View):
    def __init__(self, q_type: int):
        super().__init__(timeout=None)
        self.q_type = q_type

    @discord.ui.button(label="Join Queue", style=discord.ButtonStyle.primary, custom_id="join_queue_node_btn")
    async def join_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        u_id = interaction.user.id
        queue = ACTIVE_QUEUES[self.q_type]
        capacity = self.q_type * 2
        
        if u_id in queue:
            return await interaction.response.send_message("⚠️ Tracking Error: You are already registered inside this specific match waiting pool loop.", ephemeral=True)
            
        queue.append(u_id)
        
        q_role_id = DATA["config"].get("queue_role_id")
        if q_role_id:
            role = interaction.guild.get_role(int(q_role_id))
            if role: 
                await interaction.user.add_roles(role)
                
        await interaction.response.edit_message(embed=make_queue_embed(self.q_type), view=self)
        
        if len(queue) >= capacity:
            await trigger_match_initialization(interaction, self.q_type)

    @discord.ui.button(label="Leave Queue", style=discord.ButtonStyle.danger, custom_id="leave_queue_node_btn")
    async def leave_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        u_id = interaction.user.id
        queue = ACTIVE_QUEUES[self.q_type]
        
        if u_id not in queue:
            return await interaction.response.send_message("❌ Error: You are not currently registered inside this active queue waiting tree.", ephemeral=True)
            
        queue.remove(u_id)
        
        q_role_id = DATA["config"].get("queue_role_id")
        if q_role_id:
            role = interaction.guild.get_role(int(q_role_id))
            if role: 
                await interaction.user.remove_roles(role)
                
        await interaction.response.edit_message(embed=make_queue_embed(self.q_type), view=self)


async def trigger_match_initialization(interaction: discord.Interaction, q_type: int):
    guild = interaction.guild
    origin_channel = interaction.channel
    
    queue = ACTIVE_QUEUES[q_type].copy()
    ACTIVE_QUEUES[q_type].clear()
    
    fresh_view = QueueView(q_type)
    fresh_embed = make_queue_embed(q_type)
    await origin_channel.send(embed=fresh_embed, view=fresh_view)
    
    random.shuffle(queue)
    team_size = q_type
    team1_ids = queue[:team_size]
    team2_ids = queue[team_size:]
    
    m_id = DATA["next_match_id"]
    DATA["next_match_id"] += 1
    
    q_role_id = DATA["config"].get("queue_role_id")
    m_role_id = DATA["config"].get("match_role_id")
    
    q_role = guild.get_role(int(q_role_id)) if q_role_id else None
    m_role = guild.get_role(int(m_role_id)) if m_role_id else None
    
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True)
    }
    
    for p_id in queue:
        member = guild.get_member(p_id)
        if member:
            overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            if q_role: 
                await member.remove_roles(q_role)
            if m_role: 
                await member.add_roles(m_role)
                
    category = discord.utils.get(guild.categories, name="Active Matches")
    if not category:
        category = await guild.create_category("Active Matches")
        
    channel = await guild.create_text_channel(name=f"match-{m_id}", category=category, overwrites=overwrites)
    
    t1_names = [guild.get_member(p).display_name for p in team1_ids if guild.get_member(p)]
    t2_names = [guild.get_member(p).display_name for p in team2_ids if guild.get_member(p)]
    
    DATA["matches"][str(m_id)] = {
        "channel_id": channel.id,
        "type": q_type,
        "team1": team1_ids,
        "team2": team2_ids,
        "votes_t1": [],
        "votes_t2": [],
        "vote_threshold": q_type + 1
    }
    save_data()
    
    embed = discord.Embed(
        title=f"⚡ Match Series #{m_id} Initialized!", 
        color=discord.Color.red(), 
        description="Format Setup Type: **Best of 3 Matches Series Blueprint**\n\nUse the buttons below to lock in the self-reported winner!"
    )
    embed.add_field(name="🟢 Team 1 (Home)", value="\n".join(t1_names) or "Empty Thread Roster", inline=True)
    embed.add_field(name="🔵 Team 2 (Away)", value="\n".join(t2_names) or "Empty Thread Roster", inline=True)
    embed.set_footer(text="Competitors must cross-verify results to execute channel closures.")
    
    vote_view = MatchVoteView(str(m_id))
    await channel.send(content=" ".join(f"<@{p_id}>" for p_id in queue), embed=embed, view=vote_view)


@bot.hybrid_command(name="setupqueue", description="Staff Command: Spawn a dynamic interactive match-making interface link widget")
@is_staff()
@app_commands.choices(format_size=[
    app_commands.Choice(name="1v1 Bracket Match", value=1), 
    app_commands.Choice(name="2v2 Bracket Match", value=2), 
    app_commands.Choice(name="3v3 Bracket Match", value=3)
])
async def setupqueue(ctx, format_size: int):
    view = QueueView(format_size)
    embed = make_queue_embed(format_size)
    await ctx.send(embed=embed, view=view)


# ==============================================================================
# --- NEATQUE RESULT SCRAPER EVENT LISTENER ---
# ==============================================================================

@bot.event
async def on_message(message: discord.Message):
    # 1. Ignore messages sent by your own bot to prevent endless loops
    if message.author == bot.user:
        return

    # 2. Strict Filter: Listen if the sender is NeatQue's ID or Name
    if message.author.id == 857633321064595466 or "neatque" in message.author.name.lower():
        text_to_scan = ""
        
        # Scrape raw text content
        if message.content:
            text_to_scan += message.content + "\n"
            
        # Scrape EVERY string layer inside a Discord Embed Box
        if message.embeds:
            for embed in message.embeds:
                if embed.title:
                    text_to_scan += embed.title + "\n"
                if embed.description:
                    text_to_scan += embed.description + "\n"
                if embed.author and embed.author.name:
                    text_to_scan += embed.author.name + "\n"
                if embed.footer and embed.footer.text:
                    text_to_scan += embed.footer.text + "\n"
                for field in embed.fields:
                    text_to_scan += f"{field.name} {field.value}\n"

        winning_user_ids = []
        losing_user_ids = []

        # 🚨 FIX: Force the bot to download and cache the live server member list!
        # Without this line, message.guild.members returns 0 accounts, breaking name matching.
        if message.guild:
            try:
                await message.guild.query_members(limit=100, cache=True)
            except Exception as e:
                print(f"Member chunking fault: {e}")

        # 🎯 ADVANCED CLEAN NAME PARSER
        # Splitting the text by line to inspect exactly who got a + or a -
        for line in text_to_scan.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Check if this line indicates a stats change
            has_plus = "+" in line
            has_minus = "-" in line
            
            if not has_plus and not has_minus:
                continue

            # Clean out common symbols, numbers in parentheses, and the trailing point metrics
            # Example text conversion: "@Tent💍🐗 +40.0 (33.7)" -> "@Tent💍🐗"
            clean_line = re.sub(r"\([^\)]+\)", "", line)  # Removes everything inside parenthetical bounds (...)
            clean_line = re.sub(r"[\+\-]\s*\d+[\d\.]*", "", clean_line)  # Removes the points flag change (+35.3, -17.0, etc.)
            clean_line = clean_line.replace("@", "").strip()  # Clears out the literal symbol prefix text

            if not clean_line:
                continue

            # Match the cleaned plain text string directly to the freshly downloaded server member cache
            member = discord.utils.get(message.guild.members, display_name=clean_line) or \
                     discord.utils.get(message.guild.members, name=clean_line)
            
            if member:
                p_id_str = str(member.id)
                if has_plus and p_id_str not in winning_user_ids:
                    winning_user_ids.append(p_id_str)
                elif has_minus and p_id_str not in losing_user_ids:
                    losing_user_ids.append(p_id_str)

        # 3. Award the matching users inside your league database ledger
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

            # Commit updates directly back to GitHub Cloud data files
            save_data()

            if awarded_mentions:
                await message.channel.send(
                    f"🪙 **NeatQue Automated Link Synced!**\n"
                    f"The following match winners have been credited with **{reward} coins**: "
                    f"{', '.join(awarded_mentions)}"
                )

    await bot.process_commands(message)


# --- Start Services ---
keep_alive()
bot.run(TOKEN)




