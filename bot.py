import discord
from discord.ext import commands
from discord import app_commands
import os
import io
import json
import random
import threading
from datetime import datetime, timedelta
from flask import Flask

# --- Flask Keep-Alive Web Server ---
app = Flask('')

@app.route('/')
def home():
    return "🏒 Hockey Card & Match Queue System Online!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_web_server)
    t.daemon = True
    t.start()

# --- Configuration & Security ---
TOKEN = "MTUxOTIyNTQxNTg1ODc4NjM3NA.GoGCIf.zGFZKNrTY1tD1QmslHsmoL_96KKMsDJEC34ISg"  # Keep safe in private repo
STAFF_ROLE_NAME = "Staff"
DATABASE_FILE = "card_league_database.json"

# Ordered priority mapping for sorted card ledger structures
RARITY_ORDER = ["Specialty", "Otherworldly", "Juggernaut", "Pro", "Insane", "Epic", "Great", "Average"]

# --- Complete Consolidated Database System ---
DATA = {
    # Existing Season Setup Layout Tracks
    "season_title": "TBA League",
    "games_count": 0,
    "preseason": False,
    "teams": {},
    "players": {},
    "schedule": [],
    "playoffs": { "active": False, "best_of": 3, "rounds": {} },
    
    # Card Collector Engine Tracks
    "global_cards": {},  # card_id -> { name, rarity, overall, image_url }
    "users": {},         # user_id -> { coins, inventory: {card_id: count}, last_weekly, wins, losses }
    "matches": {},       # match_id -> { channel_id, type, team1: [], team2: [] }
    "next_match_id": 1,
    
    # Global Config Properties
    "config": {
        "pack_3_price": 50,
        "pack_5_price": 80,
        "pack_10_price": 150,
        "match_reward": 25,
        "queue_role_id": None,
        "match_role_id": None
    }
}

def save_data():
    with open(DATABASE_FILE, "w") as f:
        json.dump(DATA, f, indent=4)

def load_data():
    global DATA
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, "r") as f:
            DATA = json.load(f)

def verify_user(user_id_str, username="Unknown"):
    if user_id_str not in DATA["users"]:
        DATA["users"][user_id_str] = {
            "name": username, 
            "coins": 100, 
            "inventory": {},
            "last_weekly": None, 
            "wins": 0, 
            "losses": 0
        }

def is_staff():
    async def predicate(ctx):
        return any(role.name == STAFF_ROLE_NAME for role in ctx.author.roles)
    return commands.check(predicate)

# --- Bot Setup Initializer ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ==============================================================================
# --- CARD CREATION AND MANAGEMENT MODULES ---
# ==============================================================================

@bot.hybrid_command(name="addcard", description="Staff Command: Initialize a new player card profile into the master catalog")
@is_staff()
@app_commands.choices(rarity=[
    app_commands.Choice(name="Average (White)", value="Average"),
    app_commands.Choice(name="Great (Dark Purple)", value="Great"),
    app_commands.Choice(name="Epic (Emerald Green)", value="Epic"),
    app_commands.Choice(name="Insane (Royal Purple)", value="Insane"),
    app_commands.Choice(name="Pro (Gold)", value="Pro"),
    app_commands.Choice(name="Juggernaut (Bronze Orange)", value="Juggernaut"),
    app_commands.Choice(name="Otherworldly (Dark Red)", value="Otherworldly"),
    app_commands.Choice(name="Specialty (Silver)", value="Specialty")
])
async def addcard(ctx, player: discord.Member, rarity: str, overall: int, image_url: str = None):
    card_id = str(player.id)
    
    # Store card data profile
    DATA["global_cards"][card_id] = {
        "name": player.display_name,
        "rarity": rarity,
        "overall": max(1, min(overall, 99)),  # Lock range between 1-99
        "image_url": image_url or ""
    }

    
    save_data()
    await ctx.send(f"✅ Successfully created card profile for **{player.display_name}**! [{rarity} | {overall} OVR]")

# ==============================================================================
# --- CARD PACK ECONOMY & WEEKLY REWARDS MODULES ---
# ==============================================================================

def draw_random_cards(count: int) -> list:
    """Helper algorithm to select cards based on realistic tier drop probabilities."""
    if not DATA["global_cards"]:
        return []
        
    # Group every card in your database by its rarity string
    grouped_cards = {rarity: [] for rarity in RARITY_ORDER}
    for card_id, card_data in DATA["global_cards"].items():
        grouped_cards[card_data["rarity"]].append(card_id)
        
    # Define weight percentages (Average is easiest, Specialty/Otherworldly are rarest)
    rarity_weights = {
        "Average": 45.0,
        "Great": 25.0,
        "Epic": 15.0,
        "Insane": 8.0,
        "Pro": 4.0,
        "Juggernaut": 2.0,
        "Otherworldly": 0.8,
        "Specialty": 0.2
    }
    
    drawn_list = []
    # Loop for how many cards are inside the purchased pack container
    for _ in range(count):
        # Fallback list to make sure we don't pick from empty tiers
        available_rarities = [r for r in RARITY_ORDER if grouped_cards[r]]
        if not available_rarities:
            # If all categorized arrays are empty, just pull any card blindly
            drawn_list.append(random.choice(list(DATA["global_cards"].keys())))
            continue
            
        weights = [rarity_weights[r] for r in available_rarities]
        selected_rarity = random.choices(available_rarities, weights=weights, k=1)[0]
        
        # Pick a random player card from inside that chosen tier bracket
        random_card_id = random.choice(grouped_cards[selected_rarity])
        drawn_list.append(random_card_id)
        
    return drawn_list


@bot.hybrid_command(name="buypack", description="Public Command: Spend league coins to open card packs of varying sizes")
@app_commands.choices(pack_size=[
    app_commands.Choice(name="3 Player Pack", value=3),
    app_commands.Choice(name="5 Player Pack", value=5),
    app_commands.Choice(name="10 Player Pack", value=10)
])
async def buypack(ctx, pack_size: int):
    if not DATA["global_cards"]:
        return await ctx.send("❌ Store Unavailable: There are no player cards created in the system database yet.")
        
    u_id = str(ctx.author.id)
    verify_user(u_id, ctx.author.display_name)
    
    # Check price key mapping
    price_key = f"pack_{pack_size}_price"
    pack_cost = DATA["config"].get(price_key, 100)
    
    if DATA["users"][u_id]["coins"] < pack_cost:
        return await ctx.send(f"❌ Transaction Denied: You need **{pack_cost}** coins to buy this pack. Your Balance: **{DATA['users'][u_id]['coins']}** coins.")
        
    # Execute transaction deduction
    DATA["users"][u_id]["coins"] -= pack_cost
    
    # Process drawing engine math
    pulled_card_ids = draw_random_cards(pack_size)
    
    # Deposit items into user roster inventory dictionary
    results_display = []
    for c_id in pulled_card_ids:
        card = DATA["global_cards"][c_id]
        DATA["users"][u_id]["inventory"][c_id] = DATA["users"][u_id]["inventory"].get(c_id, 0) + 1
        results_display.append(f"📦 **[{card['rarity']}]** {card['name']} ({card['overall']} OVR)")
        
    save_data()
    
    embed = discord.Embed(
        title="🎉 Pack Opened Successfully!", 
        description=f"You opened a **{pack_size} Card Pack** for **{pack_cost} coins**.\n\n" + "\n".join(results_display),
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"New Wallet Balance: {DATA['users'][u_id]['coins']} coins")
    await ctx.send(embed=embed)


@bot.hybrid_command(name="claimweekly", description="Public Command: Claim your free weekly 3-player starter pack")
async def claimweekly(ctx):
    if not DATA["global_cards"]:
        return await ctx.send("❌ Store Unavailable: No card baseline entries exist to drop items from.")
        
    u_id = str(ctx.author.id)
    verify_user(u_id, ctx.author.display_name)
    
    current_time = datetime.now()
    last_claim_str = DATA["users"][u_id].get("last_weekly")
    
    # Validate cooldown safety windows
    if last_claim_str:
        last_claim_dt = datetime.fromisoformat(last_claim_str)
        cooldown_end = last_claim_dt + timedelta(days=7)
        if current_time < cooldown_end:
            time_remaining = cooldown_end - current_time
            days = time_remaining.days
            hours = time_remaining.seconds // 3600
            return await ctx.send(f"⏳ Cooldown Active: You already claimed your free drop. Try again in **{days} days and {hours} hours**.")
            
    # Draw rewards and update date strings
    pulled_card_ids = draw_random_cards(3)
    results_display = []
    for c_id in pulled_card_ids:
        card = DATA["global_cards"][c_id]
        DATA["users"][u_id]["inventory"][c_id] = DATA["users"][u_id]["inventory"].get(c_id, 0) + 1
        results_display.append(f"🎁 **[{card['rarity']}]** {card['name']} ({card['overall']} OVR)")
        
    DATA["users"][u_id]["last_weekly"] = current_time.isoformat()
    save_data()
    
    embed = discord.Embed(
        title="📅 Weekly Card Reward Claimed!", 
        description="Your free structural **3-Player Pack** has been deposited:\n\n" + "\n".join(results_display),
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


@bot.hybrid_command(name="setpackprices", description="Staff Command: Adjust purchase cost variables for league pack tiers")
@is_staff()
async def setpackprices(ctx, pack_3_cost: int, pack_5_cost: int, pack_10_cost: int):
    DATA["config"]["pack_3_price"] = max(1, pack_3_cost)
    DATA["config"]["pack_5_price"] = max(1, pack_5_cost)
    DATA["config"]["pack_10_price"] = max(1, pack_10_cost)
    
    save_data()
    await ctx.send(f"⚙️ **Pack Prices Configured!**\n• 3 Pack: `{pack_3_cost}` coins\n• 5 Pack: `{pack_5_cost}` coins\n• 10 Pack: `{pack_10_cost}` coins")
# ==============================================================================
# --- LEADERBOARD & METRIC TRACKING CONTROL MODULES ---
# ==============================================================================

@bot.hybrid_command(name="leaderboard", description="Public Command: Display top players sorted by competitive match victories")
async def leaderboard(ctx):
    if not DATA["users"]:
        return await ctx.send("📂 Database Empty: No active user profile data logs registered yet.")
        
    # Sort accounts by total wins descending, then lower losses as a tiebreaker
    sorted_users = sorted(
        DATA["users"].items(), 
        key=lambda x: (x[1].get("wins", 0), -x[1].get("losses", 0)), 
        reverse=True
    )
    
    # Filter out empty profiles to keep data clean
    active_board = [u for u in sorted_users if u[1].get("wins", 0) > 0 or u[1].get("losses", 0) > 0]
    
    if not active_board:
        return await ctx.send("📊 Leaderboard Empty: No matches have been recorded inside the ledger history files yet.")
        
    desc_lines = []
    # Build list display limit capped to top 10 profiles
    for idx, (u_id, u_data) in enumerate(active_board[:10], start=1):
        win_count = u_data.get("wins", 0)
        loss_count = u_data.get("losses", 0)
        
        # Calculate win ratio mathematics
        total_games = win_count + loss_count
        ratio = (win_count / total_games * 100) if total_games > 0 else 0.0
        
        desc_lines.append(
            f"**#{idx}** <@{u_id}> — **{win_count}** W | **{loss_count}** L _({ratio:.1f}% WR)_"
        )
        
    embed = discord.Embed(
        title="🏆 Matchmaking Queue Master Leaderboard", 
        description="\n".join(desc_lines), 
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)


@bot.hybrid_command(name="resetleaderboard", description="Staff Command: Wipe out all player win/loss statistics across the server ledger")
@is_staff()
async def resetleaderboard(ctx):
    if not DATA["users"]:
        return await ctx.send("❌ Error: User registry database folder is currently uninitialized.")
        
    # Clear variables while keeping their collection inventories intact
    for u_id in DATA["users"]:
        DATA["users"][u_id]["wins"] = 0
        DATA["users"][u_id]["losses"] = 0
        
    save_data()
    await ctx.send("🧹 **Leaderboard Cleared!** All player competitive matchmaking win and loss metrics have been reset to 0.")


@bot.hybrid_command(name="editmatchreward", description="Staff Command: Set the coin reward value handed out to winning teams")
@is_staff()
async def editmatchreward(ctx, new_reward: int):
    # Lock lower bounds threshold to 0 coins
    DATA["config"]["match_reward"] = max(0, new_reward)
    save_data()
    await ctx.send(f"🪙 **Match Reward Adjusted!** Winning teams will now receive `{new_reward}` coins per series.")



@bot.hybrid_command(name="removecard", description="Staff Command: Completely erase a card profile from the global master list")
@is_staff()
async def removecard(ctx, player: discord.Member):
    card_id = str(player.id)
    if card_id not in DATA["global_cards"]:
        return await ctx.send("❌ Error: That player does not have an active card profile in the catalog.")
        
    card_name = DATA["global_cards"][card_id]["name"]
    del DATA["global_cards"][card_id]
    
    # Clean up inventories so players don't hold corrupted data links
    for u_id in DATA["users"]:
        if card_id in DATA["users"][u_id]["inventory"]:
            del DATA["users"][u_id]["inventory"][card_id]
            
    save_data()
    await ctx.send(f"🗑️ Successfully purged **{card_name}**'s card profile from all databases completely.")


@bot.hybrid_command(name="changerarity", description="Staff Command: Update a player card's rarity tier and statistical overall value")
@is_staff()
@app_commands.choices(new_rarity=[
    app_commands.Choice(name="Average (White)", value="Average"),
    app_commands.Choice(name="Great (Dark Purple)", value="Great"),
    app_commands.Choice(name="Epic (Emerald Green)", value="Epic"),
    app_commands.Choice(name="Insane (Royal Purple)", value="Insane"),
    app_commands.Choice(name="Pro (Gold)", value="Pro"),
    app_commands.Choice(name="Juggernaut (Bronze Orange)", value="Juggernaut"),
    app_commands.Choice(name="Otherworldly (Dark Red)", value="Otherworldly"),
    app_commands.Choice(name="Specialty (Silver)", value="Specialty")
])
async def changerarity(ctx, player: discord.Member, new_rarity: str, new_overall: int):
    card_id = str(player.id)
    if card_id not in DATA["global_cards"]:
        return await ctx.send("❌ Error: No card profile found for this user. Create it first using `/addcard`.")
        
    DATA["global_cards"][card_id]["rarity"] = new_rarity
    DATA["global_cards"][card_id]["overall"] = max(1, min(new_overall, 99))
    
    save_data()
    await ctx.send(f"🔧 Updated **{player.display_name}**'s card baseline! New values: [{new_rarity} | {new_overall} OVR]")



# --- Rarity Metrics Configuration ---
RARITY_CONFIG = {
    "Average": {"color": discord.Color.from_rgb(255, 255, 255), "weight": 55, "label": "Average (White)"},
    "Great": {"color": discord.Color.from_rgb(128, 0, 128), "weight": 20, "label": "Great (Dark Purple)"},
    "Epic": {"color": discord.Color.from_rgb(80, 200, 120), "weight": 12, "label": "Epic (Emerald Green)"},
    "Insane": {"color": discord.Color.from_rgb(147, 112, 219), "weight": 6, "label": "Insane (Royal Purple)"},
    "Pro": {"color": discord.Color.from_rgb(255, 215, 0), "weight": 4, "label": "Pro (Gold)"},
    "Juggernaut": {"color": discord.Color.from_rgb(205, 127, 50), "weight": 2, "label": "Juggernaut (Bronze Orange)"},
    "Otherworldly": {"color": discord.Color.from_rgb(139, 0, 0), "weight": 0.8, "label": "Otherworldly (Dark Red)"},
    "Specialty": {"color": discord.Color.from_rgb(192, 192, 192), "weight": 0.2, "label": "Specialty (Silver)"}
}

# Ordered priority mapping for sorted ledger trees
RARITY_ORDER = ["Specialty", "Otherworldly", "Juggernaut", "Pro", "Insane", "Epic", "Great", "Average"]

# --- Database Core System ---
DATA = {
    "config": {
        "pack_3_price": 50,
        "pack_5_price": 80,
        "pack_10_price": 150,
        "match_reward": 25,
        "queue_role_id": None,
        "match_role_id": None
    },
    "global_cards": {},  # card_id -> { name, rarity, overall, image_url }
    "users": {},         # user_id -> { coins, inventory: {card_id: count}, last_weekly, wins, losses }
    "matches": {},       # match_id -> { channel_id, type, team1: [], team2: [] }
    "next_match_id": 1
}

def save_data():
    with open(DATABASE_FILE, "w") as f:
        json.dump(DATA, f, indent=4)

def load_data():
    global DATA
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, "r") as f:
            DATA = json.load(f)

def verify_user(user_id_str, username="Unknown"):
    if user_id_str not in DATA["users"]:
        DATA["users"][user_id_str] = {
            "name": username, "coins": 100, "inventory": {},
            "last_weekly": None, "wins": 0, "losses": 0
        }

# --- Bot Context Initialization ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="?", intents=intents)

def is_staff():
    async def predicate(ctx):
        return any(role.name == STAFF_ROLE_NAME for role in ctx.author.roles)
    return commands.check(predicate)

# --- Active Volatile Queue Containers ---
ACTIVE_QUEUES = {1: [], 2: [], 3: []}  # 1v1, 2v2, 3v3

@bot.event
async def on_ready():
    load_data()
    print(f"🏒 Card Collector Engine Running: Signed in as {bot.user}")
    try:
        await bot.tree.sync()
    except Exception as e:
        print(f"Sync error: {e}")

# ==============================================================================
# --- CARD SYSTEM COMMANDS ---
# ==============================================================================

@bot.hybrid_command(name="addcard", description="Staff Command: Register a new player framework card item blueprint")
@is_staff()
@app_commands.choices(rarity=[app_commands.Choice(name=v["label"], value=k) for k, v in RARITY_CONFIG.items()])
async def addcard(ctx, player: discord.Member, rarity: str, overall: int, image_attachment: discord.Attachment = None):
    card_id = str(player.id)
    img_url = image_attachment.url if image_attachment else None
    
    DATA["global_cards"][card_id] = {
        "name": player.display_name,
        "rarity": rarity,
        "overall": overall,
        "image_url": img_url
    }
    save_data()
    
    embed = discord.Embed(title="🎴 Card Blueprint Registered", color=RARITY_CONFIG[rarity]["color"])
    embed.add_field(name="Player Profile", value=player.mention)
    embed.add_field(name="Rarity Class", value=rarity)
    embed.add_field(name="Overall Score", value=str(overall))
    if img_url:
        embed.set_image(url=img_url)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="removecard", description="Staff Command: Delete a target player card blueprint from data maps completely")
@is_staff()
async def removecard(ctx, player: discord.Member):
    card_id = str(player.id)
    if card_id not in DATA["global_cards"]:
        return await ctx.send("❌ Error: That player does not have a card blueprint registered inside the catalog.")
        
    del DATA["global_cards"][card_id]
    for u_id in DATA["users"]:
        if card_id in DATA["users"][u_id]["inventory"]:
            del DATA["users"][u_id]["inventory"][card_id]
            
    save_data()
    await ctx.send(f"🗑️ Card Blueprint and user allocations completely removed for **{player.display_name}**.")

@bot.hybrid_command(name="editcardrarity", description="Staff Command: Adjust an active card blueprint's tier settings")
@is_staff()
@app_commands.choices(rarity=[app_commands.Choice(name=v["label"], value=k) for k, v in RARITY_CONFIG.items()])
async def editcardrarity(ctx, player: discord.Member, rarity: str):
    card_id = str(player.id)
    if card_id not in DATA["global_cards"]:
        return await ctx.send("❌ Error: Card blueprint not tracked inside system records.")
        
    DATA["global_cards"][card_id]["rarity"] = rarity
    save_data()
    await ctx.send(f"🔧 **Rarity Calibration Updated!** **{DATA['global_cards'][card_id]['name']}** moved to tier: `{rarity}`.")

# ==============================================================================
# --- ECONOMY & SHOP ECO-SYSTEM ---
# ==============================================================================

@bot.hybrid_command(name="claimweekly", description="Public Command: Request your complimentary free weekly 3-card pack allocation")
async def claimweekly(ctx):
    u_id = str(ctx.author.id)
    verify_user(u_id, ctx.author.display_name)
    user = DATA["users"][u_id]
    
    now = datetime.utcnow()
    if user["last_weekly"]:
        last_claimed = datetime.fromisoformat(user["last_weekly"])
        if now < last_claimed + timedelta(days=7):
            delta = (last_claimed + timedelta(days=7)) - now
            days, hours = delta.days, delta.seconds // 3600
            return await ctx.send(f"⏳ Cooldown lock active! You can claim again in **{days}d {hours}h**.")
            
    if not DATA["global_cards"]:
        return await ctx.send("❌ Inventory System Fault: No card blueprints have been registered to draw from yet.")
        
    drawn = []
    cards_pool = list(DATA["global_cards"].items())
    weights = [RARITY_CONFIG[c[1]["rarity"]]["weight"] for c in cards_pool]
    
    for _ in range(3):
        card = random.choices(cards_pool, weights=weights, k=1)[0]
        c_id, c_info = card[0], card[1]
        user["inventory"][c_id] = user["inventory"].get(c_id, 0) + 1
        drawn.append(f"• **[{c_info['rarity']}]** {c_info['name']} ({c_info['overall']} OVR)")
        
    user["last_weekly"] = now.isoformat()
    save_data()
    
    embed = discord.Embed(title="🎁 Weekly Free 3-Pack Opened!", description="\n".join(drawn), color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.hybrid_command(name="buypack", description="Public Command: Exchange currency coins to parse randomized card items")
@app_commands.choices(size=[app_commands.Choice(name="3 Cards", value=3), app_commands.Choice(name="5 Cards", value=5), app_commands.Choice(name="10 Cards", value=10)])
async def buypack(ctx, size: int):
    u_id = str(ctx.author.id)
    verify_user(u_id, ctx.author.display_name)
    user = DATA["users"][u_id]
    
    price_key = f"pack_{size}_price"
    cost = DATA["config"][price_key]
    
    if user["coins"] < cost:
        return await ctx.send(f"❌ Transaction Fault: Insufficient balance. Pack costs **{cost} coins**. Balance: `{user['coins']}`.")
        
    if not DATA["global_cards"]:
        return await ctx.send("❌ System Registry State Empty: No card targets created to spawn yet.")
        
    user["coins"] -= cost
    drawn = []
    cards_pool = list(DATA["global_cards"].items())
    weights = [RARITY_CONFIG[c[1]["rarity"]]["weight"] for c in cards_pool]
    
    for _ in range(size):
        card = random.choices(cards_pool, weights=weights, k=1)[0]
        c_id, c_info = card[0], card[1]
        user["inventory"][c_id] = user["inventory"].get(c_id, 0) + 1
        drawn.append(f"• **[{c_info['rarity']}]** {c_info['name']} ({c_info['overall']} OVR)")
        
    save_data()
    embed = discord.Embed(title=f"🛍️ {size}-Pack Card Draw Complete", description="\n".join(drawn), color=discord.Color.gold())
    embed.set_footer(text=f"Spent: {cost} coins | Remaining Balance: {user['coins']}")
    await ctx.send(embed=embed)

@bot.hybrid_command(name="editprices", description="Staff Command: Calibrate configuration price thresholds for card store inventories")
@is_staff()
async def editprices(ctx, pack_3: int, pack_5: int, pack_10: int):
    DATA["config"]["pack_3_price"] = pack_3
    DATA["config"]["pack_5_price"] = pack_5
    DATA["config"]["pack_10_price"] = pack_10
    save_data()
    await ctx.send(f"🔧 **Store Cost Parameters Calibrated!**\n• 3-Pack: `{pack_3}`\n• 5-Pack: `{pack_5}`\n• 10-Pack: `{pack_10}`")

@bot.hybrid_command(name="editcoins", description="Staff Command: Modify currency files ledger values for a target player")
@is_staff()
@app_commands.choices(action=[
    app_commands.Choice(name="Give", value="give"), 
    app_commands.Choice(name="Take", value="take")
])
async def editcoins(ctx, action: str, player: discord.Member, amount: int):
    p_id = str(player.id)
    verify_user(p_id, player.display_name)
    
    if action == "give":
        DATA["users"][p_id]["coins"] += amount
    else:
        DATA["users"][p_id]["coins"] = max(0, DATA["users"][p_id]["coins"] - amount)
        
    save_data()
    await ctx.send(f"💰 Balance adjusted for {player.mention}. New Wallet Balance: {DATA['users'][p_id]['coins']} coins.")

# ==============================================================================
# --- LEDGER & INVENTORY INSPECTION TRACKERS ---
# ==============================================================================

@bot.hybrid_command(name="catalog", description="Public Command: Inspect card directory matrix profiles inside descending index pagination")
async def catalog(ctx, page: int = 1):
    if not DATA["global_cards"]:
        return await ctx.send("📂 Directory Empty: Card frameworks completely uninitialized.")
        
    sorted_cards = sorted(DATA["global_cards"].values(), key=lambda x: (RARITY_ORDER.index(x["rarity"]), -x["overall"]))
    
    per_page = 8
    max_pages = max(1, (len(sorted_cards) + per_page - 1) // per_page)
    page = max(1, min(page, max_pages))
    
    start = (page - 1) * per_page
    end = start + per_page
    
    desc_lines = []
    for c in sorted_cards[start:end]:
        desc_lines.append(f"• [{c['rarity']}] {c['name']} - {c['overall']} OVR")
        
    embed = discord.Embed(title="🏒 League Card Master Catalog", description="\n".join(desc_lines), color=discord.Color.blue())
    embed.set_footer(text=f"Page {page}/{max_pages} | Total Item Profiles: {len(sorted_cards)}")
    await ctx.send(embed=embed)


@bot.hybrid_command(name="inventory", description="Public Command: View active owned personal card stack layout rosters")
async def inventory(ctx, player: discord.Member = None):
    target = player or ctx.author
    t_id = str(target.id)
    verify_user(t_id, target.display_name)
    
    inv = DATA["users"][t_id]["inventory"]
    owned_cards = [c_id for c_id, count in inv.items() if count > 0 and c_id in DATA["global_cards"]]
    
    if not owned_cards:
        return await ctx.send(f"📂 {target.display_name} currently does not own any cataloged cards.")
        
    sorted_owned = sorted(owned_cards, key=lambda x: (RARITY_ORDER.index(DATA["global_cards"][x]["rarity"]), -DATA["global_cards"][x]["overall"]))
    
    desc_lines = []
    for c_id in sorted_owned:
        c = DATA["global_cards"][c_id]
        desc_lines.append(f"• [{c['rarity']}] {c['name']} ({c['overall']} OVR) x{inv[c_id]}")
        
    embed = discord.Embed(title=f"🎒 Card Roster Vault: {target.display_name}", description="\n".join(desc_lines), color=discord.Color.dark_theme())
    embed.add_field(name="Coins", value=f"{DATA['users'][t_id]['coins']} 🪙")
    await ctx.send(embed=embed)

# ==============================================================================
# --- INTERACTION TRADING MODULES ---
# ==============================================================================

class TradeView(discord.ui.View):
    def __init__(self, sender, receiver, s_card_id, r_card_id):
        super().__init__(timeout=120)
        self.sender = sender
        self.receiver = receiver
        self.s_card_id = s_card_id
        self.r_card_id = r_card_id

    @discord.ui.button(label="Accept Trade", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.receiver.id:
            return await interaction.response.send_message("❌ You are not the recipient party targeted inside this trade layout loop.", ephemeral=True)
            
        s_id, r_id = str(self.sender.id), str(self.receiver.id)
        s_inv = DATA["users"][s_id]["inventory"]
        r_inv = DATA["users"][r_id]["inventory"]
        
        if s_inv.get(self.s_card_id, 0) < 1 or r_inv.get(self.r_card_id, 0) < 1:
            return await interaction.response.send_message("❌ Transaction Aborted: One or both parties no longer hold the trading target card allocation requirements.", ephemeral=True)
            
        s_inv[self.s_card_id] -= 1
        r_inv[self.r_card_id] -= 1
        
        s_inv[self.r_card_id] = s_inv.get(self.r_card_id, 0) + 1
        r_inv[self.s_card_id] = r_inv.get(self.s_card_id, 0) + 1
        
        save_data()
        self.stop()
        await interaction.response.edit_message(content=f"✅ Trade Executed! Swap transaction finalized cleanly between {self.sender.mention} and {self.receiver.mention}.", view=None)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in (self.receiver.id, self.sender.id):
            return await interaction.response.send_message("❌ Access Bound Violation.", ephemeral=True)
            
        self.stop()
        await interaction.response.edit_message(content="❌ Trade Cancelled! Interaction cancelled by active processing authority.", view=None)


@bot.hybrid_command(name="trade", description="Public Command: Initiate an asset card swap proposal with another player")
async def trade(ctx, target_player: discord.Member, your_card: discord.Member, their_card: discord.Member):
    if target_player == ctx.author:
        return await ctx.send("❌ Execution Blocked: You cannot cycle asset properties back into your own network matrix file.")
        
    s_id, r_id = str(ctx.author.id), str(target_player.id)
    yc_id, tc_id = str(your_card.id), str(their_card.id)
    
    verify_user(s_id, ctx.author.display_name)
    verify_user(r_id, target_player.display_name)
    
    if DATA["users"][s_id]["inventory"].get(yc_id, 0) < 1:
        return await ctx.send(f"❌ Transaction Fault: You do not own a card blueprint profile for {your_card.display_name} inside your vault registry.")
        
    if DATA["users"][r_id]["inventory"].get(tc_id, 0) < 1:
        return await ctx.send(f"❌ Transaction Fault: {target_player.display_name} does not own the requested asset card for {their_card.display_name}.")
        
    view = TradeView(ctx.author, target_player, yc_id, tc_id)
    await ctx.send(f"🤝 {target_player.mention}, {ctx.author.mention} wants to trade their [{DATA['global_cards'][yc_id]['rarity']}] {your_card.display_name} for your [{DATA['global_cards'][tc_id]['rarity']}] {their_card.display_name}.", view=view)

# ==============================================================================
# --- MATCH ENGINE STACK AND QUEUE SYSTEM ---
# ==============================================================================

class QueueView(discord.ui.View):
    def __init__(self, q_type):
        super().__init__(timeout=None)
        self.q_type = q_type

    @discord.ui.button(label="Join Queue", style=discord.ButtonStyle.primary, custom_id="join_queue_btn")
    async def join_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        u_id = interaction.user.id
        queue = ACTIVE_QUEUES[self.q_type]
        
        if u_id in queue:
            return await interaction.response.send_message("⚠️ Tracking State: You are already registered inside this specific match waiting pool loop.", ephemeral=True)
            
        queue.append(u_id)
        
        # Allocate Queue Roles if config tracks them
        if DATA["config"]["queue_role_id"]:
            role = interaction.guild.get_role(int(DATA["config"]["queue_role_id"]))
            if role:
                await interaction.user.add_roles(role)
                
        await interaction.response.send_message(f"✅ Added to {self.q_type}v{self.q_type} Queue ({len(queue)}/{self.q_type * 2})", ephemeral=False)
        
        if len(queue) >= (self.q_type * 2):
            await trigger_match_initialization(interaction.guild, self.q_type)


async def trigger_match_initialization(guild, q_type):
    queue = ACTIVE_QUEUES[q_type].copy()
    ACTIVE_QUEUES[q_type].clear()
    random.shuffle(queue)
    
    team_size = q_type
    team1_ids = queue[:team_size]
    team2_ids = queue[team_size:]
    
    m_id = DATA["next_match_id"]
    DATA["next_match_id"] += 1
    
    # Strip queue roles and add Match Active tracking configurations
    q_role = guild.get_role(int(DATA["config"]["queue_role_id"])) if DATA["config"]["queue_role_id"] else None
    m_role = guild.get_role(int(DATA["config"]["match_role_id"])) if DATA["config"]["match_role_id"] else None
    
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
        "team2": team2_ids
    }
    save_data()
    
    embed = discord.Embed(title=f"⚡ Match Series #{m_id} Initialized!", color=discord.Color.red(), description="Format: Best of 3 Matches Series Blueprint Setup")
    embed.add_field(name="🟢 Team 1 (Home)", value="\n".join(t1_names) or "Empty Thread", inline=True)
    embed.add_field(name="🔵 Team 2 (Away)", value="\n".join(t2_names) or "Empty Thread", inline=True)
    embed.set_footer(text="Staff must execute /reportmatch to resolve this match data index tree manually.")
    
    await channel.send(embed=embed)


@bot.hybrid_command(name="setupqueue", description="Staff Command: Spawn a dynamic interactive match-making interface link widget")
@is_staff()
@app_commands.choices(format_size=[
    app_commands.Choice(name="1v1 Bracket", value=1), 
    app_commands.Choice(name="2v2 Bracket", value=2), 
    app_commands.Choice(name="3v3 Bracket", value=3)
])
async def setupqueue(ctx, format_size: int):
    view = QueueView(format_size)
    embed = discord.Embed(
        title=f"🏒 {format_size}v{format_size} Competitive League Queue", 
        description="Select the action node trigger button below to register your tracking spot inside the waiting roster pool.", 
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=view)

# ==============================================================================
# --- STAFF ADMINISTRATION UTILITY & LOGISTICS CONTROL ENDPOINTS ---
# ==============================================================================

@bot.hybrid_command(name="reportmatch", description="Staff Command: Record final scores, assign rewards, and safely decommission channels")
@is_staff()
@app_commands.choices(winner=[
    app_commands.Choice(name="Team 1 (Home)", value=1), 
    app_commands.Choice(name="Team 2 (Away)", value=2)
])
async def reportmatch(ctx, match_number: int, winner: int):
    m_str = str(match_number)
    if m_str not in DATA["matches"]:
        return await ctx.send("❌ Processing Error: Target identifier match reference mapping missing inside dictionary registry files.")
        
    match = DATA["matches"][m_str]
    win_team = match["team1"] if winner == 1 else match["team2"]
    lose_team = match["team2"] if winner == 1 else match["team1"]
    reward = DATA["config"]["match_reward"]
    
    # Process wallet arrays and update win records
    for p_id in win_team:
        p_str = str(p_id)
        verify_user(p_str, f"User {p_str}")
        DATA["users"][p_str]["coins"] += reward
        DATA["users"][p_str]["wins"] += 1
        
    for p_id in lose_team:
        p_str = str(p_id)
        verify_user(p_str, f"User {p_str}")
        DATA["users"][p_str]["losses"] += 1
        
    # Strip Active Match Role assignments
    m_role = ctx.guild.get_role(int(DATA["config"]["match_role_id"])) if DATA["config"]["match_role_id"] else None
    if m_role:
        for p_id in (win_team + lose_team):
            member = ctx.guild.get_member(p_id)
            if member: 
                await member.remove_roles(m_role)
                
    # Purge allocated channel targets securely
    channel = ctx.guild.get_channel(match["channel_id"])
    if channel:
        await channel.delete(reason=f"Administrative Closure: Match #{match_number} completed.")
        
    del DATA["matches"][m_str]
    save_data()
    await ctx.send(f"✅ Match #{match_number} Logged! Winners received {reward} coins. Active instance room successfully dissolved.")


@bot.hybrid_command(name="cancelmatch", description="Staff Command: Terminate an active match instance and purge the designated text room")
@is_staff()
async def cancelmatch(ctx, match_number: int):
    m_str = str(match_number)
    if m_str not in DATA["matches"]:
        return await ctx.send("❌ Error: Target match identifier not tracking inside active operational trees.")
        
    match = DATA["matches"][m_str]
    m_role = ctx.guild.get_role(int(DATA["config"]["match_role_id"])) if DATA["config"]["match_role_id"] else None
    
    if m_role:
        for p_id in (match["team1"] + match["team2"]):
            member = ctx.guild.get_member(p_id)
            if member: 
                await member.remove_roles(m_role)
                
    channel = ctx.guild.get_channel(match["channel_id"])
    if channel: 
        await channel.delete(reason="Administrative Override Action: Cancel Match standard procedure invocation.")
        
    del DATA["matches"][m_str]
    save_data()
    await ctx.send(f"🛑 Match #{match_number} Cancelled! Structural tracking parameters erased.")


@bot.hybrid_command(name="substitute", description="Staff Command: Swap an active player out for a replacement substitute player")
@is_staff()
async def substitute(ctx, match_number: int, current_player: discord.Member, new_player: discord.Member):
    m_str = str(match_number)
    if m_str not in DATA["matches"]:
        return await ctx.send("❌ Target match mapping instance completely dead.")
        
    match = DATA["matches"][m_str]
    team_key = None
    
    if current_player.id in match["team1"]: 
        team_key = "team1"
    elif current_player.id in match["team2"]: 
        team_key = "team2"
        
    if not team_key:
        return await ctx.send(f"❌ Error: {current_player.display_name} is not assigned to this match.")
        
    idx = match[team_key].index(current_player.id)
    match[team_key][idx] = new_player.id
    save_data()
    
    # Sync permissions
    channel = ctx.guild.get_channel(match["channel_id"])
    if channel:
        await channel.set_permissions(current_player, overwrite=None)
        await channel.set_permissions(new_player, read_messages=True, send_messages=True)
        
    m_role = ctx.guild.get_role(int(DATA["config"]["match_role_id"])) if DATA["config"]["match_role_id"] else None
    if m_role:
        await current_player.remove_roles(m_role)
        await new_player.add_roles(m_role)
        
    await ctx.send(f"🔄 Roster Swap Complete! {new_player.mention} replaces {current_player.mention} in Match #{match_number}.")


@bot.hybrid_command(name="removefromqueue", description="Staff Command: Eject a user from all volatile waiting queues manually")
@is_staff()
async def removefromqueue(ctx, player: discord.Member):
    removed = False
    for q_type, users in ACTIVE_QUEUES.items():
        if player.id in users:
            users.remove(player.id)
            removed = True
            
    q_role = ctx.guild.get_role(int(DATA["config"]["queue_role_id"])) if DATA["config"]["queue_role_id"] else None
    if q_role: 
        await player.remove_roles(q_role)
        
    if removed: 
        await ctx.send(f"🗑️ Ejected {player.mention} from active matchmaking waiting queues safely.")
    else: 
        await ctx.send("⚠️ State: Player was not found in any active queue containers.")


@bot.hybrid_command(name="configureroles", description="Staff Command: Map tracking roles configuration identifiers")
@is_staff()
async def configureroles(ctx, queue_role: discord.Role, match_role: discord.Role):
    DATA["config"]["queue_role_id"] = str(queue_role.id)
    DATA["config"]["match_role_id"] = str(match_role.id)
    save_data()
    await ctx.send(f"⚙️ Configurations Setup Success: Queue tracking mapped to {queue_role.name} and Active Match tracking mapped to {match_role.name}.")

# --- Start Services ---
keep_alive()
bot.run(TOKEN)


