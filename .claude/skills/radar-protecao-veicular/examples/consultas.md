# Exemplos de uso (saídas reais do piloto, base CNPJ 2026-10)

## "Encontre associações de proteção veicular em Goiás, Mato Grosso e Tocantins, com CNPJs e contatos comerciais"

```bash
python scripts/enriquecer_contatos.py --uf GO MT TO --classes 1 2 3
python scripts/normalizar_dados.py
python scripts/consultar.py --uf GO MT TO --classes 1 2 3 --com-contato
python scripts/exportar_resultados.py --uf GO MT TO --nome piloto_go_mt_to
```

Resultado do piloto: 234 entidades nas classes 1, 2, 3 e 5 (GO 168, MT 44, TO 22);
5 confirmadas (classe 1), 99 prováveis, 64 patrimoniais sem confirmação veicular, 66 pendentes; 625 descartadas
com justificativa. Contatos: 5 confirmados no site oficial (CNPJ citado), 7 prováveis, demais só declarados à Receita.
Ver `piloto_classe1_amostra.csv`.

## "Apresente os dirigentes públicos da associação MAXCAR, com fontes"

```bash
python scripts/consultar.py --nome "MAXCAR"
```
Retorna a ficha com `dirigentes_publicos` (nome, cargo, data de entrada no QSA) e `fontes`
(Receita Federal, competência 2026-10; site oficial lido). Sem CPF.

## "Quais associações têm presença em Goiânia e Anápolis e canais comerciais verificáveis?"

```bash
python scripts/consultar.py --municipio GOIANIA ANAPOLIS --com-contato
```

## "Quais entidades da minha base têm situação confirmada na SUSEP e quais exigem conferência?"

```bash
python scripts/consultar.py --susep
python scripts/validar_susep.py fila --uf GO MT TO     # gera out/fila_susep.xlsx para conferência manual
python scripts/validar_susep.py importar --arquivo out/fila_susep.xlsx
```

## "Gere uma planilha XLSX com as associações verificadas, separadas por UF, com dicionário de colunas"

```bash
python scripts/exportar_resultados.py --classes 1 2 --nome verificadas
```
Abas: Resumo, uma por UF, Dicionario, Classes. Filtro e cabeçalho congelado em todas.

## Pergunta livre (SQL)

```bash
python scripts/consultar.py --sql "select uf, count(distinct cnpj_basico) entidades from base where classe in (1,2) group by 1 order by 2 desc"
```
