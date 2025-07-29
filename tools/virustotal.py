import os
import html
import asyncio
import hashlib
import requests
import re
import base64
from pyrogram.types import Message, LinkPreviewOptions
from dotenv import load_dotenv

from app import BOT, bot

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.dirname(SCRIPT_DIR)
ENV_PATH = os.path.join(MODULES_DIR, "extra_config.env")
load_dotenv(dotenv_path=ENV_PATH)

VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY") 

TEMP_DIR = "temp_virustotal/"
os.makedirs(TEMP_DIR, exist_ok=True)
ERROR_VISIBLE_DURATION = 8
VT_API_URL = "https://www.virustotal.com/api/v3"

def calculate_sha256(file_path: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def is_url(text: str) -> bool:
    return text.lower().startswith(("http://", "https://"))

def is_ip(text: str) -> bool:
    return bool(re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", text))

def is_domain(text: str) -> bool:
    return "." in text and "/" not in text and not is_ip(text)

def format_vt_report(data: dict, scan_type: str, resource: str) -> str:
    """Creates a standardized report from VirusTotal API data."""
    report_lines = [f"<b>VirusTotal {scan_type.capitalize()} Report:</b>"]
    
    stats = data.get("last_analysis_stats", {})
    malicious = stats.get("malicious", 0)
    suspicious = stats.get("suspicious", 0)
    detections = malicious + suspicious
    total_scans = sum(stats.values())
    
    report_lines.append(f"<b>  - Detections:</b> <code>{detections} / {total_scans}</code>")
    
    if malicious > 0:
        report_lines.append("<b>  - Status:</b> 🔴 Malicious")
    elif suspicious > 0:
        report_lines.append("<b>  - Status:</b> 🟠 Suspicious")
    else:
        report_lines.append("<b>  - Status:</b> 🟢 Clean")

    if scan_type == "file":
        report_lines.append(f"<b>  - Type:</b> <code>{data.get('type_description', 'N/A')}</code>")
    
    # Add detection details if any
    if detections > 0:
        results = data.get("last_analysis_results", {})
        detection_details = [
            f"    - {engine}: <code>{html.escape(result['result'])}</code>"
            for engine, result in results.items()
            if result["category"] in ["malicious", "suspicious"]
        ]
        if detection_details:
            report_lines.append("\n<b>Detection Details:</b>")
            report_lines.append(f"<blockquote expandable>{'\n'.join(detection_details)}</blockquote>")

    # Add the correct link to the full report
    gui_path = f"{scan_type}/{resource}"
    if scan_type == "ip": gui_path = f"ip-address/{resource}"
    report_lines.append(f"\n<a href='https://www.virustotal.com/gui/{gui_path}'>View Full Report</a>")
    
    return "\n".join(report_lines)

@bot.add_cmd(cmd=["virustotal", "vt"])
async def virustotal_handler(bot: BOT, message: Message):
    if not VIRUSTOTAL_API_KEY or VIRUSTOTAL_API_KEY == "YOUR_KEY":
        return await message.edit(
            "<b>VirusTotal API Key not configured.</b>\n"
            "Please create <code>extra_config.env</code> in your modules folder and add your key.",
            del_in=ERROR_VISIBLE_DURATION
        )

    replied_msg = message.replied
    target_input = message.input
    
    if replied_msg and replied_msg.media:
        await scan_file(api_key, message)
    elif target_input:
        if is_url(target_input):
            await scan_url(api_key, message)
        elif is_ip(target_input):
            await scan_domain_or_ip(api_key, message, "ip")
        elif is_domain(target_input):
            await scan_domain_or_ip(api_key, message, "domain")
        else:
            await message.edit("Invalid input. Please provide a valid URL, domain, or IP.", del_in=ERROR_VISIBLE_DURATION)
    else:
        await message.edit("Reply to a file or provide a URL/domain/IP to scan.", del_in=ERROR_VISIBLE_DURATION)

async def scan_file(api_key: str, message: Message):
    progress = await message.reply("<code>Downloading file...</code>")
    original_path = ""
    temp_files = []
    try:
        original_path = await bot.download_media(message.replied, file_name=os.path.join(TEMP_DIR, ""))
        temp_files.append(original_path)
        
        await progress.edit("<code>Calculating hash...</code>")
        file_hash = await asyncio.to_thread(calculate_sha256, original_path)
        
        await progress.edit("<code>Querying VirusTotal...</code>")
        headers = {"x-apikey": api_key}
        url = f"{VT_API_URL}/files/{file_hash}"
        response = await asyncio.to_thread(requests.get, url, headers=headers)
        
        if response.status_code == 200:
            final_report = format_vt_report(response.json()["data"]["attributes"], "file", file_hash)
        elif response.status_code == 404:
            final_report = "<b>VirusTotal Scan Report:</b>\n<b>  - Status:</b> ⚪ Not found in database."
        else:
            final_report = f"<b>VirusTotal Scan Report:</b>\n<b>  - Error:</b> API responded with code {response.status_code}."
        
        await bot.send_message(message.chat.id, final_report, reply_to_message_id=message.replied.id, link_preview_options=LinkPreviewOptions(is_disabled=True))
        await progress.delete()
        await message.delete()
    except Exception as e:
        await progress.edit(f"<b>Error:</b> <code>{html.escape(str(e))}</code>", del_in=ERROR_VISIBLE_DURATION)
    finally:
        for f in temp_files:
            if f and os.path.exists(f): os.remove(f)

async def scan_url(api_key: str, message: Message):
    progress = await message.edit("<code>Querying VirusTotal for URL...</code>")
    target_url = message.input
    url_id = base64.urlsafe_b64encode(target_url.encode()).decode().strip("=")
    
    headers = {"x-apikey": api_key}
    url = f"{VT_API_URL}/urls/{url_id}"
    
    try:
        response = await asyncio.to_thread(requests.get, url, headers=headers)
        if response.status_code == 200:
            final_report = format_vt_report(response.json()["data"]["attributes"], "url", url_id)
        elif response.status_code == 404:
            final_report = "<b>VirusTotal Scan Report:</b>\n<b>  - Status:</b> ⚪ URL not found. Submitting for analysis..."
            # If not found, submit it for scanning
            post_url = f"{VT_API_URL}/urls"
            post_data = {"url": target_url}
            await asyncio.to_thread(requests.post, post_url, data=post_data, headers=headers)
            final_report += "\n<i>  Please check the full report in a minute.</i>"
        else:
            final_report = f"<b>VirusTotal Scan Report:</b>\n<b>  - Error:</b> API responded with code {response.status_code}."
        
        await progress.edit(final_report, link_preview_options=LinkPreviewOptions(is_disabled=True))
    except Exception as e:
        await progress.edit(f"<b>Error:</b> <code>{html.escape(str(e))}</code>", del_in=ERROR_VISIBLE_DURATION)

async def scan_domain_or_ip(api_key: str, message: Message, scan_type: str):
    progress = await message.edit(f"<code>Querying VirusTotal for {scan_type.capitalize()}...</code>")
    resource = message.input
    endpoint = "ip_addresses" if scan_type == "ip" else "domains"
    
    headers = {"x-apikey": api_key}
    url = f"{VT_API_URL}/{endpoint}/{resource}"
    
    try:
        response = await asyncio.to_thread(requests.get, url, headers=headers)
        if response.status_code == 200:
            final_report = format_vt_report(response.json()["data"]["attributes"], scan_type, resource)
        elif response.status_code == 404:
            final_report = f"<b>VirusTotal Scan Report:</b>\n<b>  - Status:</b> ⚪ {scan_type.capitalize()} not found in database."
        else:
            final_report = f"<b>VirusTotal Scan Report:</b>\n<b>  - Error:</b> API responded with code {response.status_code}."
            
        await progress.edit(final_report, link_preview_options=LinkPreviewOptions(is_disabled=True))
    except Exception as e:
        await progress.edit(f"<b>Error:</b> <code>{html.escape(str(e))}</code>", del_in=ERROR_VISIBLE_DURATION)
