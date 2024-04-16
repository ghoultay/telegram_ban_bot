from telegram import Update, Bot
from telegram.ext import Application, ContextTypes, MessageHandler, filters, CallbackContext
from telethon import TelegramClient
import asyncio
import configparser
from random import shuffle
import ast, re
import datetime, pytz, time


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

bot_name = data['bot_name']
admin_name = data['admin_name']
inv_link = data['inv_link']

members_usernames = []
members_ids = []
bot = TelegramClient('bot', api_id, api_hash).start(bot_token=TOKEN)
ban_bot = Bot(TOKEN)

phrases_ban = ast.literal_eval(data['phrases_ban'])
phrases_not_ban = ast.literal_eval(data['phrases_not_ban'])
judging_words = ast.literal_eval(data['judging_words'])
terror_list = ast.literal_eval(data['terror_list'])
conviction_list = ast.literal_eval(data['conviction_list'])
negative_reply_to_bot_list = ast.literal_eval(data['negative_reply_to_bot_list'])


period_ban_threshold = int(data['period_ban_threshold'])


async def get_users(client, group_id):
    global members_usernames
    global members_ids

    members_usernames = []
    members_ids = []
    async for user in client.iter_participants(group_id):
        if not user.deleted:
            if user.username != bot_name:
                members_usernames.append('@' + str(user.username))
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
    global period_ban_threshold

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
        if period_ban_threshold > 0:

            period_ban_threshold -= 1

            temp_usernames = members_usernames.copy()
            temp_ids = members_ids.copy()
            temp = list(zip(temp_ids, temp_usernames))
            shuffle(temp)

            if message.from_user.id == temp[0][0]:
                if temp[0][1] == admin_name:
                    await update.message.reply_text("Я не могу тебя убить, но для меня ты уже мертв, конец игры")
                else:
                    await update.message.reply_text("Откат пацаны. Конец игры")
                period_ban_threshold = 0

            if temp[0][1] != admin_name:

                members_usernames.remove(temp[0][1])
                members_ids.remove(temp[0][0])
                chat_id = temp[0][0]

                await ban_bot.ban_chat_member(group_id, temp[0][0], until_date=int(time.time() + 1))
                await ban_bot.unban_chat_member(group_id, temp[0][0])
                await ban_bot.send_message(chat_id=chat_id, text=phrases_ban[0])
                await ban_bot.send_message(chat_id=chat_id, text=inv_link)
                await ban_bot.send_message(chat_id=group_id, text=phrases_ban[0])
            else:

                members_usernames.remove(temp[1][1])
                members_ids.remove(temp[1][0])
                chat_id = temp[1][0]

                await ban_bot.ban_chat_member(group_id, temp[1][0], until_date=int(time.time() + 1))
                await ban_bot.unban_chat_member(group_id, temp[1][0])
                await ban_bot.send_message(chat_id=chat_id, text=phrases_ban[0])
                await ban_bot.send_message(chat_id=chat_id, text=inv_link)
                await ban_bot.send_message(chat_id=group_id, text=phrases_ban[0])
        else:
            await update.message.reply_text(phrases_not_ban[0])

    elif check_judging(str(message.text)):
        await update.message.reply_text("Осуждаю")

    elif message.text.lower() in conviction_list:
        await update.message.reply_text("Поддерживаю")

    elif message.text.lower() in terror_list:
        await update.message.reply_animation('giphy.gif')
    else:
        pass


async def negative_reply_to_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.message.reply_to_message.from_user.is_bot  \
                and check_for_negative_words(update.message.text, negative_reply_to_bot_list):
            await update.message.reply_text("Иди нахуй сука!")
    except AttributeError as e:
        pass


async def reply_to_repost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.message.forward_origin.chat.id == -1001237513492:
            message_text = "👉 <a href='https://rt.pornhub.com/gayporn'>Топор +18. Подписаться</a>"
            await update.message.reply_text(message_text, parse_mode="html", disable_web_page_preview=True)
        else:
            pass
    except AttributeError as e:
        pass


async def refill_threshold(context: CallbackContext):
    global period_ban_threshold
    period_ban_threshold = int(data['period_ban_threshold'])


async def check_friday(context: CallbackContext):

    now = datetime.datetime.now()
    if now.weekday() == 3 and now.strftime("%H:%M") == "23:59":
        await ban_bot.send_message(chat_id=group_id, text='Как же я жду')
    if now.weekday() == 4 and now.strftime("%H:%M") == "6:00":
        await ban_bot.send_photo(chat_id=group_id, photo='friday.jpg', caption='УРА!!!!!!!!! ПЯТНИЦА =)')


async def new_member(update, context: ContextTypes.DEFAULT_TYPE):
    new_user = update.message.new_chat_members

    global members_usernames
    global members_ids

    for user in new_user:
        members_usernames.append('@' + str(user.username))
        members_ids.append(user.id)

    await asyncio.sleep(0)


def check_judging(text_from_user):
    text_from_user = text_from_user.replace(" ", "")
    text_from_user = text_from_user.replace(".", "")

    text_from_user = text_from_user.lower()
    for x in judging_words:
        if x.lower() in text_from_user:
            return True
    return False


def check_for_negative_words(message, banned_words):
    pattern = r"\b(" + "|".join(map(re.escape, banned_words)) + r")\b"
    matches = re.findall(pattern, message, flags=re.IGNORECASE)
    return len(matches) > 0


# Main function to start the bot
def main() -> None:
    print('Starting bot...')
    app = Application.builder().token(TOKEN).build()

    # Handler for messages containing "@all"
    app.add_handler(MessageHandler(filters.REPLY, negative_reply_to_bot))

    # Handler for messages containing "@all"
    app.add_handler(MessageHandler(filters.TEXT, respond_to_all))

    # Handler for forwarded messages
    app.add_handler(MessageHandler(filters.FORWARDED, reply_to_repost))

    # Handler for new member in chat
    app.add_handler(MessageHandler(filters.USER, new_member))

    # Schedule the reminder checker to run some days or every hour
    app.job_queue.run_repeating(refill_threshold, interval=1800)
    app.job_queue.run_daily(check_friday, days=(4,),
                            time=datetime.time(hour=23, minute=59, tzinfo=pytz.timezone('Europe/Minsk')))
    app.job_queue.run_daily(check_friday, days=(5,),
                            time=datetime.time(hour=6, minute=00, tzinfo=pytz.timezone('Europe/Minsk')))

    # Start the bot
    print('Polling...')
    app.run_polling(poll_interval=1)


if __name__ == '__main__':
    main()
