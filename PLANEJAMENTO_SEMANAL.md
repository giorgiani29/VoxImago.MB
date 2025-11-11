# Planejamento Semanal (11 a 17 de Novembro de 2025)

## 🎯 Foco da Semana: Experiência do Usuário e Interface

- Revisar e mapear pontos críticos da UI
- Refatorar código da interface para facilitar manutenção
- Remover funções não utilizadas para limpar o código e a interface
- Melhorar feedback visual e mensagens para o usuário
- Aprimorar navegação e usabilidade (pastas, buscas, filtros)
- Testar e validar melhorias de UX
- Documentar padrões e decisões de UI para o futuro

---

## 🔄 Backlog e Futuras Sprints

### Sincronização Híbrida e Incremental
- Monitorar criação/remoção local (watchdog)
- Implementar "soft delete" (is_present_local)
- Enriquecer metadados de novos arquivos
- Sincronizar mudanças da nuvem periodicamente
- Atualizar a UI com sinais/slots

### Robustez e Rollback
- Implementar e testar rollback completo
- Adicionar testes automatizados para rollback
- Documentar mecanismo de transações
- Validar integridade de dados após rollback
- Revisar dependências do requirements.txt
- Executar suite completa de testes

### Melhorias Futuras
- Configuração de critérios de matching
- Preservar metadados locais
- Implementar "dry-run" para fusão
- Explorar processamento paralelo
- Considerar internacionalização (i18n)

---

## ✅ Concluído recentemente
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
