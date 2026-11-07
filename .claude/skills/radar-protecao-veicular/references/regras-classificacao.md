# Regras de classificação

Fonte única das regras: `scripts/regras.py`. Mudou uma regra? Rode `python -m unittest discover -s tests`
e registre aqui o motivo.

## 1. Descoberta (universo de candidatas)

Uma empresa entra no universo se **qualquer** condição for verdadeira:

1. Razão social com termo FORTE (veicular, patrimonial/mutualista ou de categoria), em qualquer natureza jurídica.
2. Natureza associativa ou cooperativa **e** razão social com termo MÉDIO (indício de proteção ou contexto veicular).
3. Nome fantasia com termo FORTE.
4. CNAE 9499-5/00 (principal **ou** secundário) **e** (nome fantasia com termo MÉDIO **ou** e-mail com termo do setor).

Todos os estabelecimentos (matriz e filiais) dessas raízes são carregados. Por padrão, só situação **ATIVA**
(`--incluir-inativas` para histórico). O CNAE nunca exclui: entidades com 9430-8/00, 9411-1/00 e outros
aparecem quando o nome indica o setor.

## 2. Score cadastral (0-100)

| Evidência | Pontos |
|---|---:|
| Termo veicular forte no nome ("proteção veicular", "proteção a veículos", "auto proteção"...) | +45 |
| Termo patrimonial/mutualista forte ("proteção patrimonial", "mutualista", "socorro mútuo", "autogestão", "rateio de despesas") | +35 (ou +10 se já houver termo veicular) |
| Associação de categoria ("proprietários de veículos", "condutores de veículos") | +25 |
| Combinação proteção/benefício + contexto veicular no mesmo nome | +25 |
| Termos de reforço (até 2) | +10 cada |
| CNAE principal 9499-5/00 | +15 |
| CNAE secundário 9499-5/00 | +8 |
| CNAE relacionado (seguros, reboque, rastreamento...) | +7 |
| Natureza 399-9 Associação Privada | +15 |
| E-mail cadastral com termo do setor | +5 |
| Termo negativo (animal, ambiental, infância, sindicato, moto clube, veículos antigos, autoescola...) sem termo veicular forte | −60 |
| Cooperativa (fora do regime de PPM da LC 213/2025) | −20 |
| Natureza não associativa (Ltda, EIRELI...) | −25 |

Palavras isoladas como "proteção", "clube" ou "associação" **nunca** bastam: no máximo levam à classe 5.

## 3. Evidências externas (normalizar_dados.py)

| Evidência | Pontos |
|---|---:|
| Site vinculado (cita o CNPJ ou é o domínio do e-mail cadastral) descreve proteção veicular ou patrimonial | +25 |
| Site cita o CNPJ da entidade | +10 |
| SUSEP: cadastro confirmado por fonte oficial | +30 |

## 4. Classes

| Classe | Regra |
|---|---|
| **1 Confirmada** | Associação com nome veicular e (cadastro SUSEP oficial **ou** site que cita o CNPJ e descreve a operação); ou classe 3/5 cujo site que cita o CNPJ descreve proteção veicular |
| **2 Provável** | Associação, termo veicular forte ou combinação proteção+veículo, score ≥ 60; ou pendente com site/SUSEP favorável |
| **3 Patrimonial sem confirmação veicular** | Associação com termo patrimonial/mutualista forte, sem termo veicular |
| **4 Fora do escopo** | Termo negativo, score < 30, natureza não associativa (empresas do setor ficam com `subtipo = empresa_ecossistema_pv`), cooperativa, ou associação de categoria sem indício de proteção |
| **5 Pendente** | Demais casos com algum indício (clubes de benefícios, associações de condutores...) |

A classe é calculada por **entidade** (raiz do CNPJ): filiais herdam a melhor evidência da matriz.

## 5. SUSEP (LC 213/2025, Res. Susep 49/2025, Res. CNSP 491/2026)

| Código | Quando usar |
|---|---|
| `nao_verificado` | Padrão. Nenhuma consulta oficial importada |
| `cadastrada_em_regularizacao` | Certidão/consulta oficial mostra cadastro (status "Em regularização junto à Susep") |
| `regular` | Somente com evidência oficial explícita de regularidade. Pela página da SUSEP, regularidade exige contrato com administradora autorizada (Fase III, prazo 07/05/2028) |
| `nao_consta_oficial` | Certidão/consulta oficial negativa. Gera `alerta_susep`: requer análise jurídica |
| `nao_foi_possivel` | Fonte fora do ar, documento ilegível ou ambíguo |

Proibido: marcar irregular por ausência de resultado em busca automatizada; tratar cadastro como regularidade.
Referência de época: Fase I (cadastro) encerrou em 15/07/2025 com 2.217 associações concluídas, segundo a SUSEP.

## 6. Prioridade comercial (0-100, só evidências)

Canal confirmado no site que cita o CNPJ +25 (provável +12) · site ativo +10 · ≥2 estabelecimentos +10, ≥5 +5 ·
presença em mais de 1 UF +10 · sinais no site: sinistro +10, assistência 24h +5, vistoria +5, oficinas +5,
área do associado +5 · cadastro SUSEP +10. Faixas: **A ≥ 60**, **B 35-59**, **C < 35**.
Faturamento, associados e frota não entram: não há fonte pública confiável.

## 7. Validação (amostra 2026-11-07)

Amostra estratificada de 80 matrizes (seed 42), rotulada por revisão do nome e da natureza jurídica,
sem consulta externa: `tests/amostra_validacao.csv`.

| Classe (versão antes do ajuste) | Resultado da revisão |
|---|---|
| 2 (30) | 30 compatíveis com proteção veicular: precisão observada 100% |
| 3 (15) | 11 compatíveis, 2 falsos positivos, 2 ambíguos: 73% a 87% |
| 5 (15) | 6 claramente fora do setor, 9 ambíguos (esperado para "pendente") |
| 4 (20) | 18 negativos corretos, 1 falso negativo ("gestão de despesas de veículos"), 1 ambíguo |

As regras foram ajustadas com base nesses erros; o resultado pós-ajuste (classe 2: 30/30; classe 3: 12 positivos
e 2 ambíguos; classe 4: 27 negativos e 1 ambíguo) é otimista porque a mesma amostra orientou o ajuste.
Para medir de novo sem viés, sorteie outra amostra com outra seed.

## 8. Validação com a lista oficial SUSEP (2026-11-07)

Lista de entidades da SUSEP (gravação de tela): 2.572 linhas → 2.472 CNPJs válidos e únicos (92 zerados, 1 inválido,
7 duplicados SANDBOX) → 2.193 associações privadas (279 seguradoras e afins fora) → 2.097 ativas na Receita.

- Cobertura das regras antigas: 82,9% das associações ativas. Após os ajustes abaixo: 92,7% (sem usar a lista).
- Ajustes: negativo "RIO" virou "proteção do rio" ("Rio de Janeiro" era descartado); negativos deixam de valer com
  contexto veicular ("saúde de veículos"), exceto os duros (moto clube, veículos antigos, táxi, escolar, animal);
  associações de categoria (transportadores, caminhoneiros, proprietários de veículos) viram pendente, não descarte;
  "associados", "clube de assistência/vantagens", "rateio" e "garante" viram indício.
- Associações com evidência SUSEP entram no universo e são classe 1 (com segmento veicular) ou 3 (sem segmento).
- Segmento veicular (`regras.segmento_veicular`): carro/leves, caminhão/pesados (inclui transportadores, carreteiros,
  cegonheiros, graneleiros), moto, ou "geral" quando só há termo veicular genérico.
