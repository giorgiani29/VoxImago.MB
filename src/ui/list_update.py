
from src.utils.utils import filter_existing_files


class list_update:
    @staticmethod
    def _sort_files(files, sort_order):
        if sort_order == "created_desc":
            return sorted(files, key=lambda x: x.get("createdTime", 0), reverse=True)
        elif sort_order == "created_asc":
            return sorted(files, key=lambda x: x.get("createdTime", 0))
        elif sort_order == "modified_desc":
            return sorted(files, key=lambda x: x.get("modifiedTime", 0), reverse=True)
        elif sort_order == "modified_asc":
            return sorted(files, key=lambda x: x.get("modifiedTime", 0))
        elif sort_order == "name_asc":
            return sorted(files, key=lambda x: x.get("name", "").lower())
        elif sort_order == "name_desc":
            return sorted(files, key=lambda x: x.get("name", "").lower(), reverse=True)
        return files

    @staticmethod
    def _load_files_for_filters(app, source):
        print(
            f"DEBUG: _load_files_for_filters chamado com source='{source}', current_filter='{app.current_filter}', advanced_filters='{app.advanced_filters}'")
        folder_id = app.current_folder_id
        filter_type = app.current_filter

        if not app.search_term and folder_id is None:
            if app.advanced_filters.get('is_starred') or app.advanced_filters.get('extension') not in [None, '']:
                filter_type = 'all'
                local_files = app.search_engine.load_files_paged(
                    'local', app.current_page, app.page_size, None, app.current_sort, filter_type, None, app.advanced_filters, explorer_special=app.explorer_special_active
                )
                drive_files = []
                if app.is_authenticated and app.show_drive_metadata:
                    drive_files = app.search_engine.load_files_paged(
                        'drive', app.current_page, app.page_size, None, app.current_sort, filter_type, None, app.advanced_filters, explorer_special=app.explorer_special_active
                    )
                all_files = local_files + drive_files
                return list_update._sort_files(all_files, app.current_sort)
            else:
                local_files = app.search_engine.load_files_paged(
                    'local', app.current_page, app.page_size, None, app.current_sort, filter_type, None, app.advanced_filters, explorer_special=app.explorer_special_active
                )
                drive_files = []
                if app.is_authenticated and app.show_drive_metadata:
                    drive_files = app.search_engine.load_files_paged(
                        'drive', app.current_page, app.page_size, None, app.current_sort, filter_type, None, app.advanced_filters, explorer_special=app.explorer_special_active
                    )
                all_files = local_files + drive_files
                if app.current_sort == "created_desc":
                    all_files = sorted(all_files, key=lambda x: x.get(
                        "createdTime", 0), reverse=True)
                elif app.current_sort == "created_asc":
                    all_files = sorted(
                        all_files, key=lambda x: x.get("createdTime", 0))
                elif app.current_sort == "modified_desc":
                    all_files = sorted(all_files, key=lambda x: x.get(
                        "modifiedTime", 0), reverse=True)
                elif app.current_sort == "modified_asc":
                    all_files = sorted(
                        all_files, key=lambda x: x.get("modifiedTime", 0))
                elif app.current_sort == "name_asc":
                    all_files = sorted(
                        all_files, key=lambda x: x.get("name", "").lower())
                elif app.current_sort == "name_desc":
                    all_files = sorted(all_files, key=lambda x: x.get(
                        "name", "").lower(), reverse=True)
                return all_files
        else:
            if app.advanced_filters.get('extension'):
                filter_type = 'all'
            files = app.search_engine.load_files_paged(
                source, app.current_page, app.page_size, app.search_term,
                app.current_sort, filter_type, folder_id, app.advanced_filters, explorer_special=app.explorer_special_active
            )
            if not app.show_drive_metadata:
                files = [f for f in files if not (
                    f.get('source') == 'drive' and not f.get('path'))]
            return list_update._sort_files(files, app.current_sort)

    @staticmethod
    def clear_display(app):
        app.all_loaded_label.hide()
        app.file_list_model.setFiles([])

        if hasattr(app.details_panel, 'thumbnail_thread') and app.details_panel.thumbnail_thread:
            try:
                if app.details_panel.thumbnail_thread.isRunning():
                    app.details_panel.thumbnail_thread.quit()
                    if not app.details_panel.thumbnail_thread.wait(2000):
                        pass
            except Exception as e:
                pass
        if hasattr(app.details_panel, 'thumbnail_worker') and app.details_panel.thumbnail_worker:
            try:
                app.details_panel.thumbnail_worker.deleteLater()
            except Exception as e:
                pass

        app.details_panel.thumbnail_worker = None
        app.details_panel.thumbnail_thread = None
        app.details_panel.hide()

    @staticmethod
    def load_next_batch(app):
        if app.is_loading or app.all_files_loaded:
            return

        app.is_loading = True
        app.loading_label.show()
        app.progress_bar.setVisible(True)
        app.progress_bar.setRange(0, 0)
        app.status_bar.showMessage("Carregando arquivos...", 0)

        try:
            app.indexer.ensure_conn()
            search_all_sources = bool(
                app.search_term and app.is_authenticated)
            source = app.current_view if not search_all_sources else None

            files_raw = list_update._load_files_for_filters(app, source)
            print(
                f"DEBUG: files_raw (primeiro item): {files_raw[0] if files_raw else 'VAZIO'}")
            files_to_add = filter_existing_files(
                files_raw, path_key='path' if files_raw and 'path' in files_raw[0] else 'caminho')
            print(
                f"DEBUG: files_to_add (primeiro item): {files_to_add[0] if files_to_add else 'VAZIO'}")
            print(
                f"DEBUG: Carregados {len(files_to_add)} arquivos para filtro '{app.current_filter}', source='{source}'")

            if not files_to_add:
                app.all_files_loaded = True
                if not app.file_list_model.rowCount():
                    app.loading_label.setText("Nenhum arquivo encontrado.")
                    app.loading_label.show()
                else:
                    app.loading_label.hide()
                    app.all_loaded_label.show()
            else:
                app._add_thumbnail_widgets(files_to_add)
                if len(files_to_add) < app.page_size:
                    app.all_files_loaded = True
                    app.all_loaded_label.show()
                app.current_page += 1
                app.loading_label.hide()

        except Exception as e:
            print(f"Erro ao carregar arquivos: {e}")
            app.loading_label.setText("Erro ao carregar arquivos.")
            app.loading_label.show()
        finally:
            app.is_loading = False
            app.scroll_loading = False
            app.progress_bar.setVisible(False)
            app.status_bar.showMessage("Arquivos carregados.", 3000)

    @staticmethod
    def update_file_list(app, source=None):

        list_update.clear_display(app)
        if source is None:
            source = app.current_view
        files = list_update._load_files_for_filters(app, source)
        app.file_list_model.setFiles(files)
        app.all_files_loaded = len(files) < app.page_size
        app.current_page = 1 if files else 0
