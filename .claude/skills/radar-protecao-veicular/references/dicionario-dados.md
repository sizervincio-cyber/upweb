# Dicionário de dados

Uma linha por **estabelecimento** (matriz ou filial). Classe, score e SUSEP valem para a **entidade** (raiz de 8 dígitos do CNPJ) e são herdados pelas filiais.

Regras de interpretação:

- **Associação civil não tem proprietário.** `dirigentes_publicos` traz presidente, diretores e demais registros do QSA publicados pela Receita. Não presuma que dirigente seja dono ou que fundador ainda atue.
- **Dirigente pode estar desatualizado**: o QSA reflete o último registro na Receita (veja a data de entrada). Para decisões críticas, confira ata/estatuto ou o cadastro SUSEP.
- **Capital social**: `informado` (valor > 0), `zero_informado` (a Receita registra 0,00) ou `ausente_na_base`. Não é faturamento. Na competência 2026-10, 99,6% das associações têm capital zero (associação civil não tem capital como empresa), então capital **não mede porte de associação**. Para empresas do setor (Ltda/S.A.: regionais, consultorias, possíveis administradoras de PPM) o campo é informado em 97% dos casos e é útil.
- **Contatos da Receita** podem ser do escritório contábil. Só `confirmado_site_cita_cnpj` comprova vínculo com a entidade.
- **Não coletado por desenho (LGPD)**: CPF (nem mascarado), faixa etária, representante legal de sócio menor, endereço residencial, telefone pessoal.

Campos não inventados: faturamento, número de associados e frota **não existem** na base, por falta de fonte oficial pública.

## Identificação

| Coluna | Descrição |
|---|---|
| `cnpj_formatado` | CNPJ completo (14 digitos, formatado) |
| `matriz_filial` | MATRIZ ou FILIAL |
| `razao_social` | Razao social (Receita) |
| `nome_fantasia` | Nome fantasia (Receita) |
| `natureza_juridica` | Codigo da natureza juridica |
| `natureza_juridica_desc` | Descricao da natureza juridica |
| `subtipo` | associacao | cooperativa | empresa_ecossistema_pv | outra_natureza |

## Atividade

| Coluna | Descrição |
|---|---|
| `cnae_fiscal_principal` | CNAE principal (7 digitos) |
| `cnae_principal_desc` | Descricao do CNAE principal |
| `cnae_fiscal_secundaria` | CNAEs secundarios (separados por virgula) |

## Localização

| Coluna | Descrição |
|---|---|
| `uf` | UF do estabelecimento |
| `municipio` | Municipio (tabela Receita) |
| `bairro` | Bairro |
| `endereco_empresarial` | Endereco empresarial (Receita) |
| `cep` | CEP |

## Contatos

| Coluna | Descrição |
|---|---|
| `telefone_institucional_receita` | Telefones declarados a Receita (podem ser do contador) |
| `email_cadastral` | E-mail declarado a Receita |
| `email_cadastral_tipo` | dominio_proprio | gratuito | provavel_terceiro_contador | ausente |
| `site_institucional` | Site oficial lido (vinculo validado) |
| `site_candidato` | Site candidato: dominio proprio do e-mail cadastral (nao verificado ate ser lido) |
| `site_situacao` | validado_cita_cnpj, validado_dominio_cadastral, candidato_nao_verificado, inacessivel_na_coleta, bloqueia_robos, sem_site_identificado |
| `contato_status` | confirmado_site_cita_cnpj | provavel_site_dominio_cadastral | somente_declarado_receita | sem_contato_publico |
| `whatsapp_comercial_confirmado` | WhatsApp publicado no site que cita o CNPJ |
| `whatsapp_site_nao_confirmado` | WhatsApp em site sem citacao do CNPJ (conferir) |
| `telefones_site` | Telefones publicados no site oficial |
| `emails_site` | E-mails publicados no site oficial |
| `redes_sociais` | Redes sociais linkadas no site oficial |

## Administração

| Coluna | Descrição |
|---|---|
| `dirigentes_publicos` | QSA publico: nome (qualificacao, data de entrada). Sem CPF |
| `qtd_dirigentes_qsa` | Quantidade de registros no QSA |

## Dados cadastrais

| Coluna | Descrição |
|---|---|
| `data_abertura` | Data de inicio de atividade |
| `situacao_cadastral_desc` | Situacao cadastral na Receita |
| `porte_desc` | Porte cadastral |
| `capital_social_valor` | Capital social (campo oficial, R$) |
| `capital_social_status` | informado | zero_informado | ausente_na_base |

## SUSEP

| Coluna | Descrição |
|---|---|
| `status_susep` | Codigo da situacao SUSEP |
| `status_susep_desc` | Descricao da situacao SUSEP |
| `data_consulta_susep` | Data da consulta SUSEP |
| `evidencia_susep` | Evidencia SUSEP (certidao, protocolo, lista oficial) |
| `alerta_susep` | Alerta juridico quando ha certidao negativa |

## Inteligência comercial

| Coluna | Descrição |
|---|---|
| `qtd_estabelecimentos_ativos` | Estabelecimentos ativos da mesma raiz (matriz+filiais) |
| `ufs_atuacao` | UFs com estabelecimento ativo |
| `email_compartilhado_qtd_entidades` | Quantas entidades usam o mesmo dominio de e-mail (indicio de gestao comum) |
| `sinal_assistencia_24h` | Site cita assistencia 24h/guincho |
| `sinal_vistoria` | Site cita vistoria |
| `sinal_sinistro` | Site cita sinistro/evento/indenizacao |
| `sinal_oficinas` | Site cita oficinas/rede credenciada |
| `sinal_rastreamento` | Site cita rastreamento |
| `sinal_area_associado` | Site tem area/app do associado |
| `indicios_software_gestao` | Indicios de software de gestao no site (nao prova contrato) |
| `oportunidade_gestao_digital` | Leitura comercial baseada nos sinais |
| `prioridade_comercial_score` | Prioridade comercial 0-100 (somente evidencias) |
| `prioridade_comercial` | A (>=60) | B (35-59) | C (<35) |

## Auditoria

| Coluna | Descrição |
|---|---|
| `classe` | Classe final 1-5 (ver regras-classificacao.md) |
| `classe_desc` | Descricao da classe |
| `score_confianca` | Score de confianca 0-100 (evidencias cadastrais + externas) |
| `evidencias` | Lista JSON de evidencias cadastrais usadas no score |
| `competencia_cnpj` | Competencia da base CNPJ (AAAA-MM) |
| `fontes` | Fontes usadas na ficha |
| `coletado_em` | Data/hora da coleta cadastral (UTC) |

## Arquivos de trabalho (`$RADAR_PV_DATA/work`)

| Arquivo | Conteúdo |
|---|---|
| `candidatos.parquet` | Saída da descoberta (todas as classes, com `classe_preliminar` e `score_cadastral`) |
| `dirigentes.parquet` | QSA das candidatas: nome, qualificação, data de entrada, fonte |
| `enriquecimento.parquet` | Resultado da leitura dos sites oficiais |
| `susep.parquet` | Situações SUSEP importadas, com evidência e data |
| `base_final.parquet` | Ficha consolidada (fonte das exportações e de `consultar.py --sql`) |
