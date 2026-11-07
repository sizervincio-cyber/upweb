# radar-protecao-veicular

Skill do Claude Code para mapear associações de proteção veicular e patrimonial mutualista no Brasil
com dados oficiais, evidências rastreáveis e foco em prospecção B2B (gestão digital de sinistros).

## O que faz

1. Baixa a base aberta do CNPJ (Receita Federal) em Parquet, com retomada e verificação de tamanho.
2. Descobre candidatas por razão social, nome fantasia, CNAE principal **e** secundário, natureza jurídica e e-mail
   (o CNAE 9499-5/00 é ponto de partida, não filtro).
3. Classifica cada entidade em 5 classes com score 0-100 e lista de evidências.
4. Traz dirigentes públicos do QSA (nome, cargo, data de entrada; sem CPF).
5. Valida contatos no site oficial (robots.txt respeitado): contato só é "confirmado" se o site cita o CNPJ.
6. Gera fila de conferência SUSEP e importa o resultado (a consulta oficial usa reCAPTCHA, que não é contornado).
7. Exporta CSV, XLSX (aba por UF + dicionário) e JSON, mais relatório nacional de cobertura.

## Instalação (Windows, macOS ou Linux)

```powershell
# Python 3.10+ ; a partir da raiz do repositório
cd .claude\skills\radar-protecao-veicular
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
# opcional: onde guardar os dados (padrão C:\Users\<voce>\.radar_pv)
setx RADAR_PV_DATA "D:\radar_pv"
```

Requisitos de máquina: ~6 GB de disco para a base, 4 GB de RAM (use `--memoria 2GB` em máquinas menores).

## Uso rápido

```bash
python scripts/baixar_cnpj.py                       # ~5 GB, uma vez por mês
python scripts/filtrar_associacoes.py               # Brasil inteiro em ~30 s
python scripts/enriquecer_contatos.py --uf GO MT TO # sites oficiais
python scripts/normalizar_dados.py
python scripts/exportar_resultados.py --uf GO MT TO --nome piloto
python scripts/validar_susep.py fila --uf GO MT TO
python -m unittest discover -s tests -v
```

No Claude Code, basta pedir em linguagem natural ("encontre associações de proteção veicular em Goiânia com
contato confirmado"): a Skill é carregada pelo `SKILL.md`.

## Privacidade e segurança

- Somente leitura em todas as fontes; nenhum dado é enviado a APIs de terceiros.
- Sem CPF (nem mascarado), sem faixa etária, sem endereço residencial, sem telefone pessoal.
- Logs e cache ficam em `$RADAR_PV_DATA`. Não versione a pasta de dados.
- Base legal de uso: dados públicos do CNPJ (Lei 12.527/2011) e LGPD art. 7º, §3º e §4º (dados tornados públicos),
  com finalidade B2B, minimização e direito de oposição: remova a entidade/contato quando solicitado.

Documentação completa em `references/`.
