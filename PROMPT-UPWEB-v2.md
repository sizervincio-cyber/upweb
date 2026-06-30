# PROMPT MESTRE — UpWeb Gestão de Sinistros (Landing v2)

> Versão sênior do briefing. Cole este arquivo inteiro como prompt único.
> As seções 0, A e B são **regras de engenharia** que vêm antes da estética —
> elas evitam imagens quebradas, LCP de 6 MB e saída truncada.

---

## 0. PAPEL E REGRA DE ENTREGA (ler primeiro)

Atue simultaneamente como **Diretor de Arte Sênior, UX/UI de SaaS B2B, Front-end Sênior, Copywriter B2B e Motion Designer**. Você está reescrevendo uma landing **já existente** (não é greenfield): existe `index.html`, `styles.css` e `main.js`. A base visual é boa, mas o hero atual é um **vídeo escuro de tela cheia com texto por cima** — isso deve ser **removido** e substituído pelo hero claro de duas colunas descrito na seção 7.

**Definição de pronto (Definition of Done).** Só considere a tarefa concluída quando TODOS os itens abaixo forem verdadeiros:

- [ ] `index.html`, `styles.css`, `main.js` reescritos por completo e **autossuficientes** (sem dependências externas além das fontes Google).
- [ ] **Zero `<img>`/`<video>` apontando para arquivo inexistente.** Conferir contra a seção A antes de escrever qualquer `src`.
- [ ] Nenhum erro no console; nenhum recurso 404.
- [ ] `prefers-reduced-motion` desliga todas as animações.
- [ ] Navegável 100% por teclado; foco visível; contraste AA (seção B).
- [ ] Mobile (375px), tablet (768px) e desktop (1280px) sem overflow horizontal.
- [ ] Entregue os **três arquivos completos**, na ordem `index.html` → `styles.css` → `main.js`, sem omitir trechos com "...". Se faltar espaço, pare em um limite de arquivo e sinalize para continuar — **nunca** entregue arquivo parcial.

---

## A. AUDITORIA DE ASSETS — FONTE DE VERDADE (não invente caminhos)

Use **exatamente** este inventário. Não há outros arquivos em `/assets`.

### ✅ EXISTEM — pode referenciar à vontade
| Arquivo | Peso | Observação de uso |
|---|---|---|
| `assets/logo-roxo.svg` | ~140 KB | logo header (raster embutido — não escalar além de ~160px) |
| `assets/logo-branca.svg` | ~140 KB | logo footer |
| `assets/dashboard.png` | 560 KB | card "Kanban de Sinistros" |
| `assets/timeline.png` | 370 KB | card "Linha do Tempo" |
| `assets/vistoria-online.png` | 537 KB | módulo "Vistoria 100% Online" |
| `assets/envio-juridico.png` | 344 KB | módulo "Envio Jurídico" |
| `assets/gestao-upweb.png` | **6,4 MB** | **NÃO usar sem otimizar** (ver seção C) |
| `assets/beneficios.png` | **6,5 MB** | infográfico vertical pesado — **evitar acima da dobra** |
| `assets/hero-upweb-bg.mp4` | **543 KB** | ⭐ **BACKGROUND DO HERO** — animação do produto UpWeb (Kanban real + painel de claim) sobre fundo lavanda claro com pattern de rede. Já otimizado (1440px, sem áudio, faststart). |
| `assets/hero-poster.jpg` | 60 KB | poster do vídeo do hero (frame do produto). Usar no atributo `poster` e como fallback. |

> **Não referenciar:** `Hyperrealism Video Editing.mp4` (10,7 MB — é o master original do hero, fica no repo só como fonte) e `hero-upweb-scroll.mp4` (3,3 MB — clipe antigo genérico de "auto tracking", **descontinuado**).

### ❌ NÃO EXISTEM — proibido referenciar como `src`
- `assets/ficha-sinistro.png` → para o card "Ficha do Sinistro", **usar `assets/dashboard.png` ou um mockup CSS** (ver seção D).
- `assets/section-pattern-light.svg` → recriar o pattern com **CSS/SVG inline** (gradiente + `radial-gradient` de pontos).
- `assets/cta-final-bg.webp` → usar **`--grad-brand` em CSS** no CTA final.
- `assets/footer-pattern.svg` → pattern do footer **em CSS inline**, opacidade baixa.

> Regra dura: se o arquivo não está na lista ✅, ele **não vira `src`**. Vira fallback CSS.

---

## B. ACESSIBILIDADE — CRITÉRIOS MENSURÁVEIS (não "acessibilidade básica")

- Contraste **AA mínimo (4,5:1 texto normal)**. Cuidados específicos desta paleta:
  - **Nunca** texto `--brand-100 (#EDE3FF)` sobre branco (falha grave). Lavanda só sobre fundo roxo escuro.
  - Texto secundário usar `--ink-600 (#4A4458)` sobre branco (passa AA), não `--ink-400`.
  - Em chips lavanda, o texto é `--brand-900`, não roxo médio.
- HTML semântico: um único `<h1>`; hierarquia `h2/h3` sem pular níveis; `<main>`, `<nav>`, `<section aria-labelledby>`, `<footer>`.
- Hambúrguer com `aria-expanded` + `aria-controls`; drawer fecha com `Esc` e devolve foco ao botão.
- Acordeão FAQ acessível por teclado (usar `<details>/<summary>`).
- `<video>` com `aria-label`; imagens informativas com `alt` descritivo; decorativas com `alt=""` ou `aria-hidden`.
- `:focus-visible` com outline de 2px `--brand-700`, nunca `outline:none` sem substituto.
- `skip-link` para `#conteudo`.

---

## C. PERFORMANCE — ORÇAMENTO EXPLÍCITO (a parte que o briefing original esquecia)

Meta: **LCP < 2,5 s** em conexão simulada, **CLS < 0,1**, sem long task acima de 200 ms.

Regras:
1. **Acima da dobra não pode pesar megabytes.** Usar `hero-upweb-bg.mp4` (543 KB, já otimizado) + `hero-poster.jpg` (60 KB). **Nunca** usar `gestao-upweb.png` (6,4 MB) ou `beneficios.png` (6,5 MB) acima da dobra.
2. Vídeo do hero: `preload="metadata"`, `muted`, `playsinline`, `loop`, `autoplay`, `poster="assets/hero-poster.jpg"`, `aria-hidden="true"`. Em `prefers-reduced-motion`, não dar autoplay — mostrar só o poster.
3. Toda imagem abaixo da dobra: `loading="lazy"` + `decoding="async"` + `width`/`height` explícitos (evita CLS).
4. Imagens decorativas e patterns: **CSS, não arquivo**.
5. Fontes: `&display=swap`, `preconnect` para `fonts.gstatic.com`, e **apenas os pesos usados** (Poppins 600/700/800; Inter 400/500/600/700).
6. Nada de framework, jQuery, bibliotecas de animação. JS vanilla, `defer`.
7. Comente no topo do HTML, uma linha: `<!-- TODO produção: converter gestao-upweb.png e beneficios.png para WebP < 300KB -->`.

---

## D. MOCKUPS DE PRODUTO QUANDO NÃO HÁ SCREENSHOT (sênior anti-"imagem quebrada")

Onde o briefing pede uma tela que **não existe** como arquivo (ex.: "Ficha do Sinistro", "KPIs de leitura financeira", mockup de celular da vistoria), **construa o mockup em HTML/CSS**, não use placeholder cinza nem `src` inventado:
- Janela de browser/app fake (barra com 3 dots, header com abas), conteúdo com retângulos/skeletons em tons de `--surface-1`/`--brand-100`.
- KPIs da seção financeira são **cards de dados reais em HTML** (número em Poppins 700 + label), não uma imagem.
- Mockup de celular = `<div>` com `border-radius` grande, notch, e a imagem `vistoria-online.png` dentro.

Mockup em código fica nítido em qualquer densidade de tela e não tem custo de download.

---

## E. ANTI-AI-SLOP / DIREÇÃO DE ARTE (o que separa "premium" de "template")

- **Roxo é assinatura, não preenchimento.** Fundo dominante branco/`--surface-2`. Roxo aparece em: 1 CTA por dobra, eyebrows, ícones, 1 bloco de virada, detalhes. Se mais de ~20% da tela está roxa, está errado.
- **Um só elemento dramático por seção.** Nada de gradiente + sombra forte + borda colorida + glow no mesmo card.
- Tipografia: hierarquia por **peso e tamanho**, não por cor. Limite de medida de leitura ~65ch.
- Sombras suaves e de marca (`rgba(42,7,63,...)`), nunca preto puro.
- Espaçamento por escala de 8px. Ritmo vertical consistente entre seções (`--section-y`).
- Ícones: line-icons SVG inline, 1,5px de traço, consistentes. **Sem emoji grande, sem ícone infantil.**
- Microinterações curtas (150–250 ms), `ease-out`. Reveal sutil (≤24px, ≤500 ms). Nada que "salte".
- Proibido: glassmorphism pesado, hero escuro, texto sobre área poluída, cards gigantes, marquee de logos espalhafatoso, "blur translúcido" no header.

---

# PARTE 2 — BRIEFING DE CONTEÚDO E LAYOUT

> A estrutura abaixo é a mesma do seu briefing, já com correções sênior aplicadas.
> Onde há ⚠️, é um ajuste em relação ao texto original.

## 1. Tese e tom
Tese: **"Controle o sinistro do primeiro registro ao desfecho final — com processo, evidência, rastreabilidade e leitura financeira."**
Vender: controle operacional, gestão digital, rastreabilidade, organização documental, vistoria online, linha do tempo, envio jurídico, pagamentos, relatórios, leitura financeira, redução de retrabalho, governança para APVs.
Tom: B2B, premium, objetivo, tecnológico, confiável. Sem hype de startup.

## 2. Stack
HTML5 semântico + CSS3 + JS vanilla. Sem Tailwind/Bootstrap/frameworks. Arquivos: `index.html`, `styles.css`, `main.js`. Fontes: Poppins (títulos), Inter (corpo/UI).

## 3. Tokens CSS (`:root`)
```css
:root{
  --brand-700:#6F06E4; --brand-900:#2A073F; --brand-500:#7B2CBF; --brand-100:#EDE3FF;
  --surface-0:#FFFFFF; --surface-1:#F7F5FA; --surface-2:#FAF8FF;
  --ink-900:#1E1E1E; --ink-700:#2E2938; --ink-600:#4A4458; --ink-400:#7B748A;
  --success:#18A957; --alert:#D93025; --warning:#F5A524;
  --grad-brand:linear-gradient(135deg,#2A073F 0%,#6F06E4 65%,#7B2CBF 100%);
  --shadow-soft:0 16px 40px rgba(42,7,63,.08);
  --shadow-card:0 18px 48px rgba(42,7,63,.10);
  --shadow-hero:0 28px 80px rgba(42,7,63,.18);
  --radius-sm:12px; --radius-md:16px; --radius-lg:20px; --radius-xl:28px;
  --container:1280px;
}
```

## 4. Estrutura da página (ordem)
1. Header sólido tecnológico · 2. Hero claro 2 colunas · 3. Faixa de associações · 4. Segunda dobra Produto+Fluxo · 5. Leitura financeira · 6. Regulação e governança · 7. Método UpWeb · 8. Autoridade humana · 9. Prova social · 10. Comparativo · 11. Formulário · 12. FAQ · 13. CTA final · 14. Footer · 15. WhatsApp float · 16. Mobile CTA bar.
⚠️ Remover a antiga seção "Diagnóstico / como a maioria gerencia hoje" e o grid de 6 cards de caos.

## 6. Header
Sólido, **sem glassmorphism, sem blur**. Altura 80px, `sticky top:0`, `z-index:100`, fundo `#FFFFFF`, `border-bottom:1px solid rgba(111,6,228,.10)`, `box-shadow:0 8px 28px rgba(42,7,63,.08)`. Linha superior de 3px `linear-gradient(90deg,#2A073F,#6F06E4,#9B5CFF)`. Logo `logo-roxo.svg` (~152px). Menu: Produto · Método · Comparativo · FAQ (links `#1E1E1E`, 600, hover `#6F06E4` com underline animado fino). CTA "Agendar demonstração" roxo, `radius 14px`, hover `translateY(-2px)` + sombra roxa. Mobile: hambúrguer → drawer branco.

## 7. Hero (NOVA primeira dobra) ⚠️ vídeo de produto como BACKGROUND claro
`min-height:calc(100vh - 80px)`, container 1280px, `padding:80px 32px 48px`. **Layout: o vídeo do produto é o fundo do hero; o texto fica numa coluna à esquerda.** Isso é o oposto do hero escuro atual: o vídeo `hero-upweb-bg.mp4` é **claro (lavanda)**, tem a área vazia à esquerda e o produto (Kanban/claim) entrando pela direita — então o texto à esquerda assenta naturalmente sobre o espaço limpo do vídeo.

**Vídeo de fundo:**
```html
<video class="hero-bg" autoplay muted loop playsinline preload="metadata"
       poster="assets/hero-poster.jpg" aria-hidden="true">
  <source src="assets/hero-upweb-bg.mp4" type="video/mp4">
</video>
```
- `object-fit:cover`, cobrindo o hero; em telas largas, ancorar `object-position` à direita para preservar o produto e liberar a esquerda para o texto.
- **Scrim de legibilidade CLARO** (não escuro): gradiente `linear-gradient(90deg, rgba(255,255,255,.92) 0%, rgba(255,255,255,.70) 38%, rgba(255,255,255,0) 70%)` por cima do vídeo, só do lado do texto. Mantém o ar "clean" e garante contraste AA do texto escuro.
- Glow/`radial-gradient` lavanda apenas como reforço, sem escurecer.

**Coluna esquerda (texto, sobre o scrim claro — cor de texto escura `--ink-900`/`--ink-600`):**
- Eyebrow: "GESTÃO DE SINISTROS PARA ASSOCIAÇÕES DE PROTEÇÃO VEICULAR"
- H1: "Controle inteligente e digital dos **sinistros da sua APV**." (destaque em roxo/gradiente)
- Sub: "Do primeiro registro ao desfecho final."
- Linha de apoio: "Mais controle, menos retrabalho e decisões seguras."
- Parágrafo: "Centralize documentos, vistorias, prazos, aprovações, pagamentos e histórico em uma operação rastreável, organizada e segura."
- CTAs: "Agendar demonstração" (primário) · "Ver como funciona →" (secundário)
- Provas rápidas (✓ ícone SVG, não emoji): Rastreabilidade total · Organização documental · Leitura financeira em tempo real
- "Integrações nativas:" chips WhatsApp · E-mail · Assinatura Digital (ícones genéricos)

⚠️ **Fallback:** se o `<video>` falhar (`error`), exibir `hero-poster.jpg` como `background-image` do hero (não a PNG de 6 MB).
⚠️ **Mobile:** o vídeo tem o produto à direita; em 1 coluna, ou (a) aumentar o scrim claro para quase opaco e manter o texto legível por cima, ou (b) empilhar — texto em cima sobre fundo `--surface-2`, vídeo num bloco com `border-radius` logo abaixo. Escolher a opção que preserve legibilidade AA.
Animação: texto reveal por linha, CTAs scale leve. Respeitar `prefers-reduced-motion` (e nesse caso pausar/ocultar o vídeo, mostrando o poster).

## 8. Faixa de associações
Texto "Associações que confiam na UpWeb". Fundo `rgba(237,227,255,.72)`, borda `rgba(111,6,228,.12)`. Marquee infinito 28–34s, **pausa no hover**, grupo duplicado para loop. Logos = **chips de texto em CSS** (Protege+, Clube FORTE, União Proteção, PROTEG, Rota Proteção, Mais Veicular, ProtegeMax, VeicularSeguro, AssociaPlus) em cinza/`grayscale(1)`/`opacity .55`; hover colore e `scale(1.08)`. ⚠️ marquee deve respeitar `prefers-reduced-motion` (parar a animação).

## 9. Segunda dobra — Produto + Fluxo (`id="sistema-upweb"`)
Título: "Do registro ao desfecho: tudo em um fluxo único." Sub: "Controle abertura, triagem, documentos, vistoria, análise, jurídico, pagamentos e relatórios em uma operação digital, rastreável e organizada."
⚠️ **Realismo sobre o "16:9 cabe em uma tela":** mire numa composição compacta e editorial, mas **não comprima a ponto de quebrar legibilidade/contraste/altura mínima de toque**. Em telas baixas, deixe respirar — legibilidade vence o "caber em 100vh". `padding:32px 0 40px`, bordas `rgba(111,6,228,.10)` topo/baixo, container 1280px.
Cinco blocos:
- **9.1 Virada roxa:** faixa `--grad-brand`, `radius 20px`, `padding 24px 32px`, ícone escudo/check line branco. Texto: "Sinistro é onde a promessa da associação encontra a realidade da operação." + apoio: "Processo, organização e dados transformam esforço em resultado e confiança em reputação."
- **9.2 Três cards:** (01) Kanban de Sinistros → `dashboard.png`; (02) Ficha do Sinistro → ⚠️ `ficha-sinistro.png` **não existe** → usar `dashboard.png` ou mockup CSS; (03) Linha do Tempo → `timeline.png`. Cards brancos, borda lavanda, `radius 18px`, hover `translateY(-4px)`.
- **9.3 Fluxo do sinistro:** linha pontilhada lavanda + 7 nós (Abertura → Triagem → Documentos/Evidências → Vistoria Online → Análise/Decisão → Jurídico/Pagamentos → Finalização/Relatórios). Ícones circulares roxos line; 1 etapa ativa sólida. Vira **timeline vertical no mobile**.
- **9.4 Módulos:** (1) "Vistoria 100% Online" + mockup de celular com `vistoria-online.png`; (2) "Envio Jurídico e Pagamentos" + mini-fluxo 4 ícones (Envio → Análise → Aprovação → Pagamento) usando `envio-juridico.png`.
- **9.5 Faixa de benefícios:** "Todos os benefícios que sua associação precisa em um só lugar." Lista: controle/visibilidade · redução de retrabalho · decisões seguras · economia de tempo/custos · conformidade e segurança jurídica.

## 10. Leitura financeira
Eyebrow "Leitura financeira" · Título "Leitura financeira em tempo real" · Sub sobre custos/prazos/SLA.
⚠️ KPIs são **cards de dados em HTML** (não imagem): Valor Previsto R$ 1.248.750,00 · Aprovado R$ 875.420,00 · Pago R$ 642.300,00 · Custo Médio R$ 2.145,33 · Prazo Médio 7,6 dias · Pendências 23 · SLA 92%. Overflow-x no mobile. Nota: "Filtros por período, categoria, oficina, responsável e status." CTA ghost "Ver relatório completo →".

## 11. Regulação e governança
Split: texto esquerda / ilustração CSS (escudo+documento+lock) direita. Título "Apoio à organização operacional e documental para uma gestão mais segura." + parágrafo + **nota de isenção**: "O sistema não substitui obrigações legais, contábeis ou regulatórias perante órgãos competentes."

## 12. Método UpWeb (5 etapas)
Mapear · Organizar · Implantar · Acompanhar · Evoluir (com as descrições do briefing). Horizontal no desktop, timeline vertical no mobile, conectores lavanda, ícones roxos.

## 13. Autoridade humana
Fundo `--brand-900`/gradiente escuro. Split: placeholder de foto (CSS) à esquerda, texto+stats à direita. Título "Tecnologia criada por quem entende a realidade da operação." Stats com **counter animation** ao entrar na viewport: +10 anos · +45 associações · +1M sinistros. ⚠️ aqui (fundo escuro) lavanda sobre roxo é OK.

## 14. Prova social
3 colunas: (1) mockup do sistema + "Mais de 1.000.000 de sinistros gerenciados."; (2) card de depoimento (aspas roxas, avatar placeholder CSS, "Presidente", estrelas SVG); (3) grid de logos-chip. ⚠️ marcar depoimento como exemplo até validação real (evitar afirmação falsa de cliente).

## 15. Comparativo
3 colunas: "WhatsApp / Planilhas" (itens negativos, ícone ✗) · "UpWeb Sinistros" (itens positivos, ícone ✓) · coluna benefício + CTA "Agendar demonstração →".

## 16. Formulário
Título "Agende uma demonstração personalizada" + texto + badges (consultivo/sem compromisso · resposta em 24h). Campos: Nome, E-mail, WhatsApp, Associação, Sinistros/mês (Menos de 50 / 50–200 / 200–500 / +500). Botão "Agendar demonstração". ⚠️ Sem backend: validar no front e montar **link `wa.me` com os dados** ou `mailto:` como fallback; mensagem de sucesso `aria-live="polite"`. Máscara simples de WhatsApp.

## 17. FAQ
5 itens (substitui WhatsApp? · difícil implantar? · dados seguros? · qualquer tamanho? · atende SUSEP? — com as respostas do briefing). `<details>/<summary>`, **apenas um aberto por vez**, borda roxa quando aberto. ⚠️ Manter `FAQPage` JSON-LD sincronizado com as 5 perguntas reais.

## 18. CTA final
⚠️ Fundo `--grad-brand` em CSS (não `cta-final-bg.webp`, que não existe). Título "Transforme a gestão de sinistros da sua associação hoje." + texto. Botões "Falar com especialista" e "Agendar demonstração". Texto esquerda / botões direita, empilha no mobile.

## 19. Footer
Fundo `--brand-900`, pattern CSS (não `footer-pattern.svg`). `logo-branca.svg` + tagline. Colunas Soluções / Empresa / Suporte / Contato (`comercial@upweb.com.br`). Rodapé: Política de Privacidade · Termos de Uso · © UpWeb.

## 20. Fixos
WhatsApp float (56px, `#25D366`, ícone SVG branco, aparece após `scrollY>400`, pulse leve). Mobile CTA bar (oculta no desktop; mobile fixa no rodapé, fundo branco, borda lavanda, botão full-width "Agendar demonstração").

## 21. JavaScript (`main.js`, vanilla, `defer`)
1. Header `.is-scrolled` em `scrollY>24`. 2. Drawer mobile (toggle, fecha ao clicar link e com `Esc`, gerencia `aria-expanded`). 3. Reveal via `IntersectionObserver` (`.reveal`). 4. Marquee pausa no hover **e** respeita reduced-motion. 5. Fallback de vídeo: se `error` no `<video>` do hero, aplicar `hero-poster.jpg` como `background-image` do hero (nunca a PNG de 6 MB). 6. WhatsApp float após `scrollY>400`. 7. Mobile bar após `scrollY>100` em telas pequenas. 8. Validação de form + sucesso. 9. FAQ um-aberto-por-vez. 10. Counter animation (Autoridade). 11. Em todo `[data-whatsapp]`: `https://wa.me/55SEUNUMERO?text=Olá,%20quero%20agendar%20uma%20demonstração%20da%20UpWeb%20Gestão%20de%20Sinistros.` ⚠️ Deixar `SEUNUMERO` como constante única no topo do JS para troca fácil. 12. Guard de reduced-motion no topo, aplicado a todas as animações JS.

## 22. Responsividade
Desktop: hero 2 colunas, cards 3 colunas, fluxo horizontal. Tablet (768): cards 2 colunas, fluxo em 2 linhas. Mobile (375): hero 1 coluna (mídia abaixo do texto), H1 38–44px, CTAs empilhados, fluxo vertical, módulos empilhados, KPIs/benefícios em scroll-x. Testar os 3 breakpoints sem overflow horizontal.

## 23. Resultado esperado
SaaS enterprise premium, limpo, claro, tecnológico, com presença de produto, roxo como assinatura. **Evitar:** glassmorphism pesado, hero escuro, texto sobre área poluída, ícone infantil, emoji grande, card gigante, infográfico antigo, layout genérico, animação exagerada, poluição visual.

---

## ORDEM DE EXECUÇÃO SUGERIDA (para não truncar)
1. `index.html` completo (semântica + todos os `src` conferidos contra a seção A).
2. `styles.css` completo (tokens → base → header → hero → seções → componentes fixos → responsivo → reduced-motion).
3. `main.js` completo (módulos da seção 21).
Entregar os três na íntegra. Se atingir limite, parar em fronteira de arquivo e sinalizar "continua".
