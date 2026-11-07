# Fontes, acesso e limites (verificado em 2026-11-07)

| Fonte | Uso na Skill | Acesso automatizado | Observações |
|---|---|---|---|
| **Receita Federal: CNPJ dados abertos** `arquivos.receitafederal.gov.br` (compartilhamento Nextcloud público, WebDAV `public.php/webdav/Dados/Cadastros/CNPJ/AAAA-MM/`) | Empresas, estabelecimentos, QSA, Simples, tabelas de CNAE, município, natureza e qualificação | Sim (`baixar_cnpj.py --fonte rfb`), CSV zipado ~7 GB, convertido para Parquet | Fonte primária. Competência mais recente em 07/11/2026: **2026-10**. Velocidade medida ~0,9 MB/s (≈2 h) |
| **Espelho Parquet CNPJ Aberto** `huggingface.co/datasets/cnpjaberto/cnpj-dados-receita-brasil-AAAA-MM` | Mesma base, já em Parquet (5,0 GB, 223,6 milhões de linhas) | Sim (`--fonte hf`, padrão), ~25 MB/s, conferência de bytes pelo `_manifest.json` | Terceiro. Declara origem na Receita e licença "dados abertos do governo federal". Competência 2026-10 = oficial. O script avisa se a Receita publicar competência mais nova |
| **SUSEP: página de PPM** `gov.br/susep/.../associacoes-de-protecao-patrimonial-mutualista` | Regras, fases e prazos | Leitura simples | Fase I encerrada em 15/07/2025; Res. CNSP 491/2026 conclui a Fase II; Fase III até 07/05/2028 |
| **SUSEP: emissão de certidão** `www2.susep.gov.br/safe/certidoes/app/certidao/emitir` | Situação do cadastro por CNPJ | **Não**: protegida por reCAPTCHA | Conferência manual via `validar_susep.py fila` + `importar` |
| **SUSEP: consultar associações** `www2.susep.gov.br/safe/autorizacoes/app/` | Situação do cadastro | **Não**: aplicação web sem API pública documentada | Não usar engenharia reversa de endpoints internos |
| **SUSEP: lista nominal** | Gabarito de cobertura | Não publicada em dados abertos | Caminho oficial: pedido via LAI (Fala.BR) e importar com `--lista-oficial` |
| **Sites institucionais** | Contatos, sinais operacionais, vínculo com o CNPJ | Sim, com robots.txt, 1 req/s, máx. 4 páginas, sem login/formulário | Site descoberto só pelo domínio do e-mail cadastral próprio ou CSV informado pelo usuário |
| Buscadores (DuckDuckGo, Google) | Descoberta de sites | **Não usados**: retornam desafio anti-robô | Pesquisa de sites fica manual (CSV `--sites`) |
| APIs de terceiros (BrasilAPI, minhareceita.org, CNPJá, OpenCNPJ) | Consulta pontual de CNPJ | Possível, mas **desligado** | Enviaria a lista de CNPJs pesquisados a terceiros; a base local já contém os mesmos dados |

## Modelo de solicitação via LAI (Fala.BR) para a SUSEP

> Com fundamento na Lei 12.527/2011, solicito a relação das associações de proteção patrimonial mutualista
> que concluíram o cadastramento previsto na Lei Complementar 213/2025 (Resolução Susep 49/2025), contendo
> CNPJ, razão social, UF e situação cadastral atual ("em regularização" ou outra), em formato aberto (CSV/XLSX),
> com a data de referência da extração.

Importe a resposta com `python scripts/validar_susep.py importar --lista-oficial arquivo.csv` (colunas `cnpj`, `situacao`).
