"""
Script de teste de cenários de fusão - Simula conflitos e valida comportamento do sistema
Testa: diferentes cenários de fusão de metadados e resolução de conflitos
"""

import os
import sys
from database.database import FileIndexer
from database.search import SearchEngine
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

src_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)


class FusionTestScenarios:

    def __init__(self, test_db_path):
        self.test_db_path = test_db_path
        self.indexer = None
        self.setup_database()

    def setup_database(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

        self.indexer = FileIndexer(self.test_db_path)
        print(f"✅ Banco de teste criado: {self.test_db_path}")

    def cleanup(self):
        if self.indexer:
            self.indexer.close()
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        print("🧹 Recursos de teste limpos")

    def create_test_files(self):
        test_files = [
            {
                'file_id': 'local_001',
                'name': 'foto_familia.jpg',
                'path': '/home/user/fotos/foto_familia.jpg',
                'mimeType': 'image/jpeg',
                'source': 'local',
                'description': 'Foto da família no parque',
                'size': 2048576,
                'modifiedTime': 1609459200,
                'createdTime': 1609459200,
            },
            {
                'file_id': 'drive_001',
                'name': 'foto_familia.jpg',
                'mimeType': 'image/jpeg',
                'source': 'drive',
                'description': 'Foto da família no parque - versão Drive',
                'size': 2048576,
                'modifiedTime': 1609545600,
                'createdTime': 1609459200,
            },
            {
                'file_id': 'local_002',
                'name': 'documento_importante.pdf',
                'path': '/home/user/docs/documento_importante.pdf',
                'mimeType': 'application/pdf',
                'source': 'local',
                'description': '',
                'size': 1048576,
                'modifiedTime': 1609459200,
                'createdTime': 1609459200,
            },
            {
                'file_id': 'local_003',
                'name': 'documento_importante.pdf',
                'path': '/home/user/backup/documento_importante.pdf',
                'mimeType': 'application/pdf',
                'source': 'local',
                'description': 'Backup do documento importante',
                'size': 1048576,
                'modifiedTime': 1609459200,
                'createdTime': 1609459200,
            },
            {
                'file_id': 'drive_002',
                'name': 'documento_importante.pdf',
                'mimeType': 'application/pdf',
                'source': 'drive',
                'description': 'Versão atualizada do documento - Drive',
                'size': 1048576,
                'modifiedTime': 1609632000,
                'createdTime': 1609459200,
            },
            {
                'file_id': 'drive_003',
                'name': 'apresentacao_nova.pptx',
                'mimeType': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'source': 'drive',
                'description': 'Apresentação do novo projeto',
                'size': 3145728,
                'modifiedTime': 1609718400,
                'createdTime': 1609718400,
            }
        ]

        local_files = [f for f in test_files if f['source'] == 'local']
        self.indexer.save_files_in_batch(local_files, source='local')

        drive_files = [f for f in test_files if f['source'] == 'drive']
        return drive_files

    def simulate_fusion(self, drive_files):
        from src.drive.match import find_local_matches

        fusion_results = {
            'successful_fusions': 0,
            'failed_fusions': 0,
            'conflicts': 0,
            'logs': []
        }

        print(
            f"\n🔄 Iniciando simulação de fusão com {len(drive_files)} arquivos do Drive...")

        for drive_item in drive_files:
            print(
                f"\n🔍 Procurando matches para: '{drive_item['name']}' (tamanho: {drive_item['size']})")

            matches = find_local_matches(drive_item, self.indexer.cursor)

            if matches:
                if len(matches) > 1:
                    fusion_results['conflicts'] += 1
                    log_msg = f"⚠️ Conflito: Múltiplos matches ({len(matches)}) para '{drive_item['name']}'"
                    print(log_msg)
                    fusion_results['logs'].append(log_msg)

                for local_id in matches:
                    self.indexer.cursor.execute(
                        "SELECT description FROM files WHERE file_id = ?", (local_id,))
                    local_result = self.indexer.cursor.fetchone()

                    if local_result and local_result[0] and local_result[0] != drive_item['description']:
                        log_msg = f"⚠️ Conflito de descrição: local='{local_result[0][:30]}...', drive='{drive_item['description'][:30]}...'"
                        print(log_msg)
                        fusion_results['logs'].append(log_msg)

                try:
                    for local_id in matches:
                        self.indexer.cursor.execute(
                            "UPDATE files SET description = ?, thumbnailLink = ?, webContentLink = ? WHERE file_id = ?",
                            (drive_item['description'], drive_item.get('thumbnailLink', ''),
                             drive_item.get('webContentLink', ''), local_id)
                        )
                        self.indexer.cursor.execute(
                            "UPDATE search_index SET description = ?, normalized_description = ? WHERE file_id = ?",
                            (drive_item['description'], SearchEngine(None).normalize_text(
                                drive_item['description']), local_id)
                        )
                    fusion_results['successful_fusions'] += 1
                    print(
                        f"✅ Fusão realizada com sucesso para '{drive_item['name']}'")
                except Exception as e:
                    fusion_results['failed_fusions'] += 1
                    log_msg = f"❌ Erro na fusão: {e}"
                    print(log_msg)
                    fusion_results['logs'].append(log_msg)
            else:
                fusion_results['failed_fusions'] += 1
                log_msg = f"❌ Falha de fusão: Nenhum match encontrado para '{drive_item['name']}' (tamanho: {drive_item['size']})"
                print(log_msg)
                fusion_results['logs'].append(log_msg)

        self.indexer.conn.commit()
        return fusion_results

    def validate_results(self, results):
        print("\n📊 VALIDAÇÃO DOS RESULTADOS:")
        print(f"✅ Fusões bem-sucedidas: {results['successful_fusions']}")
        print(f"❌ Falhas de fusão: {results['failed_fusions']}")
        print(f"⚠️ Conflitos detectados: {results['conflicts']}")

        expected_successful = 2
        expected_failed = 1
        expected_conflicts = 1

        success = (results['successful_fusions'] == expected_successful and
                   results['failed_fusions'] == expected_failed and
                   results['conflicts'] == expected_conflicts)

        if success:
            print("✅ TODAS AS VALIDAÇÕES PASSARAM!")
        else:
            print("❌ ALGUMAS VALIDAÇÕES FALHARAM!")
            print(
                f"   Esperado: {expected_successful} sucessos, {expected_failed} falhas, {expected_conflicts} conflitos")
            print(
                f"   Obtido: {results['successful_fusions']} sucessos, {results['failed_fusions']} falhas, {results['conflicts']} conflitos")

        return success


def run_fusion_tests():
    print("🧪 TESTE AUTOMATIZADO: CENÁRIOS DE FUSÃO DE METADADOS")
    print("=" * 60)

    test_db = "data/test_fusion_scenarios.db"

    try:
        test_scenario = FusionTestScenarios(test_db)

        drive_files = test_scenario.create_test_files()

        results = test_scenario.simulate_fusion(drive_files)

        validation_passed = test_scenario.validate_results(results)

        print("\n📝 LOGS GERADOS:")
        for log in results['logs']:
            print(f"   {log}")

        if validation_passed:
            print("\n🎉 TESTE DE FUSÃO APROVADO!")
            return True
        else:
            print("\n❌ TESTE DE FUSÃO REPROVADO!")
            return False

    except Exception as e:
        print(f"❌ ERRO DURANTE TESTE: {e}")
        return False
    finally:
        if 'test_scenario' in locals():
            test_scenario.cleanup()


if __name__ == "__main__":
    success = run_fusion_tests()
    sys.exit(0 if success else 1)
