
import os
import math
from datetime import datetime
from telegram import Message, ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, PicklePersistence, ConversationHandler, ContextTypes, MessageHandler, filters

secret_file_code = '0000'
escape_code = '0000'

starting_points = 100
hint_penalty = 5
wrong_secret_file_code_penalty = 5
wrong_escape_code_penalty = 10
penalty_per_min = 2
average_time = 90
nomi_squadre = ['A', 'B', 'C', 'D']

secret_file = open('secretfile.zip', 'rb')

CHOOSING_TEAM, ENTERING, PLAYING, SECRET_FILE, ASKING_HINT, ESCAPING, ESCAPED, SUPERVISING = range(8)

TOKEN = None
with open('token.txt') as file:
    TOKEN = file.readline()
    file.close()

os.remove('persistence.pkl')
persistence = PicklePersistence('persistence.pkl')
application = Application.builder().token(TOKEN).persistence(persistence).build()


class Group:
    def __init__(self, id):
        self.group_id = id
        self.points = starting_points
        self.hints_used = 0
        self.secret_file_wrong_attempts = 0
        self.escape_wrong_attempts = 0
        self.supervisor_chat_id = None

    def set_player(self, player):
        self.player: Player = player

    async def start(self):
        self.start_time = datetime.now()
        await self.log('Entrata nella stanza')

    async def send_to_group(self, text: str):
        await application.bot.send_message(self.player.chat_id, text)

    async def send_to_supervisor(self, text: str):
        if self.supervisor_chat_id:
            await application.bot.send_message(self.supervisor_chat_id, text)

    async def ask_for_hint(self):
        self.hints_used += 1
        self.points -= hint_penalty
        await self.log('Richiesto indizio')
        return PLAYING


    async def forward_hint_request(self, message: Message):
        if len(message.photo) > 0:
            await application.bot.send_photo(self.supervisor_chat_id, message.photo[0])
        elif message.voice:
            await application.bot.send_voice(self.supervisor_chat_id, message.voice)
        else:
            await application.bot.send_message(self.supervisor_chat_id, message.text)
        return PLAYING


    def set_supervisor(self, supervisor, chat_id):
        self.supervisor = supervisor
        self.supervisor_chat_id = chat_id

    async def log(self, line: str):
        string = f'{datetime.now().strftime("%H:%M:%S")} - {self.group_id}: {line}'
        print(string)
        await self.send_to_supervisor(string)

    async def wrong_secret_file_code(self):
        self.secret_file_wrong_attempts += 1
        self.points -= wrong_secret_file_code_penalty
        await self.log('Codice file segreto errato')

    async def secret_file_unlocked(self):
        await self.log('File segreto sbloccato')

    async def wrong_escape_code(self):
        self.escape_wrong_attempts += 1
        self.points -= wrong_escape_code_penalty
        await self.log('Codice di uscita errato')

    async def escape_success(self):
        self.end_time = datetime.now()
        self.tot_time = (self.end_time - self.start_time).total_seconds() / 60
        diff_time = self.tot_time - average_time
        if diff_time < 0:
            diff_time = 0
        time_penalty = diff_time * penalty_per_min
        self.points -= time_penalty
        await self.log(f"""
Uscita effettuata
Tempo impiegato: {math.floor(self.tot_time)} min {math.floor((self.tot_time - math.floor(self.tot_time)) * 60)} sec
Punteggio: {self.points}
Indizi richiesti: {self.hints_used}
Codici file segreto sbagliati: {self.secret_file_wrong_attempts}
Codici di uscita sbagliati: {self.escape_wrong_attempts}
        """)



groups = {}
for group_id in nomi_squadre:
    groups[group_id] = Group(group_id)


class Player:
    def __init__(self, id, name, chat_id):
        self.id = id
        self.name = name
        self.chat_id = chat_id

    def set_group_id(self, group_id: str):
        self.group_id = group_id

    
players = {}


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('''
Lista comandi:
/hint - Chiedi un indizio
/secretfile - Inserimento codice per il file segreto
/escape - Inserimento codice per uscire
    ''')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    id = update.message.from_user.id
    if id not in players:
        await update.message.reply_text(
            f'''
Ciao ragazzi! Benvenuti all'Escape Room di Caramanico 2022!
Come già sapete, userete questo bot Telegram per uscire dalla stanza, e per recuperare un file segreto che vi aiuterà nel farlo.
Partirete con {starting_points} punti, e a seconda del tempo che impiegate, di quanti indizi chiedete e di quanti codici sbagliate il punteggio scenderà.
Alla fine vince la squadra che è uscita con più punti!
Digita il comando /login per inizializzare tutti i dati di gioco!
        '''
        )
    else:
        await update.message.reply_text('Il tempo è già partito! Spremetevi le meningi e cercate di uscire!')


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    id = update.message.from_user.id
    if id not in players:
        name = update.message.from_user.name
        chat_id = update.message.chat_id
        player = Player(id, name, chat_id)
        players[id] = player
        context.user_data['player_id'] = id
        await update.message.reply_text('Quale squadra siete?',
            reply_markup=ReplyKeyboardMarkup([[
                nomi_squadre[0],
                nomi_squadre[1]
            ], [
                nomi_squadre[2],
                nomi_squadre[3]
            ]], one_time_keyboard=True))
        return CHOOSING_TEAM
    else:
        await update.message.reply_text('Il tempo è già partito! Spremetevi le meningi e cercate di uscire!')
        return PLAYING


async def team_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    group_id = update.message.text
    player = players[context.user_data['player_id']]
    player.set_group_id(group_id)
    groups[group_id].set_player(player)
    context.user_data['group_id'] = group_id
    await update.message.reply_text(f'Bene! Ora siete pronti per entrare nella stanza. Digitate il comando /enter per iniziare l\'avventura!')
    return ENTERING


async def enter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    group = groups[context.user_data['group_id']]
    await group.start()
    await update.message.reply_text('Per visualizzare la lista dei comandi digitare il comando /help. Il tempo è partito! Buona fortuna! 😜')
    return PLAYING


async def hint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    group = groups[context.user_data['group_id']]
    await group.ask_for_hint()
    update.message.reply_text('Ora puoi chiedere l\'indizio, scrivi un messaggio, manda un audio o una foto')
    return PLAYING


async def ask_hint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    group = groups[context.user_data['group_id']]
    await group.forward_hint_request(update.message)
    return PLAYING


async def secret_file_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Inserisci il codice per sbloccare il file segreto')
    return SECRET_FILE


async def unlock_secret_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    code = update.message.text
    group = groups[context.user_data['group_id']]
    if code == secret_file_code:
        await group.secret_file_unlocked()
        await update.message.reply_document(secret_file)
    else:
        await group.wrong_secret_file_code()
        await update.message.reply_text('Codice inserito errato')
    return PLAYING


async def escape(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Inserisci il codice per uscire')
    return ESCAPING


async def try_escaping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    code = update.message.text
    group = groups[context.user_data['group_id']]
    if code == escape_code:
        await group.escape_success()
        await update.message.reply_text('Congratulazioni! Il codice inserito è corretto! Fra qualche secondo si aprirà la porta!')
        return ESCAPED
    else:
        await group.wrong_escape_code()
        await update.message.reply_text('Codice inserito errato')
        return PLAYING


async def supervisor_team_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    group_id = update.message.text
    group = groups[group_id]
    group.set_supervisor(
        context.user_data['supervisor'], context.user_data['chat_id'])
    context.user_data['group'] = group
    context.user_data['group_id'] = group_id
    await update.message.reply_text(f'Bene! Ora ti arriveranno tutti gli aggiornamenti della squadra {group_id}')
    return SUPERVISING


async def supervise(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    supervisor = update.message.from_user
    chat_id = update.message.chat_id
    context.user_data['supervisor'] = supervisor
    context.user_data['chat_id'] = chat_id
    await update.message.reply_text('Quale squadra supervisioni?',
                                    reply_markup=ReplyKeyboardMarkup([[
                                        nomi_squadre[0],
                                        nomi_squadre[1]
                                    ], [
                                        nomi_squadre[2],
                                        nomi_squadre[3]
                                    ]], one_time_keyboard=True))
    return CHOOSING_TEAM


async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    group = groups[context.user_data['group_id']]
    await group.send_to_group(update.message.text)
    return SUPERVISING


def main() -> None:
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help))

    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('login', login)],
        states={
            CHOOSING_TEAM: [MessageHandler(filters.Regex(f'^({"|".join(nomi_squadre)})$'), team_chosen)],
            ENTERING: [CommandHandler('enter', enter)],
            PLAYING: [CommandHandler('hint', hint), CommandHandler('secretfile', secret_file_callback), CommandHandler('escape', escape), MessageHandler(filters.TEXT | filters.VOICE | filters.PHOTO, ask_hint)],
            SECRET_FILE: [MessageHandler(filters.TEXT, unlock_secret_file)],
            ESCAPING: [MessageHandler(filters.TEXT, try_escaping)]
        },
        fallbacks=[MessageHandler],
        name='main_conversation',
        persistent=True,
    ))

    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('supervise', supervise)],
        states={
            CHOOSING_TEAM: [MessageHandler(filters.Regex(f'^({"|".join(nomi_squadre)})$'), supervisor_team_chosen)],
            SUPERVISING: [MessageHandler(filters.TEXT, forward_message)]
        },
        fallbacks=[MessageHandler],
        name='supervisor_conversation',
        persistent=True,
    ))

    application.run_polling()


if __name__ == '__main__':
    main()
