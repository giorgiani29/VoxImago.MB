# VoxImago - Guia Rápido de Referência

## Estrutura do Projeto Organizada
```
VoxImago.MB-main/
├── app.py                    # Ponto de entrada principal
├── data/                     # Dados do aplicativo
│   ├── file_index.db         # Banco de dados SQLite (movido)
│   ├── credentials.json      # Credenciais OAuth2 do Google
│   ├── token.json           # Token de autenticação
│   ├── settings.json        # Configurações do app
│   ├── last_sync.txt        # Timestamp da última sync
│   └── last_local_sync.txt  # Timestamp da última sync local
├── src/                     # Código fonte principal
│   ├── database.py          # Sistema de banco com normalização
│   ├── ui.py               # Interface gráfica + debug (F10/F11/F12)
│   ├── workers.py          # Workers de sincronização
│   ├── widgets.py          # Widgets customizados
│   ├── file_list_model.py  # Modelo de dados para listas
│   ├── file_list_delegate.py # Delegado para renderização
│   └── utils.py            # Utilitários gerais
├── tests/                   # Scripts de teste
│   ├── test_final.py       # Teste completo do sistema
│   ├── test_edge_cases.py  # Teste de casos extremos
│   └── analyze_code.py     # Análise de qualidade do código
├── scripts/                 # Scripts utilitários
├── tools/                   # Ferramentas auxiliares
├── config/                  # Arquivos de configuração
├── assets/                  # Recursos do aplicativo
├── docs/                    # Documentação
│   ├── QUICK_REFERENCE.md  # Este arquivo
│   ├── README_OPTIMIZACAO.md # Guia de otimização  
│   ├── DEBUG_GUIDE.md      # Guia de debug (F10/F11/F12)
│   └── GUIA_MVP.md         # Guia do MVP completo
├── README.md                # Documentação principal (padrão GitHub)
├── venv/                    # Ambiente virtual Python
├── icons/                   # Ícones do aplicativo (se houver)
└── thumbnail_cache/         # Cache de miniaturas
```

## Como Executar
```bash
# No diretório principal VoxImago.MB-main/
python app.py
```

## Sistema de Debug Integrado (F10/F11/F12)
- **F10**: Testa normalização de acentos com amostras automáticas
- **F11**: Mostra status completo do banco de dados
- **F12**: Analisa busca e normalização de texto

## Funcionalidades Principais
1. **Busca com Acentos Normalizada**: "formação" encontra "formacao" e vice-versa
2. **Sincronização Google Drive**: OAuth2 + metadados
3. **Índice FTS5**: Busca full-text com trigrams
4. **Cache de Thumbnails**: Miniaturas para visualização rápida

## Arquivos de Configuração (data/)
- `settings.json`: Configurações gerais
- `credentials.json`: Credenciais OAuth2 Google
- `token.json`: Token de acesso atual
- `file_index.db`: Base SQLite com FTS5

## Testes Disponíveis (tests/)
```bash
# Teste completo do sistema (recomendado)
python tests/test_final.py

# Teste de casos extremos e caracteres especiais
python tests/test_edge_cases.py

# Análise de qualidade do código
python analyze_code.py
```

## Principais Melhorias Implementadas
1. ✅ **Bug Crítico Corrigido**: FTS5 index não era mais destruído a cada inicialização
2. ✅ **Normalização de Acentos**: Sistema completo usando unicodedata NFD
3. ✅ **Compatibilidade Workers**: Schema 6 colunas totalmente suportado
4. ✅ **Sistema Debug**: F10/F11/F12 para debug em tempo real
5. ✅ **Projeto Organizado**: Estrutura limpa e lógica

## Status Atual (Setembro 2025)
- 🟢 **Funcional**: Sistema totalmente operacional com 107,022+ arquivos indexados
- 🟢 **Busca Bidirecional**: "formação" ↔ "formacao" funcionando perfeitamente
- 🟢 **Debug Integrado**: Hotkeys F10/F11/F12 operacionais e testados
- 🟢 **Sincronização Inteligente**: Timing de 30 minutos para evitar syncs desnecessários
- 🟢 **Qualidade do Código**: Zero funções não utilizadas, estrutura limpa

## Próximos Passos
1. Executar `python app.py` 
2. Usar F10/F11/F12 para testar funcionalidades
3. Verificar busca com e sem acentos
4. Monitorar performance com debug tools