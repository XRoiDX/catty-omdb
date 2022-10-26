from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup as markup, InlineKeyboardButton as button, Message as update, CallbackQuery as callback
from pyrogram.errors import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified
from Config import ADMINS
from LuciferMoringstar_Robot.Utils import save_file
import logging
import asyncio
import re
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
lock = asyncio.Lock()

Current = int(os.environ.get("SKIP", 2))
cancel = False

@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot: Client, update: callback):
    if update.data.startswith('index_cancel'):
        cancel = True
        await update.answer("Index Cancelling..")
        return

    if lock.locked():
        await update.answer("Wait Until Previous Process Complete", show_alert=True)
        return

    _, muhammedrk, chat, lst_msg_id, from_user = update.data.split("#")

    msg = update.message
    await update.answer("Processing...⏳", show_alert=True)

    pr0fess0r = [[ button('🚫 Stop Work 🚫', callback_data='close') ]]
    await update.message.edit(text="starting indexing..", reply_markup=markup(pr0fess0r))
    try:
        chat = int(chat)
    except:
        chat = chat
    await index_files_to_db(int(lst_msg_id), chat, msg, bot)


@Client.on_message(filters.private & filters.command("index") & filters.user(ADMINS))
async def send_for_index(bot: Client, update: update):

    last_msg = await bot.ask(text = "Forward me last message of a channel which I should save to my database.\n\nYou can forward posts from any public channel, but for private channels bot should be an admin in the channel.\n\nMake sure to forward with quotes (Not as a copy)", chat_id = update.from_user.id)

    if last_msg.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = last_msg.forward_from_message_id
        chat_id = last_msg.forward_from_chat.username or last_msg.forward_from_chat.id
    else:
        await update.reply("Process Cancelled")
        await last_msg.request.delete()
        return

    try:
        await bot.get_chat(chat_id)
    except ChannelInvalid:
        await update.reply('This may be a private channel / group. Make me an admin over there to index the files.')
        return
    except (UsernameInvalid, UsernameNotModified):
        await update.reply('Invalid Link specified.')
        return
    except Exception as e:
        logger.exception(e)
        await update.reply(f'Errors - {e}')
        return

    try:
        k = await bot.get_messages(chat_id, last_msg_id)
    except:
        await update.reply('Make Sure That Iam An Admin In The Channel, if channel is private')
        return

    if k.empty:
        await update.reply('This may be group and iam not a admin of the group.')
        return

    keyboard = [[
      button('✅️ Start Work ✅️', callback_data=f'index#accept#{chat_id}#{last_msg_id}#{update.from_user.id}')
      ],[
      button('🚫 Stop Work 🚫', callback_data='close')
      ]]
    await update.reply(
        f"Do you Want To Index This Channel/ Group ?\n\nChat ID/ Username: <code>{chat_id}</code>\nLast Message ID: <code>{last_msg_id}</code>",
        reply_markup=markup(keyboard))
    return

@Client.on_message(filters.command('setskip') & filters.user(ADMINS))
async def set_skip_number(bot: Client, update: update):
    if ' ' in update.text:
        _, skip = update.text.split(" ")
        try:
            skip = int(skip)
        except:
            return await update.reply("Skip number should be an integer.")
        await update.reply(f"Successfully set SKIP number as {skip}")
        Current = int(skip)
    else:
        await update.reply("Give me a skip number")

async def index_files_to_db(lst_msg_id, chat, msg, bot):
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0
    async with lock:
        try:
            current = Current
            cancel = False
            async for message in bot.iter_messages(chat, lst_msg_id, current):
                if cancel:
                    await msg.edit(f"Successfully Cancelled!!\n\nSaved <code>{total_files}</code> files to dataBase!\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\nErrors Occurred: <code>{errors}</code>")
                    break
                current += 1
                if current % 20 == 0:
                    can = [[ button('Cancel', callback_data='index_cancel') ]]
                    reply = markup(can)
                    await msg.edit_text(
                        text=f"Total messages fetched: <code>{current}</code>\nTotal messages saved: <code>{total_files}</code>\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\nErrors Occurred: <code>{errors}</code>",
                        reply_markup=reply)
                if message.empty:
                    deleted += 1
                    continue
                elif not message.media:
                    no_media += 1
                    continue
                elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.AUDIO, enums.MessageMediaType.DOCUMENT]:
                    unsupported += 1
                    continue
                media = getattr(message, message.media.value, None)
                if not media:
                    unsupported += 1
                    continue
                media.file_type = message.media.value
                media.caption = message.caption
                aynav, vnay = await save_file(media)
                if aynav:
                    total_files += 1
                elif vnay == 0:
                    duplicate += 1
                elif vnay == 2:
                    errors += 1
        except Exception as e:
            logger.exception(e)
            await msg.edit(f'Error: {e}')
        else:
            await msg.edit(f'Succesfully saved <code>{total_files}</code> to dataBase!\nDuplicate Files Skipped: <code>{duplicate}</code>\nDeleted Messages Skipped: <code>{deleted}</code>\nNon-Media messages skipped: <code>{no_media + unsupported}</code>(Unsupported Media - `{unsupported}` )\nErrors Occurred: <code>{errors}</code>')


RATING = ["5.1 | IMDB", "6.2 | IMDB", "7.3 | IMDB", "8.4 | IMDB", "9.5 | IMDB", ]
GENRES = ["fun, fact",
         "Thriller, Comedy",
         "Drama, Comedy",
         "Family, Drama",
         "Action, Adventure",
         "Film Noir",
         "Documentary"]
