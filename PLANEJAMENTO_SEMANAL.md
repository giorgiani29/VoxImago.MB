# Planejamento Semanal (15 a 18 de Outubro de 2025)

## Quarta-feira (15/10)
- [x] Revisar e organizar logs detalhados do processo de fusão e sincronização.
- [x] Adicionar/improvar prints/logs para início/fim da fusão, progresso em lotes, deletes em lote e commits.
- [x] Validar se o feedback ao usuário está claro durante operações longas.

## Quinta-feira (16/10)
- [x] Refatorar o loop de fusão para usar updates em lote (`executemany`) se possível.(não funcionou)
- [x] Reduzir buscas SQL desnecessárias dentro do loop de fusão.
- [x] Garantir que os campos usados no matching tenham índices no banco.
- [x] Medir e comparar o tempo de execução antes/depois das mudanças. (Benchmark atual: count_files = 0.10s, load_files_paged = 0.03s)

## Sexta-feira (17/10)
- [ ] Implementar rollback e transações para garantir atomicidade em lotes grandes.
- [ ] Tratar exceções em todos os slots e sinais da interface PyQt6.
- [ ] Adicionar logs de falhas de fusão e conflitos de metadados.
- [ ] Padronizar nomes de arquivos de banco nos testes para evitar sobrescrita.

## Segunda-feira (20/10)
- [ ] Adicionar testes automatizados para o sistema de fusão, simulando cenários de conflito.
- [ ] Garantir tratamento de exceções em todos os scripts de teste/utilitários.
- [ ] Revisar dependências do requirements.txt para garantir que todas são usadas.
- [ ] Expandir a documentação com exemplos de uso avançado e explicação dos critérios de fusão.

## Para a próxima semana (caso não finalize)
- [ ] Permitir configuração do critério de matching (nome, tamanho, hash).
- [ ] Adicionar opção de preservar metadados locais caso já existam.
- [ ] Implementar opção de "dry-run" para simular fusão sem alterar o banco.
- [ ] Explorar processamento paralelo ou uso de dicionários em memória para matching.
- [ ] Considerar internacionalização (i18n) se o app for usado por públicos diversos.

