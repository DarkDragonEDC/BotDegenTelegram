import logging
import os
import datetime # Importa o módulo datetime inteiro para evitar conflitos de nome
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- 1. CONFIGURAÇÕES BÁSICAS ---

# ATENÇÃO: Substitua pelo seu Token do BotFather
TOKEN = "8307699328:AAGKETYLWJI5-0hPbEEN0V-_K5NxyTNYHco" 
ARQUIVO_SUBSCRIBERS = "subscribers.txt"

# Define o fuso horário de Brasília/São Paulo (UTC-3)
# Usando timedelta é a forma mais segura para um offset fixo
FUSO_HORARIO = datetime.timezone(datetime.timedelta(hours=-3)) 

# Configuração de Log
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


# --- 2. FUNÇÕES DE BANCO DE DADOS (ARQUIVO SIMPLES) ---

def load_subscribers():
    """Carrega os IDs de usuário que ativaram a notificação."""
    if not os.path.exists(ARQUIVO_SUBSCRIBERS):
        return set()
    try:
        with open(ARQUIVO_SUBSCRIBERS, 'r') as f:
            # Converte a linha lida (que é string) para inteiro (user_id)
            return set(int(line.strip()) for line in f if line.strip().isdigit())
    except Exception as e:
        logging.error(f"Erro ao carregar subscribers: {e}")
        return set()


def save_subscribers(subscribers):
    """Salva a lista atual de IDs no arquivo."""
    try:
        with open(ARQUIVO_SUBSCRIBERS, 'w') as f:
            for user_id in subscribers:
                f.write(f"{user_id}\n")
    except Exception as e:
        logging.error(f"Erro ao salvar subscribers: {e}")


# --- 3. FUNÇÕES DO AGENDADOR (JOB) ---

async def send_daily_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia a mensagem 'Recompensa Diária disponível' para todos os inscritos."""
    subscribers = load_subscribers()
    
    for user_id in subscribers:
        try:
            # Envia a mensagem no chat privado do usuário (chat_id = user_id)
            await context.bot.send_message(
                chat_id=user_id, 
                text="🔔 **Recompensa Diária disponível!**\nLembre-se de resgatá-la.",
                parse_mode='Markdown'
            )
            logging.info(f"Notificação enviada para o usuário ID: {user_id}")
        except Exception as e:
            # Se o bot foi bloqueado, o envio falha. Removemos o ID.
            logging.warning(f"Erro ao enviar para o ID {user_id} (Removendo da lista): {e}")
            subscribers.discard(user_id) # Remove o ID inválido
    
    # Salva a lista atualizada após remover IDs inválidos (opcional, mas recomendado)
    save_subscribers(subscribers)


# --- 4. HANDLERS DE COMANDO ---

async def ativar_recompensa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adiciona o usuário à lista de notificação."""
    
    # Pegamos o ID do usuário que enviou a mensagem, seja no grupo ou no privado
    user_id = update.effective_user.id
    subscribers = load_subscribers()
    
    if user_id not in subscribers:
        subscribers.add(user_id)
        save_subscribers(subscribers)
        
        await update.message.reply_text(
            "✅ **Notificação Diária ativada!**\nVocê receberá a mensagem no privado todos os dias às 21:00 (Horário de Brasília).",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("Você já ativou a notificação.")

async def desativar_recompensa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove o usuário da lista de notificação."""
    
    user_id = update.effective_user.id
    subscribers = load_subscribers()
    
    if user_id in subscribers:
        subscribers.discard(user_id)
        save_subscribers(subscribers)
        
        await update.message.reply_text(
            "❌ **Notificação Diária desativada!**\nVocê não receberá mais o lembrete diário.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("Você não tem a notificação diária ativada.")


# --- 5. FUNÇÃO PRINCIPAL ---

def main() -> None:
    """Inicia o Bot e o Agendador."""
    
    application = Application.builder().token(TOKEN).build()
    
    # Adiciona os Handlers
    application.add_handler(CommandHandler("ativar_recompensa", ativar_recompensa))
    application.add_handler(CommandHandler("desativar_recompensa", desativar_recompensa))
    
    # Configura o Agendador (JobQueue)
    job_queue = application.job_queue
    
    # Agendar a função send_daily_message para rodar diariamente às 21:00 (9 PM)
    job_queue.run_daily(
        send_daily_message, 
        # CORRIGIDO: Usando datetime.time (classe) para o parâmetro time=
        time=datetime.time(hour=21, minute=0, second=0, tzinfo=FUSO_HORARIO),
        days=(0, 1, 2, 3, 4, 5, 6), # Todos os dias
        name='daily_reward_notification'
    )
    
    # Inicia o Bot
    logging.info("Bot iniciado e Agendador configurado para 21:00 (UTC-3).")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()