import re
import requests
from io import BytesIO
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import os

BOT_TOKEN = os.environ.get('
          8458041575:AAGYjPxiWO4K0lUOIZaXr1C2OyXDuwPCbAU
        ')

def extract_drive_links(text):
    return re.findall(r'https?://drive\.google\.com/[^\s]+', text)

def extract_file_id(link):
    match = re.search(r'/d/([a-zA0-9_-]+)', link)
    if not match:
        match = re.search(r'id=([a-zA0-9_-]+)', link)
    return match.group(1) if match else None

def get_confirmed_download_response(file_id):
    session = requests.Session()
    base_url = "https://drive.google.com/uc?export=download"
    response = session.get(base_url, params={'id': file_id}, stream=True)

    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            response = session.get(base_url, params={'id': file_id, 'confirm': value}, stream=True)
            break

    return response

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    drive_links = extract_drive_links(message_text)

    if not drive_links:
        await update.message.reply_text("❌ No valid Google Drive links found.")
        return

    for link in drive_links:
        file_id = extract_file_id(link)
        if not file_id:
            await update.message.reply_text(f"❌ Invalid link format:\n{link}")
            continue

        status_msg = await update.message.reply_text(f"🔗 Processing:\n{link}\n📥 Downloading...")

        try:
            response = get_confirmed_download_response(file_id)
            response.raise_for_status()

            content_disposition = response.headers.get('content-disposition', '')
            filename_match = re.search(r'filename="(.+)"', content_disposition)
            filename = filename_match.group(1) if filename_match else 'drive_file'

            file_stream = BytesIO(response.content)
            file_stream.name = filename

            await status_msg.edit_text(f"📤 Uploading to Telegram: `{filename}`", parse_mode="Markdown")
            await context.bot.send_document(chat_id=update.effective_chat.id, document=file_stream)
            await status_msg.edit_text(f"✅ Done: `{filename}`", parse_mode="Markdown")

        except Exception as e:
            await status_msg.edit_text(f"❌ Failed for:\n{link}\nError: `{str(e)}`", parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()