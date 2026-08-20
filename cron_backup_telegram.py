#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import app

def main():
    print('[CRON TELEGRAM BACKUP] Inicializando verificação de backup...')
    app.init_db()
    cfg = app.get_config()

    ativo = cfg.get('telegram_backup_ativo', '0') == '1'
    bot_token = cfg.get('telegram_bot_token', '').strip()
    chat_id = cfg.get('telegram_chat_id', '').strip()

    if not ativo:
        print('[CRON TELEGRAM BACKUP] Backup via Telegram está desativado nas configurações. Encerrando.')
        sys.exit(0)

    if not bot_token or not chat_id:
        print('[CRON TELEGRAM BACKUP] ERRO: Token do Bot ou Chat ID não configurados. Encerrando.')
        sys.exit(1)

    print(f'[CRON TELEGRAM BACKUP] Enviando backup em Excel para o chat {chat_id}...')
    sucesso, msg = app._enviar_backup_telegram(bot_token, chat_id)

    if sucesso:
        print(f'[CRON TELEGRAM BACKUP] SUCESSO: {msg}')
        sys.exit(0)
    else:
        print(f'[CRON TELEGRAM BACKUP] ERRO: {msg}')
        sys.exit(1)

if __name__ == '__main__':
    main()
