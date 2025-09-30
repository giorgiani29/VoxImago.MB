# Plano de Otimização do Projeto Vox Imago

Este documento descreve melhorias propostas para performance e escalabilidade do aplicativo.

---

## Otimizações pendentes e propostas


### Otimizações Prioritárias (Performance)

1. **Paginação de resultados na interface**
   - Exibir arquivos em páginas para evitar sobrecarga de memória e melhorar a navegação.

2. **Indexação Inteligente e Incremental**
   - Indexar a planilha/banco localmente, usando índices e PRAGMA para performance.
   - Sincronização incremental: atualizar apenas registros modificados (por data ou ID), economizando recursos.

3. **UI escalável com `QListView` + `QAbstractListModel`**
   - Migrar UI para modelo customizado para melhor performance em listas grandes.

4. **Lazy loading de metadados e thumbnails**
   - Buscar e exibir metadados e miniaturas apenas quando necessário, evitando carregar tudo de uma vez.

5. **Barra de loading dedicada na primeira sincronização**
   - Exibir uma janela de progresso para informar o usuário e evitar travamentos na interface.

---

### Outras Otimizações e Funcionalidades

6. **Busca Avançada e Explorer Especial**
   - Permitir busca de arquivos locais usando os metadados do Drive (inclusive descrição).
   - Exibir apenas arquivos locais, mas permitir busca/filtro por qualquer metadado do Drive.
   - Não exibir arquivos do Drive que não existem localmente.


7. **Profiling, logging e limpeza de código**
   - Adicionar logs de tempo e profiling (`cProfile`, `snakeviz`) para análise de performance.
   - Limpar funções duplicadas e código legado.

8. **Sincronização agendada ou em segundo plano**
   - Permitir atualização automática dos metadados em horários definidos ou quando o PC estiver ocioso.

9. **Notificações e logs claros**
   - Informar ao usuário sobre erros, progresso e resultados da sincronização.

10. **Filtros avançados**
   - Buscar por múltiplos campos, datas, favoritos, tipos de arquivo, etc.

11. **Exportação de resultados**
   - Permitir exportar listas de arquivos encontrados para CSV ou Excel.

12. **Perfil de uso e estatísticas**
   - Mostrar estatísticas de uso, arquivos mais acessados, etc.

13. **Configurações flexíveis**
   - Permitir ao usuário escolher quais Drives sincronizar, limitar por tamanho/tipo, etc.

14. **Segurança**
   - Criptografar dados sensíveis e proteger credenciais.

15. **Interface adaptável**
   - Modo escuro, responsividade, acessibilidade.

---

## Checklist de Entregáveis (Atualizado - Setembro 2025)

### ✅ **IMPLEMENTADO E FUNCIONANDO**
- [x] Paginação de resultados na interface ✅
- [x] UI com `QListView` + `QAbstractListModel` ✅
- [x] Lazy loading de metadados e thumbnails ✅
- [x] Barra de loading dedicada na primeira sincronização ✅
- [x] Explorer Especial (modo local apenas) ✅
- [x] Notificações e logs claros (status bar, tray, debug F10/F11/F12) ✅
- [x] Filtros avançados (extensão, datas, favoritos) ✅
- [x] Sistema de debug integrado (F10/F11/F12) ✅
- [x] Normalização de acentos completa ✅
- [x] Sincronização inteligente com timing de 30 minutos ✅
- [x] Qualidade de código (zero funções não utilizadas) ✅

### 🔄 **EM PROGRESSO / PARCIAL**
- [~] Busca avançada por metadados do Drive nos arquivos locais (Fusion básico implementado)
- [~] Profiling e logging (Debug system implementado, logging completo pendente)

### ⏳ **PENDENTE (BAIXA PRIORIDADE)**
- [ ] Sincronização incremental dos metadados (API Drive com delta)
- [ ] Sincronização agendada ou em segundo plano
- [ ] Exportação de resultados (CSV/Excel)
- [ ] Perfil de uso e estatísticas
- [ ] Configurações flexíveis
- [ ] Segurança avançada
- [ ] Interface adaptável

---

## 📊 Status Atual do Projeto (Setembro 2025)

### 🎯 **MVP COMPLETO E FUNCIONAL**
- **107,022+ arquivos indexados** com sucesso
- **Sistema de busca bidirecional** com acentos funcionando perfeitamente
- **Interface moderna** com tema escuro e system tray
- **Debug integrado** com hotkeys F10/F11/F12
- **Performance otimizada** com lazy loading e cache inteligente
- **Sincronização inteligente** evitando operações desnecessárias

### 🚀 **Funcionalidades Confirmadas**
1. ✅ Busca unificada (local + Google Drive)
2. ✅ Filtros avançados (tipo, extensão, data, favoritos)
3. ✅ Normalização de acentos ("formação" ↔ "formacao")
4. ✅ Cache de thumbnails com hash inteligente
5. ✅ System tray com menu contextual
6. ✅ Fusion system (metadados Drive → arquivos locais)
7. ✅ Paginação e lazy loading
8. ✅ Debug tools completos

### 📈 **Métricas de Qualidade**
- **0 funções não utilizadas** (análise AST completa)
- **Estrutura modular** bem organizada em src/
- **Testes automatizados** cobrindo casos extremos
- **Documentação** sincronizada e atualizada

---

## Notas de verificação (estado anterior):

- Sincronização incremental dos metadados: DriveSync busca a lista completa e faz upsert; não há filtro por `modifiedTime`/delta. LocalScan revarre diretórios. Falta implementar delta por data/hash e paginação de API do Drive com cutoff por alteração.
- Busca avançada por metadados do Drive nos arquivos locais: Existe FTS5 e busca unificada, mas não há vinculação robusta de metadados do Drive ao arquivo local equivalente. O “Explorer Especial” restringe a resultados locais, porém sem mesclar descrições do Drive.
- Explorer Especial: Implementado como modo de visualização local (filtro `source='local'`) e opção na UI.
- Notificações e logs: Há mensagens na status bar, notificações via `QSystemTrayIcon` e logs detalhados de geração de miniaturas. Ainda não há um logger central ou níveis (INFO/WARN/ERROR) configuráveis.
- Filtros avançados: Implementados (extensão, datas de criação/modificação, favoritos). Persistência básica via `settings.json`.
