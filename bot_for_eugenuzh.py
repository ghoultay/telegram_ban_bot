from telegram import Update, Bot
from telegram.ext import Application, ContextTypes, MessageHandler, filters
from telethon import TelegramClient
import asyncio
import configparser
from random import shuffle
import time
import ast


def read_config(filename='bot_config.txt', section='telegrambot'):
    # Create a parser
    parser = configparser.ConfigParser()
    # Read config file
    parser.read(filename, encoding='utf-8')

    # Get section, default to mysql
    data = {}
    if parser.has_section(section):
        items = parser.items(section)
        for item in items:
            data[item[0]] = item[1]
    else:
        raise Exception(f'{section} not found in the {filename} file')

    return data

data = read_config()

print(data)

TOKEN = data['token']
api_id = int(data['api_id'])
api_hash = data['api_hash']
group_id = int(data['group_id'])

members_usernames = []
members_ids = []
bot = TelegramClient('bot', api_id, api_hash).start(bot_token=TOKEN)
ban_bot = Bot(TOKEN)
phrases_ban = ast.literal_eval(data['phrases_ban'])
phrases_not_ban = ast.literal_eval(data['phrases_not_ban'])

async def get_users(client, group_id):
    global members_usernames
    global members_ids

    members_usernames = []
    members_ids = []
    async for user in client.iter_participants(group_id):
        if not user.deleted:
            if user.username != 'zeliboba_sumogusov_bot':
                members_usernames.append('@'+str(user.username))
                members_ids.append(user.id)
                print("id:", user.id, "username:", user.username)
    await asyncio.sleep(0)

with bot:
    asyncio.get_event_loop().run_until_complete(get_users(bot, group_id))


# Function to handle messages containing "@all"
async def respond_to_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message: str = update.message
    message_type: str = update.message.chat.type
    global members_usernames
    global members_ids

    # check for duplicates
    if len(set(members_ids)) != len(members_ids):
        members = list(set(zip(members_ids, members_usernames)))
        members_ids = [i[0] for i in members]
        members_usernames = [i[1] for i in members]

    print(message.text)

    if '@all' == str(message.text) and message_type == 'supergroup':
        tagged_members = ' '.join(members_usernames)
        response_message = f'{tagged_members}'
        await update.message.reply_text(response_message)
    elif '🔫' == str(message.text) and message_type == 'supergroup':
        shuffle(phrases_ban)
        shuffle(phrases_not_ban)
        if len(members_ids) > 1:

            temp_usernames = members_usernames.copy()
            temp_ids = members_ids.copy()
            temp = list(zip(temp_ids, temp_usernames))
            shuffle(temp)
            chat_id = temp[0][0]
            # chat_id = 6449100843
            inv_link = 'https://t.me/+BqJBabnFieE2Y2Ri'
            if temp[0][1] != '@ghoultay':
                members_usernames.remove(temp[0][1])
                members_ids.remove(temp[0][0])

                await ban_bot.ban_chat_member(group_id, temp[0][0], until_date=int(time.time() + 1))
                await ban_bot.unban_chat_member(group_id, temp[0][0])
                await ban_bot.send_message(chat_id=chat_id, text=phrases_ban[0])
                await ban_bot.send_message(chat_id=chat_id, text=inv_link)
                await ban_bot.send_message(chat_id=group_id, text=phrases_ban[0])
            else:
                members_usernames.remove(temp[1][1])
                members_ids.remove(temp[1][0])

                await ban_bot.ban_chat_member(group_id, temp[1][0], until_date=int(time.time() + 1))
                await ban_bot.unban_chat_member(group_id, temp[0][0])
                await ban_bot.send_message(chat_id=chat_id, text=phrases_ban[0])
                await ban_bot.send_message(chat_id=chat_id, text=inv_link)
                await ban_bot.send_message(chat_id=group_id, text=phrases_ban[0])
        else:
            await update.message.reply_text(phrases_not_ban[0])
    else:
        pass


async def new_member(update, context: ContextTypes.DEFAULT_TYPE):
    new_user = update.message.new_chat_members

    global members_usernames
    global members_ids

    for user in new_user:
        members_usernames.append('@'+str(user.username))
        members_ids.append(user.id)

    await asyncio.sleep(0)


# Main function to start the bot
def main() -> None:
    print('Starting bot...')
    app = Application.builder().token(TOKEN).build()
    # Handler for messages containing "@all"
    app.add_handler(MessageHandler(filters.TEXT, respond_to_all))

    # handler to process new member event
    app.add_handler(MessageHandler(filters.USER, new_member))

    # Start the bot
    print('Polling...')
    app.run_polling(poll_interval=1)


if __name__ == '__main__':
    main()
