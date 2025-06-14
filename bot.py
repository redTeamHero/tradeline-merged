import re
import io
import qrcode
import logging
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
from scrape import scrape_and_group_tradelines

TELEGRAM_TOKEN = 'your-telegram-bot-token'
user_states = {}
user_tradelines = {}

def start(update: Update, context: CallbackContext):
    buckets = scrape_and_group_tradelines()
    keyboard = [
        [InlineKeyboardButton(f"💳 Limit: $0 - $2.5K ({len(buckets['0-2500'])})", callback_data='cat_0-2500')],
        [InlineKeyboardButton(f"💳 Limit: $2.5K - $5K ({len(buckets['2501-5000'])})", callback_data='cat_2501-5000')],
        [InlineKeyboardButton(f"💳 Limit: $5K - $10K ({len(buckets['5001-10000'])})", callback_data='cat_5001-10000')],
        [InlineKeyboardButton(f"💳 Limit: $10K+ ({len(buckets['10001+'])})", callback_data='cat_10001+')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Select a credit limit range:", reply_markup=reply_markup)

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("cat_"):
        category = data.replace("cat_", "")
        buckets = scrape_and_group_tradelines()
        user_states[user_id] = {'category': category, 'page': 0}
        user_tradelines[user_id] = buckets.get(category, [])

        banks = sorted(set(item['bank'] for item in user_tradelines[user_id]))
        bank_buttons = [[InlineKeyboardButton(bank, callback_data=f"bank_{bank}")] for bank in banks]
        bank_buttons.append([InlineKeyboardButton("⬅️ Back", callback_data='back_start')])
        reply_markup = InlineKeyboardMarkup(bank_buttons)
        query.edit_message_text("Choose a bank:", reply_markup=reply_markup)

    elif data.startswith("bank_"):
        selected_bank = data.replace("bank_", "")
        state = user_states.get(user_id, {})
        state['bank'] = selected_bank
        state['page'] = 0
        user_states[user_id] = state
        user_tradelines[user_id] = [item for item in user_tradelines[user_id] if item['bank'] == selected_bank]
        display_tradelines(query, user_id)

    elif data.startswith("nav_"):
        direction = data.replace("nav_", "")
        state = user_states.get(user_id)
        if not state:
            return
        state['page'] += 1 if direction == 'next' else -1
        state['page'] = max(0, state['page'])
        user_states[user_id] = state
        display_tradelines(query, user_id)

    elif data.startswith("preview_"):
        idx = int(data.replace("preview_", ""))
        tradeline = user_tradelines[user_id][idx]
        user_states[user_id]['selected_index'] = idx
        preview_text = tradeline['text']
        buttons = [
            [InlineKeyboardButton("✅ Buy Now", callback_data=f"buy_{idx}")],
            [InlineKeyboardButton("⬅️ Back to List", callback_data='back_to_list')]
        ]
        query.edit_message_text(text=preview_text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == 'back_to_list':
        display_tradelines(query, user_id)

    elif data.startswith("buy_"):
        idx = int(data.replace("buy_", ""))
        tradeline = user_tradelines[user_id][idx]
        qr_data = f"Buy Tradeline: {tradeline['bank']} - ${tradeline['price']:,.2f}"
        img = qrcode.make(qr_data)
        bio = io.BytesIO()
        bio.name = 'qr.png'
        img.save(bio, 'PNG')
        bio.seek(0)
        context.bot.send_photo(chat_id=query.message.chat_id, photo=bio, caption=f"Scan this QR to buy:

{tradeline['text']}")

def display_tradelines(query, user_id):
    state = user_states[user_id]
    tradelines = user_tradelines[user_id]
    per_page = 5
    start = state['page'] * per_page
    end = start + per_page
    page_items = tradelines[start:end]
    buttons = []
    for idx, item in enumerate(page_items):
        label = f"{item['bank']} | Limit: ${item['limit']:,} | ${item['price']:,.2f}"
        callback = f"preview_{start + idx}"
        buttons.append([InlineKeyboardButton(label, callback_data=callback)])
    nav_buttons = []
    if start > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Back", callback_data='nav_prev'))
    if end < len(tradelines):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data='nav_next'))
    if nav_buttons:
        buttons.append(nav_buttons)
    buttons.append([InlineKeyboardButton("⬅️ Bank Select", callback_data='back_start')])
    reply_markup = InlineKeyboardMarkup(buttons)
    query.edit_message_text(text="Select a tradeline to preview:", reply_markup=reply_markup)

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
