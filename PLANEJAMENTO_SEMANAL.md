# Planejamento Semanal (20 a 26 de Outubro de 2025)


## ✅ Concluído (13-22/10)
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

---

### Prioridade Máxima: Aprimorar Sistema de Ordenação por Datas

**Tarefas:**
 - [x] Bug: arquivos locais não apareciam após sincronização, só após reiniciar o app
 - [x] Corrigir casos de data N/A no banco de dados (garantir datas válidas para todos os arquivos)
 - [x] Adicionar opção para forçar resincronização local (scan completo manual)
 - [ ] Revisar e corrigir sincronização local para garantir que novas pastas/arquivos sejam detectados corretamente (incrementalmente)
 - [ ] Adicionar lógica para excluir incrementalmente arquivos deletados localmente durante o rescan
 - [x] Aprimorar ordenação por data (garantir consistência e usabilidade)
 - [x] Garantir ordenação correta por tipo de arquivo (mesma abordagem da ordenação por data)
 - [ ] Normalizar acentuação e caracteres especiais em nomes e buscas (ex: "ú", "&")
 - [ ] Implementar menu contextual: abrir no Explorer, copiar caminho (lista e thumbnails)
 - [x] Gerar thumbnails para arquivos RAW e vídeos, ou exibir ícone padrão
 - [ ] Melhorar feedback e fluxo do token de autenticação (login/logout, expiração)
 - [ ] Revisar e aprimorar a UI conforme necessidades identificadas
 - [ ] Implementar busca híbrida para permitir encontrar tags curtas e símbolos (ex: <3, &boa, #a, @b)

**Critério de Sucesso:**
- Usuário consegue forçar resincronização local facilmente
- Sincronização incremental detecta corretamente arquivos/pastas novos e removidos
- Sistema não mantém "arquivos fantasmas" no banco
- Datas exibidas corretamente e ordenação funcional
- Menu contextual disponível e funcional
- Thumbnails para mais tipos de arquivos
- Busca e exibição sem problemas de acentuação
- UI mais intuitiva e responsiva
- Fluxo de autenticação robusto
- Usuário consegue ordenar arquivos facilmente por datas, tanto em grid quanto em lista.

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
