# Manual de manutenção

## Rotina mensal (a Receita publica uma competência por mês)

```bash
python scripts/baixar_cnpj.py --listar                # confira a competência nova
python scripts/baixar_cnpj.py                         # baixa e marca como atual
python scripts/filtrar_associacoes.py                 # ~30 s Brasil inteiro
python scripts/enriquecer_contatos.py --classes 1 2 3 # só sites sem cache são lidos de novo
python scripts/normalizar_dados.py
python scripts/exportar_resultados.py --nome nacional_AAAA_MM
```

- Competências antigas ficam em `$RADAR_PV_DATA/raw/AAAA-MM`. Apague as que não precisa (≈5 GB cada).
- Para comparar meses: `consultar.py --sql` sobre dois `base_final.parquet` renomeados, ou guarde as exportações datadas.
- Cache de sites: `$RADAR_PV_DATA/cache/sites`. Apague para forçar releitura (ex.: a cada trimestre).
- Logs: `$RADAR_PV_DATA/logs/*.log`.

## Atualização incremental

- Download: arquivos já completos (mesmo tamanho do manifesto) não são baixados de novo; `.part` retoma via HTTP Range.
- Enriquecimento: resultados novos substituem os antigos do mesmo CNPJ; o restante é preservado.
- SUSEP: cada importação substitui só os CNPJs importados.

## Corrigir uma classificação

1. Falso positivo/negativo recorrente: ajuste `scripts/regras.py` (termos ou pesos).
2. Adicione o caso em `tests/test_regras.py` (lista de positivos ou negativos) e rode
   `python -m unittest discover -s tests -v`.
3. Registre o motivo em `references/regras-classificacao.md`.
4. Caso isolado (uma entidade): prefira evidência externa. Informe o site correto em `--sites` ou importe a
   situação SUSEP; a classe é recalculada em `normalizar_dados.py`.

## Repetir pesquisas

| Objetivo | Comando |
|---|---|
| Nova UF ou município | `consultar.py --uf XX` / `--municipio NOME` |
| Ampliar contatos | `enriquecer_contatos.py --uf XX --classes 1 2 3 5` |
| Sites encontrados manualmente | CSV `cnpj,url` → `enriquecer_contatos.py --sites arquivo.csv` |
| Conferir SUSEP | `validar_susep.py fila --uf XX` → preencher → `validar_susep.py importar --arquivo` |
| Medir precisão de novo | sortear amostra com outra seed (ver `regras-classificacao.md` §7) e rotular |

## Integração futura com CRM

Chave de integração: `cnpj` (14 dígitos) para estabelecimento e `cnpj_basico` (8) para a conta/entidade.

| CRM | Mapeamento sugerido |
|---|---|
| Conta (Account/Company) | `cnpj_basico`, `razao_social`, `nome_fantasia`, `uf`, `municipio`, `site_institucional`, `classe`, `score_confianca`, `prioridade_comercial`, `status_susep` |
| Contatos (Contact) | `dirigentes_publicos` (um contato por dirigente, cargo = qualificação; **sem telefone pessoal**) |
| Canais | `whatsapp_comercial_confirmado`, `telefones_site`, `emails_site` (marcar origem = site oficial) |
| Campos de qualificação | `sinal_*`, `indicios_software_gestao`, `oportunidade_gestao_digital`, `qtd_estabelecimentos_ativos`, `ufs_atuacao` |

Fluxo recomendado: exportar JSON (`exportar_resultados.py`) → upsert por `cnpj_basico` via API do CRM
(HubSpot, Pipedrive, RD Station) em script separado, com credenciais em variável de ambiente.
Respeite opt-out: mantenha uma lista de supressão (`cnpj`/e-mail) e filtre antes de cada carga.

## LGPD e boas práticas

- Finalidade: prospecção B2B de pessoas jurídicas. Dados de pessoas físicas limitados a nome e cargo públicos do QSA.
- Não enriqueça dirigentes com dados pessoais externos (telefone, endereço, redes sociais pessoais).
- Primeiro contato deve identificar a origem dos dados (base pública do CNPJ / site institucional) e oferecer opt-out.
- Guarde as exportações com acesso restrito; não publique a base com nomes de dirigentes em repositório público.
