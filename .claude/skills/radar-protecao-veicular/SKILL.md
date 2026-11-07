---
name: radar-protecao-veicular
description: Mapeia associações de proteção veicular e patrimonial mutualista no Brasil (26 UFs + DF) a partir da base aberta do CNPJ da Receita Federal, com classificação por evidências, dirigentes públicos (QSA), validação de contatos no site oficial, fila de conferência SUSEP (LC 213/2025) e exportação CSV/XLSX/JSON. Use quando o usuário pedir para encontrar, listar, qualificar, prospectar ou exportar associações de proteção veicular, APVs, clubes de benefícios veiculares, socorro mútuo, proteção patrimonial mutualista, seus CNPJs, dirigentes, contatos ou situação na SUSEP, por estado ou município.
---

# Radar de Associações de Proteção Veicular

Você opera uma base local (DuckDB/Parquet) construída a partir de fontes oficiais. **Nunca invente**
CNPJ, telefone, WhatsApp, dirigente, faturamento, número de associados ou frota. Toda afirmação
deve vir de uma coluna da base com sua fonte, ou ser marcada como "não verificado".

Scripts em `scripts/` (Python 3.10+). Dados em `$RADAR_PV_DATA` (padrão `~/.radar_pv`).
Rode os comandos a partir da pasta da Skill: `cd .claude/skills/radar-protecao-veicular`.

## 1. Garantir que a base existe e está atual

```bash
python scripts/baixar_cnpj.py --listar          # competências disponíveis
python scripts/baixar_cnpj.py                   # baixa a mais recente (~5 GB, retoma se cair)
python scripts/filtrar_associacoes.py           # descoberta nacional (~30 s)
python scripts/normalizar_dados.py              # consolida a ficha final
```

Se `~/.radar_pv/raw/competencia.json` não existir, rode os quatro. Se a Receita publicou
competência mais nova (o download avisa), atualize antes de responder sobre "situação atual".

## 2. Mapear pedido em linguagem natural → comando

| Pedido do usuário | Comando |
|---|---|
| "Mapeie todas as associações do Brasil por estado" | `python scripts/exportar_resultados.py --nome nacional` e leia `out/nacional_relatorio.md` |
| "Associações em GO, MT e TO com CNPJ e contatos" | `python scripts/consultar.py --uf GO MT TO --classes 1 2 3` (enriqueça antes: passo 3) |
| "Dirigentes da associação X, com fontes" | `python scripts/consultar.py --nome "X"` (campo `dirigentes_publicos` + `fontes`) |
| "Presença em Goiânia e Anápolis com canais verificáveis" | `python scripts/consultar.py --municipio GOIANIA ANAPOLIS --com-contato` |
| "Quais têm situação SUSEP confirmada e quais exigem conferência?" | `python scripts/consultar.py --susep` e `python scripts/validar_susep.py fila` |
| "Gere XLSX das verificadas, separadas por UF, com dicionário" | `python scripts/exportar_resultados.py --classes 1 2 --nome verificadas` |
| "Crie um dashboard / painel HTML com os dados" | `python scripts/gerar_dashboard.py` → `out/radar_dashboard.html` (arquivo único, offline) |
| Pergunta analítica livre | `python scripts/consultar.py --sql "select ... from base ..."` (colunas em `references/dicionario-dados.md`) |

## 3. Enriquecer contatos (antes de falar em "contato confirmado")

```bash
python scripts/enriquecer_contatos.py --uf GO MT TO --classes 1 2 3
python scripts/normalizar_dados.py
```
Lê só o site oficial (domínio do e-mail cadastral próprio, ou CSV `--sites cnpj,url` informado pelo
usuário). Respeita robots.txt, 1 req/s, máx. 4 páginas. Contato só é **confirmado** quando o site cita o CNPJ.

## 4. SUSEP: nunca concluir irregularidade sozinho

A consulta oficial tem reCAPTCHA: **não contorne**. Gere a fila (`validar_susep.py fila`), o usuário
confere manualmente e você importa (`validar_susep.py importar --arquivo ...`). Regras em
`references/regras-classificacao.md` §SUSEP. Cadastro ≠ regularidade. Ausência de resultado ≠ irregular.

## 5. Como responder

- Diga a competência da base (`competencia_cnpj`) e a data da coleta.
- Use as classes 1-5 e o `score_confianca`; explique as `evidencias`.
- Separe "declarado à Receita" (pode ser do contador) de "confirmado no site oficial".
- Associação civil não tem dono: fale em presidente, diretores e representantes (QSA), sem chamar de proprietário.
- Capital social: use `capital_social_status` (informado, zero_informado, ausente_na_base).
- Não exponha CPF (a Skill não coleta), endereço residencial ou telefone pessoal.
- Não afirme cobertura nacional completa. Cite as limitações do relatório.

Referências: `references/fontes.md`, `references/dicionario-dados.md`,
`references/regras-classificacao.md`, `references/manual-manutencao.md`, `references/relatorio-pesquisa.md`.
