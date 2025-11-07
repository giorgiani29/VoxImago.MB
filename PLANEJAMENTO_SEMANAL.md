# Planejamento Semanal (01 a 19 de Novembro de 2025)


## ✅ Concluído
- Logs detalhados do processo de fusão e sincronização
- Prints/logs para início/fim da fusão, progresso em lotes
- Tentativa de refatoração com `executemany` (não funcionou)
- Otimização de buscas SQL e índices no banco
- Benchmark: count_files = 0.10s, load_files_paged = 0.03s
- Tratamento de exceções nos slots PyQt6
- Logs de falhas de fusão e conflitos de metadados
- Padronização de nomes de arquivos de banco nos testes
- Implementar visualização organizada por data (mais recente para mais antiga)
- Melhorar qualidade e tamanho dos thumbnails (visualização maior e mais nítida)
- Implementar Grid View para exibição dos arquivos
- Atualizar RELATORIO_TESTES.md com as melhorias aplicadas
- Bug: arquivos locais não apareciam após sincronização, só após reiniciar o app
- Corrigir casos de data N/A no banco de dados (garantir datas válidas para todos os arquivos)
- Adicionar opção para forçar resincronização local (scan completo manual)
- Aprimorar ordenação por data (garantir consistência e usabilidade)
- Garantir ordenação correta por tipo de arquivo (mesma abordagem da ordenação por data)
- Gerar thumbnails para arquivos RAW e vídeos, ou exibir ícone padrão
- Corrigir exibição do caminho do arquivo no painel de preview para usar barras consistentes
- Normalizar acentuação e caracteres especiais em nomes e buscas (ex: "ú", "&")
- Implementar menu contextual: abrir no Explorer, copiar caminho (lista e thumbnails)
- Implementar padrão de data baseado no diretório raiz "Banco de Imagens" (ano) e considerar a mais antiga entre data de criação e modificação
- Melhorar feedback e fluxo do token de autenticação (login/logout, expiração)
- Modularizar eventos de seleção e duplo clique da lista de arquivos (sinais customizados no FileListView)
- Implementar busca híbrida para permitir encontrar símbolos (ex: <3, &boa, #a, @b)
- Investigar e aprimorar suporte a thumbnails HEIC e RAW (especialmente ARW, CR2, etc.) no Windows

---

### Prioridade Máxima: Sincronização Híbrida e em Tempo Real

**Tarefas:**

- [ ] **Monitorar Criação/Remoção Local:** Implementar `watchdog` para detectar quando um arquivo aparece ou desaparece da pasta local.
- [ ] **Implementar "Soft Delete":** Criar uma coluna `is_present_local` no banco. Ao invés de deletar, marcar o arquivo como ausente se ele sumir da pasta.
- [ ] **Enriquecer Metadados de Novos Arquivos:** Quando um novo arquivo for detectado, buscar imediatamente seus metadados (descrição, etc.) na API do Drive e atualizar o banco.
- [ ] **Sincronizar Mudanças da Nuvem:** Usar um `QTimer` para, periodicamente, buscar por arquivos modificados na nuvem e atualizar os metadados no banco local.
- [ ] **Atualizar a UI com Sinais/Slots:** Garantir que a UI recarregue a visualização após qualquer mudança, usando o sistema de sinais e slots do PyQt para comunicação segura entre threads.

**Critério de Sucesso:**
- Novos arquivos na pasta local aparecem na UI quase instantaneamente com metadados completos do Drive.
- Arquivos removidos da pasta local desaparecem da UI, mas seus metadados são preservados no banco.
- Alterações na descrição de um arquivo feitas no Google Drive são refletidas na UI após o ciclo de verificação.
- A aplicação permanece responsiva e estável durante todas as operações de sincronização.
- O uso de CPU/rede é mínimo, pois apenas mudanças são processadas.

---

## segunda-feira (10/11) - Foco em Robustez e Rollback
- [ ] Implementar e testar rollback completo para operações críticas
- [ ] Adicionar testes automatizados para rollback durante fusão de metadados e deletes em lote
- [ ] Documentar o mecanismo de transações no código
- [ ] Validar integridade de dados após rollback
- [ ] Revisar dependências do requirements.txt
- [ ] Executar suite completa de testes e atualizar relatório

## Para as próximas semanas
- [ ] Permitir configuração do critério de matching (nome, tamanho, hash)
- [ ] Adicionar opção de preservar metadados locais caso já existam
- [ ] Implementar opção de "dry-run" para simular fusão sem alterar o banco
- [ ] Explorar processamento paralelo ou uso de dicionários em memória para matching
- [ ] Considerar internacionalização (i18n) se o app for usado por públicos diversos
