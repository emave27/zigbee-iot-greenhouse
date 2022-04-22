from telegram.ext import Updater, CommandHandler
import requests

class PyTeleBot():
    def __init__(self):
        self.updater=Updater(token='your-bot-token', use_context=True)
        self.dispatcher=self.updater.dispatcher
        self.user_id=None
        self.message=None

    def start_ans(self, update, context):
        context.bot.send_message(chat_id=update.effective_chat.id, text='Hello and welcome to yet another Telegram bot test')
        self.user_id=update.effective_chat.id
    
    def start_polling_loop(self):
        print('Starting bot loop...')
        start_handler=CommandHandler('start', self.start_ans)
        self.dispatcher.add_handler(start_handler)
        self.updater.start_polling()

    def stop_polling_loop(self):
        print('Stopping bot loop...')
        self.updater.stop()
        quit()
    
    def send_message(self, text="Some text", send=True):
        token='your-bot-token'
        chat_id=self.user_id
        if send:
            link='https://api.telegram.org/bot'+token+'/sendMessage?chat_id='+str(chat_id)+'&text='+str(text)
            ans=requests.get(link)
            code=ans.status_code

            if code==200:
                print('Message sent!')
            else:
                print('Message not sent, check your Telegram client!')
        
        