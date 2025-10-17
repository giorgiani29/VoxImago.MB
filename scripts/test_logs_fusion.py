#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script rápido para testar logs de fusão de metadados
Executa uma sincronização forçada do Drive para gerar logs
"""

import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from workers import DriveSyncWorker
import sys
import os
sys.path.append('src')


def test_fusion_logs():
    print("🚀 TESTE RÁPIDO: LOGS DE FUSÃO DE METADADOS")
    print("=" * 60)

    token_file = 'config/token.json'
    if not os.path.exists(token_file):
        print("❌ Arquivo token.json não encontrado. Execute autenticação primeiro.")
        return

    try:
        with open(token_file, 'r') as f:
            creds_data = json.load(f)
        creds = Credentials.from_authorized_user_info(creds_data)
    except Exception as e:
        print(f"❌ Erro ao carregar credenciais: {e}")
        return

    try:
        service = build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ Erro ao criar service Drive: {e}")
        return

    print("✅ Service Drive criado com sucesso")

    db_name = 'data/test_file_index.db'
    force_sync = True
    selected_folders = None

    worker = DriveSyncWorker(service, db_name, force_sync, selected_folders)

    print("🔄 Iniciando sincronização forçada para testar logs...")
    print("📝 Verifique app.log para ver os logs de fusão/conflitos")
    print("⚠️  Pressione Ctrl+C para interromper se demorar muito")

    try:
        from PyQt6.QtWidgets import QApplication
        import signal

        app = QApplication(sys.argv)

        def on_finished():
            print("✅ Sincronização concluída")
            app.quit()

        def on_failed(error):
            print(f"❌ Sincronização falhou: {error}")
            app.quit()

        worker.sync_finished.connect(on_finished)
        worker.sync_failed.connect(on_failed)

        worker.run()

        app.exec()

    except KeyboardInterrupt:
        print("\n⏹️  Teste interrompido pelo usuário")
        worker.terminate()
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")

    print("\n📋 Verifique os logs em app.log para:")
    print("   - Falhas de fusão (quando não há matches)")
    print("   - Conflitos de metadados (múltiplos matches ou descrições diferentes)")
    print("   - Erros durante atualização")


if __name__ == "__main__":
    test_fusion_logs()
