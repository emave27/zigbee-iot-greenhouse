from telegram.ext import Updater, CommandHandler
import requests
from functions import get_chatid

class PyTeleBot():
    def __init__(self):
        self.updater=Updater(token='your-bot-token', use_context=True)
        self.dispatcher=self.updater.dispatcher

    def start_ans(self, update, context):
        #check on start if user chat id is already saved in table
        usr_id=get_chatid(None)
        if usr_id:
            #if the chat id matches with the effective chat id (user recognized), welcome the user
            if usr_id==int(update.effective_chat.id):
                context.bot.send_message(chat_id=usr_id, text='Welcome again!')
            else:
            #else, the user is not recognized
                context.bot.send_message(chat_id=update.effective_chat.id, text='Welcome, who are you?')
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text='No chat id saved!')
    
    def start_polling_loop(self):
        print('Starting bot loop...')
        start_handler=CommandHandler('start', self.start_ans)
        self.dispatcher.add_handler(start_handler)
        self.updater.start_polling()

    def stop_polling_loop(self):
        print('Stopping bot loop...')
        self.updater.stop()
        print('Done!')
        quit()
    
    def send_message(self, text="Some text", send=True):
        token='your-bot-token'
        chat_id=get_chatid(None)
        if chat_id:
            if send:
                link='https://api.telegram.org/bot'+token+'/sendMessage?chat_id='+str(chat_id)+'&text='+str(text)
                ans=requests.get(link)
                code=ans.status_code

                if code==200:
                    print('Message sent!')
                else:
                    print('Message not sent, check your Telegram client!')
        else:
            print('Message not sent, check your chat id settings!')
        
