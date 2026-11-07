# Relatório de pesquisa e decisão técnica (2026-11-07)

## TL;DR

Nenhum repositório open source resolve o problema inteiro: todos cobrem a base CNPJ, nenhum classifica
proteção veicular, valida contatos ou trata a SUSEP. **Decisão: construir uma Skill integradora**
(`radar-protecao-veicular`), sem código de terceiros embutido, usando a base oficial da Receita (ou o espelho
Parquet do CNPJ Aberto) + DuckDB. Ideias de vilquer/CNPJ_RFB (retomada, Parquet) e leorochasf/cnpj-mcp
(consulta DuckDB) foram reimplementadas, não copiadas (a do leorochasf é AGPL-3.0).

## Método

Código lido, sem instalar nem executar nada de terceiros (clone raso, profundidade 30). Buscas no GitHub com os
termos do briefing ("cnpj receita federal", "cnpj mcp", "cnpj duckdb", "cnpj parquet", "cnpj socios",
"protecao veicular", "susep", "brasilapi", "cnpj enrichment"...). Buscas por "protecao veicular" e "susep" não
retornaram projeto útil. Nenhuma Skill pronta de pesquisa de empresas brasileiras foi encontrada.

## Ranking (nota 0-100)

Pesos: Cobertura CNPJ 25 · Dirigentes/contatos 20 · Atualização 15 · Integração Claude/MCP 15 · Segurança/licença 15 · Implantação 10.

| # | Repositório | Licença | Último commit | Cob | Dir | Atu | MCP | Seg | Impl | **Total** |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | [leorochasf/cnpj-mcp](https://github.com/leorochasf/cnpj-mcp) | AGPL-3.0 | 2026-10-16 | 18 | 17 | 11 | 15 | 8 | 9 | **78** |
| 2 | [wendersoon/radar-cnpj-mcp](https://github.com/wendersoon/radar-cnpj-mcp) ¹ | MIT | 2026-11-03 | 18 | 10 | 13 | 15 | 11 | 8 | **~75** |
| 3 | [vilquer/CNPJ_RFB](https://github.com/vilquer/CNPJ_RFB) | MIT | 2026-07-15 | 23 | 15 | 12 | 2 | 14 | 8 | **74** |
| 4 | [cuducos/minha-receita](https://github.com/cuducos/minha-receita) ¹ | verificar | 2026-01-04 | 24 | 16 | 13 | 6 | 9 | 6 | **~74** |
| 5 | [fonsecach/dados-publicos-cnpj](https://github.com/fonsecach/dados-publicos-cnpj) | MIT | 2026-09-25 | 24 | 16 | 14 | 3 | 10 | 5 | **72** |
| 6 | [BrasilAPI/BrasilAPI](https://github.com/BrasilAPI/BrasilAPI) ¹ | MIT | 2026-11-06 | 12 | 12 | 13 | 4 | 12 | 10 | **~63** |
| 7 | [adntayer/dados-publicos-cnpj-receita-federal](https://github.com/adntayer/dados-publicos-cnpj-receita-federal) | MIT | 2025-02-23 | 22 | 14 | 5 | 0 | 14 | 7 | **62** |
| 8 | [libercapital/dados_publicos_cnpj_receita_federal](https://github.com/libercapital/dados_publicos_cnpj_receita_federal) | MIT | 2024-11-28 | 21 | 14 | 3 | 0 | 11 | 5 | **54** |

¹ Avaliado só pelos metadados da busca no GitHub; código não auditado. Auditar antes de adotar.
Outros vistos: DeHor-Labs/mcp-fiscal-brasil (MIT), bnovarini/cnpj-mcp (MIT), rictom/rede-cnpj (MIT, grafo societário),
rictom/cnpj-sqlite (MIT), Hitmasu/OpenCNPJ (MIT), caiopizzol/cnpj-data-pipeline (sem licença).

### Limitações por candidato

- **leorochasf/cnpj-mcp**: único MCP pronto, mas envia cada CNPJ/nome consultado para minhareceita.org, OpenCNPJ,
  CNPJá e DJEN (`index.js:54-56, 75`), o que expõe a lista de prospecção; telefone/e-mail só via essas APIs; 2 commits;
  AGPL obriga abrir o código se oferecido em rede.
- **vilquer/CNPJ_RFB**: o mais limpo (só contata a Receita, URL nova, retomada, DuckDB), mas sem MCP e pede ~40 GB / 16 GB RAM.
- **fonsecach**: mais completo e mantido, porém PostgreSQL + Python 3.13 exato e **desliga verificação TLS**
  (`src/etl/ETL_dados_publicos_empresas.py:62-63, 342-343, 559-560, 688-689`).
- **adntayer / libercapital**: URLs antigas da Receita (pré-Nextcloud), sem manutenção; libercapital usa senha padrão `postgres`.
- **Todos**: nenhum classifica setor, valida contato, lida com SUSEP ou trata QSA de associação.

## Decisão

| Opção | Veredito |
|---|---|
| Instalar uma solução pronta | Rejeitada: nenhuma cobre classificação, SUSEP e validação de contatos |
| Adaptar um projeto | Rejeitada como base: AGPL (leorochasf) ou infraestrutura pesada (fonsecach/vilquer) para um caso que cabe em DuckDB local |
| **Construir Skill integradora** | **Escolhida**: ~1.500 linhas Python, só leitura, DuckDB/Parquet, sem APIs de terceiros, compatível com Windows |

## Auditoria red team (Fase 8)

| # | Pergunta | Resposta |
|---|---|---|
| 1 | Licenças compatíveis? | Sim. Nenhum código de terceiros incluído. Dados: Receita (dados abertos); espelho HF declara "dados abertos do governo federal". |
| 2 | Encontra quem não usa CNAE 9499-5/00? | Sim. Ex.: FORZA (9430-8/00), SERIGY (9411-1/00), ASSOCIECAR (9430-8/00) aparecem como classe 2. Teste `test_cnae_diferente_nao_exclui`. |
| 3 | Falsos positivos? | Medidos: classe 2 com 30/30 compatíveis na amostra; ruído concentrado na classe 5 (pendente), por desenho. Proteção animal, ambiental, infância, moto clubes, taxistas e autoescolas vão para classe 4. |
| 4 | Dirigente atualizado? | Não garantido: QSA reflete o último registro na Receita (data de entrada exibida). Confirmar por ata/estatuto ou SUSEP em decisões críticas. |
| 5 | Capital social correto? | Parse do formato oficial "120000000000,00"; distingue informado, zero informado e ausente. Teste `test_capital_social`. |
| 6 | Contatos pertencem à entidade? | Só "confirmado" quando o site cita o CNPJ. E-mails de contador (`contabil`, `.cnt.br`, `assessoria`) não viram site. Achado: várias associações registram e-mail do contador na Receita. |
| 7 | SUSEP diferencia cadastro de regularidade? | Sim, 5 status; nenhum "irregular" automático; certidão negativa gera alerta jurídico. |
| 8 | Rastreabilidade? | Cada linha tem `evidencias`, `fontes`, `competencia_cnpj`, `coletado_em`, URL do site lido e evidência SUSEP. |
| 9 | LGPD, termos e limites? | robots.txt, 1 req/s, sem CAPTCHA, sem login, sem engenharia reversa de API SUSEP, sem CPF. |
| 10 | Envia dados a terceiros? | Não. Únicos hosts: Receita/HF (download), SUSEP (nenhuma chamada automática) e o site da própria entidade. |

## Achados de mercado

- Universo nacional identificado (competência 2026-10, só ativas): ~1.238 entidades classe 2 + ~702 classe 3,
  ordem de grandeza compatível com as **2.217 associações** que concluíram o cadastro SUSEP (Fase I).
- Concentração: MG (~570 entidades classes 1-3), PE, RJ, BA, SP, GO e SC.
- Associações **têm QSA público** na base aberta (presidente, diretores), o que viabiliza a pesquisa de dirigentes.
- **Gestoras/escritórios concentram carteiras**: o mesmo domínio de e-mail cadastral aparece em até 18 associações
  de 3 UFs (8 domínios com 7 a 18 entidades cada). Campo `email_compartilhado_qtd_entidades`. Implicação B2B:
  um contrato com o back-office pode alcançar várias associações; confirmar o vínculo antes da abordagem.
- **Software de gestão**: Hinova aparece em 6 dos 12 sites lidos no piloto; iLeva e PowerCRM em 1 cada.
  Indício de concorrente dominante, não prova de contrato.
