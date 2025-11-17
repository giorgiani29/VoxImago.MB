"""
Módulo processing

Este módulo trata do processamento de arquivos e dados relacionados ao Google Drive
no VoxImago.MB. Inclui funções para análise, transformação, preparação e manipulação
de arquivos durante operações de sincronização, upload, download e fusão.
"""

import logging
from .drive_sync import DriveSync
from .drive_dialog import DriveFolderDialog
from PyQt6.QtCore import QThread, QTimer
from PyQt6.QtWidgets import QProgressDialog, QMessageBox


def start_drive_folder_processing(parent, service, indexer, force_dialog=False):
    from src.utils.utils import load_settings

    if force_dialog:
        folder_dialog = DriveFolderDialog(service, parent)
        if folder_dialog.exec() != folder_dialog.DialogCode.Accepted:
            return  # Usuário cancelou
        folder_dialog.save_settings()
        selected_folders = folder_dialog.get_selected_folders()
        if not selected_folders:
            QMessageBox.warning(
                parent, "Aviso", "Nenhuma pasta do Drive selecionada.")
            return
    else:
        settings = load_settings()
        selected_folders = settings.get('drive_folders', [])

        if not selected_folders:
            folder_dialog = DriveFolderDialog(service, parent)
            if folder_dialog.exec() != folder_dialog.DialogCode.Accepted:
                return
            folder_dialog.save_settings()
            selected_folders = folder_dialog.get_selected_folders()
            if not selected_folders:
                QMessageBox.warning(
                    parent, "Aviso", "Nenhuma pasta do Drive selecionada.")
                return
        else:
            folder_names = []
            for folder_id in selected_folders:
                if folder_id.startswith('0') and len(folder_id) > 10:
                    folder_names.append("Shared Drive (Banco de Imagens)")
                elif folder_id == 'root':
                    folder_names.append("Meu Drive")
                else:
                    folder_names.append(f"Pasta: {folder_id[:15]}...")

            print(f"📁 Usando configurações salvas: {', '.join(folder_names)}")
            logging.info(f"📁 Usando configurações salvas: {selected_folders}")
    thread = QThread()
    worker = DriveSync(service, db_name=indexer.db_name,
                       selected_folders=selected_folders)
    worker.moveToThread(thread)
    progress = QProgressDialog(
        "Sincronizando arquivos...", "Cancelar", 0, 100, parent)
    progress.setWindowModality(parent.windowModality())
    progress.setAutoClose(True)
    progress.setAutoReset(True)
    progress.setFixedSize(400, 150)
    progress.setStyleSheet("""
        QProgressBar { min-height: 25px; border: 1px solid #ccc; border-radius: 5px; text-align: center; }
        QProgressBar::chunk { background-color: #4CAF50; border-radius: 5px; }
    """)

    total_files_to_sync = [0]

    def on_total_found(total):
        total_files_to_sync[0] = total
        print(f"DEBUG Drive: Total de arquivos a sincronizar: {total:,}")

    def update_progress(value, msg):
        progress.setValue(value)
        progress.setLabelText(msg)
        if value >= 100:
            progress.setValue(100)
            progress.setLabelText("Sincronização concluída.")

    def update_status(msg):
        progress.setLabelText(msg)
        print(f"DEBUG Status: {msg}")

    cleanup_executed = [False]

    def cleanup_thread():
        if cleanup_executed[0]:
            print("🔄 Cleanup já executado, ignorando...")
            return

        cleanup_executed[0] = True
        print("🧹 Iniciando cleanup robusto do thread...")

        try:
            if 'worker' in locals() and worker:
                print("⏹️ Parando worker...")
                worker.terminate()
                worker.is_running = False

            if 'progress' in locals() and progress:
                try:
                    progress.close()
                    print("✅ Progress dialog fechado")
                except:
                    pass

            if 'thread' in locals() and thread and thread.isRunning():
                print("⏳ Aguardando thread finalizar...")
                thread.quit()

                if not thread.wait(3000):
                    print("⚠️ Thread não finalizou em 3s, tentando terminar...")
                    thread.terminate()

                    if not thread.wait(2000):
                        print("🚨 Thread não respondeu ao terminate")
                    else:
                        print("✅ Thread terminada após terminate")
                else:
                    print("✅ Thread finalizada normalmente")

            if 'worker' in locals() and worker:
                try:
                    worker.deleteLater()
                    print("✅ Worker removido")
                except:
                    pass

            if 'thread' in locals() and thread:
                try:
                    thread.deleteLater()
                    print("✅ Thread removida")
                except:
                    pass

            print("✅ Cleanup completo concluído")
        except Exception as e:
            print(f"❌ Erro no cleanup: {e}")
            try:
                if 'progress' in locals() and progress:
                    progress.close()
            except Exception:
                pass

    def on_sync_finished():
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"✅ [{timestamp}] Sincronização Drive FINALIZADA com sucesso!")

        try:
            if hasattr(parent, 'on_drive_sync_finished'):
                parent.on_drive_sync_finished()
        except Exception as e:
            print(f"⚠️ Erro ao notificar UI sobre término: {e}")

        cleanup_thread()

    def on_sync_failed(error):
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"❌ [{timestamp}] Sincronização FALHOU: {error}")

        try:
            if hasattr(parent, 'on_drive_sync_failed'):
                parent.on_drive_sync_failed(str(error))
        except Exception as e:
            print(f"⚠️ Erro ao notificar UI sobre falha: {e}")

        cleanup_thread()

    def on_canceled():
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"🛑 [{timestamp}] Cancelamento SOLICITADO pelo usuário")

        try:
            if hasattr(parent, 'drive_sync_running'):
                parent.drive_sync_running = False
                print("✅ Flag drive_sync_running liberada após cancelamento")
        except Exception as e:
            print(f"⚠️ Erro ao liberar flag após cancelamento: {e}")

        cleanup_thread()

    def emergency_cleanup():
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"🚨 [{timestamp}] EMERGENCY CLEANUP - App fechando!")
        try:
            if worker:
                worker.terminate()
                worker.is_running = False
            if thread and thread.isRunning():
                thread.quit()
                thread.wait(2000)
                if thread.isRunning():
                    thread.terminate()
                    thread.wait(1000)
        except:
            pass

    import atexit
    atexit.register(emergency_cleanup)

    worker.total_files_found.connect(on_total_found)
    worker.progress_update.connect(update_progress)
    worker.update_status.connect(update_status)
    worker.sync_finished.connect(on_sync_finished)
    worker.sync_failed.connect(on_sync_failed)

    if hasattr(parent, 'on_drive_sync_finished'):
        worker.sync_finished.connect(parent.on_drive_sync_finished)
    if hasattr(parent, 'on_drive_sync_failed'):
        worker.sync_failed.connect(parent.on_drive_sync_failed)

    progress.canceled.connect(on_canceled)
    thread.started.connect(worker.run)

    progress.show()

    import datetime
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    folder_info = f"{len(selected_folders)} pasta(s) selecionada(s)"
    print(f"🚀 [{timestamp}] Thread INICIADA para Drive sync de {folder_info}")
    thread.start()
