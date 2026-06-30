# Assets a gerar no ChatGPT — UpWeb Gestão de Sinistros

Guia para gerar as imagens que faltam, salvar em `assets/` e me avisar para eu conectar no site.

## Como usar (leia antes)
1. No ChatGPT, peça a imagem **na proporção indicada** (ele aceita 1024×1024, 1024×1536 retrato e 1536×1024 paisagem).
2. Baixe e **salve em `assets/` com exatamente o nome do arquivo** indicado (sem acento, sem espaço).
3. Se a proporção do ChatGPT não bater com a final, **recorte** para a dimensão alvo (qualquer editor, ou me peça que eu recorto).
4. Paleta da marca para colar em qualquer prompt: **roxo `#6F06E4`, roxo escuro `#2A073F`, roxo médio `#7B2CBF`, lavanda `#EDE3FF`**, fundos claros off-white.
5. Regras gerais para todos: **sem texto, sem letras, sem logos, sem marca d'água**; estilo SaaS B2B premium, iluminação suave, nada de "stock photo" datado.

> ⚠️ Os retratos (Autoridade e Depoimento) são **pessoas geradas por IA**. Use como mockup de demonstração. Antes de publicar ao vivo, troque por foto real autorizada — exibir pessoa fictícia como cliente real pode ser enganoso.

---

## 1. Retrato — Seção "Autoridade humana"
- **Arquivo:** `assets/autoridade.jpg`
- **Proporção a pedir:** retrato 1024×1536 → **alvo final 4:5 (ex.: 720×900)**
- **Onde entra:** bloco escuro "Tecnologia criada por quem entende a realidade da operação".

**Prompt:**
```
Retrato corporativo realista de um profissional brasileiro (40-50 anos), executivo de tecnologia, vestindo camisa social na cor sóbria, expressão confiante e acessível, levemente sorrindo. Iluminação de estúdio suave e moderna. Fundo neutro off-white com um leve brilho lavanda (#EDE3FF) e bokeh muito sutil, sem distrair. Enquadramento da cintura para cima, leve profundidade de campo. Estética premium de SaaS B2B, cores frias e limpas alinhadas a roxo #6F06E4. Foto nítida, alta qualidade, sem texto, sem logos. Proporção retrato 4:5.
```

---

## 2. Avatar — Depoimento "Ricardo Menezes"
- **Arquivo:** `assets/depoimento-1.jpg`
- **Proporção a pedir:** **1024×1024 (1:1)**
- **Onde entra:** card de depoimento da seção Prova social (substitui as iniciais "RM").

**Prompt:**
```
Headshot corporativo realista de um homem brasileiro (45-55 anos), aparência de presidente de associação, cabelo grisalho, camisa social azul-marinho, sorriso discreto e confiável, olhando para a câmera. Iluminação natural suave. Fundo desfocado claro com tom lavanda muito sutil. Foto profissional de perfil de LinkedIn, enquadramento close no rosto e ombros, centralizado. Estética premium e corporativa. Sem texto, sem logos. Proporção quadrada 1:1.
```

---

## 3. Imagem de compartilhamento (Open Graph)
- **Arquivo:** `assets/og-cover.jpg`
- **Proporção a pedir:** paisagem 1536×1024 → **alvo final 1200×630 (1.91:1)**
- **Onde entra:** `<meta property="og:image">` — é a imagem que aparece quando o link é compartilhado no WhatsApp/LinkedIn.

**Prompt:**
```
Capa horizontal premium para SaaS B2B de gestão de sinistros veiculares. Composição limpa e tecnológica: à direita, um notebook moderno mostrando um painel/dashboard abstrato com cards e gráficos (sem texto legível); à esquerda, espaço livre off-white para inserir título depois. Fundo branco/lavanda (#EDE3FF) com um padrão sutil de pontos conectados (rede) em roxo, opacidade baixa. Gradiente de marca roxo (#2A073F → #6F06E4 → #7B2CBF) em um detalhe de canto. Iluminação suave, sombras leves, estética enterprise. Sem texto, sem letras, sem logos. Proporção 1.91:1 (paisagem).
```

---

## 4. (Opcional) Ilustração — Seção "Regulação e Governança"
- **Arquivo:** `assets/governanca.png`
- **Proporção a pedir:** **1024×1024 (1:1)**
- **Onde entra:** lado direito da seção Governança (hoje há uma ilustração em CSS; esta substituiria por algo mais rico). **Opcional** — o CSS atual já funciona.

**Prompt:**
```
Ilustração isométrica 3D limpa e minimalista representando segurança e governança documental: um escudo central com um cheque/aprovação, cercado por documentos organizados, um cadeado e um relógio de prazo. Paleta exclusivamente em tons de roxo e lavanda (#6F06E4, #7B2CBF, #2A073F, #EDE3FF) sobre fundo transparente ou branco. Estilo flat 3D moderno de SaaS, traços suaves, sombras leves, sem texto, sem números, sem logos. Composição centralizada, proporção quadrada 1:1.
```

---

## Resumo (checklist de geração)

| # | Arquivo | Proporção pedir | Alvo final | Prioridade |
|---|---|---|---|---|
| 1 | `assets/autoridade.jpg` | 1024×1536 | 720×900 (4:5) | Alta |
| 2 | `assets/depoimento-1.jpg` | 1024×1024 | 480×480 (1:1) | Média |
| 3 | `assets/og-cover.jpg` | 1536×1024 | 1200×630 | Alta |
| 4 | `assets/governanca.png` | 1024×1024 | 640×640 (1:1) | Opcional |

Depois de salvar os arquivos em `assets/` com esses nomes, **me avise** que eu:
- conecto o retrato e o avatar no HTML/CSS,
- atualizo a tag `og:image`,
- otimizo o peso (cada imagem para < 200 KB) e ajusto o enquadramento se precisar.
