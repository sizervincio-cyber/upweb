# PROMPT MESTRE — Revisão e Elevação "Awwwards-level" da Landing Page UpWeb

## CONTEXTO DO PROJETO
- Projeto: landing page estática (HTML/CSS/JS puro) em PT-BR para o **UpWeb — Gestão de Sinistros**, um SaaS B2B para associações de proteção veicular (APVs).
- Arquivos: `index.html`, `styles.css`, `main.js`, `assets/` (imagens + vídeos).
- Público: gestores de APV — decisão racional (controle, rastreabilidade, segurança jurídica) com gatilho emocional de confiança.
- Restrições técnicas reais já observadas:
  - Assets MUITO pesados (PNGs de ~6 MB, vídeo de 10 MB) — há um `TODO produção: converter para WebP < 300KB` no HTML.
  - Animações infinitas e lazy-load mal calibrados deixam a página perceptivelmente lenta.
- Servir/validar localmente: `python -m http.server` (config em `.claude/launch.json`, skill `/run`).

## SEU PAPEL
Aja como um **Creative Director + Front-end Lead premiado em Awwwards (Site of the Day)**. Eu quero uma revisão crítica e a APLICAÇÃO de melhorias profundas — não apenas sugestões. Trabalhe em fases, peça aprovação ao fim de cada fase antes de tocar no código em larga escala, e prove cada melhoria rodando a página.

## CRITÉRIOS DE JULGAMENTO (a barra)
Avalie e melhore tudo contra a rubrica Awwwards:
1. **Design (40%)** — tipografia, hierarquia, espaçamento, cor, composição, consistência de sistema.
2. **Usabilidade / UX (30%)** — clareza de navegação, fluxo de conversão, acessibilidade, responsividade, performance percebida.
3. **Criatividade (20%)** — direção de arte distintiva, micro-interações, momentos memoráveis (sem "AI slop").
4. **Conteúdo (10%)** — copy persuasiva, storytelling, prova social, voz de marca.
Meta: cada seção deveria ser "screenshot-able" e defensável diante de um júri.

---

## FASE 0 — DIAGNÓSTICO (não escreva código ainda)
Use **`/run`** para subir a página, e leia `index.html`, `styles.css`, `main.js`.
Use **`design-review`** e **`taste-skill`** (modo audit-first) para um diagnóstico honesto:
- O que faz a página parecer "template/AI-generated" hoje?
- Pontos fracos por critério Awwwards (cite seção + arquivo:linha).
Use **`web-design-guidelines`** (Vercel) e **`design:accessibility-review`** como checklist objetivo (contraste, foco, ARIA, hierarquia de headings).
**Entregue:** um relatório priorizado (Impacto × Esforço) com nota atual estimada por critério.

## FASE 1 — DIREÇÃO DE ARTE E SISTEMA DE DESIGN
Use **`color-expert`** para refinar a paleta (o roxo da marca #6F06E4) em escala acessível (OKLCH, contraste AA/AAA).
Use **`design-system`** + **`soft-skill`** para definir tokens: escala tipográfica, espaçamento, raios, sombras, elevação e estrutura de cards que transmitam "produto caro/premium".
Use **`frontend-design`** para propor 2–3 direções visuais distintas (descritas + mock de seção-chave). **Pare e me deixe escolher uma.**

## FASE 2 — CONTEÚDO E COPY
Use **`copywriting`** + **`marketing-psychology`** + **`marketing:brand-review`** para reescrever hero, subheadlines, CTAs, benefícios e prova social — mantendo PT-BR, tom B2B confiável, com gatilhos de conversão (clareza > esperteza). Garanta consistência de voz de marca.

## FASE 3 — PERFORMANCE (pré-requisito de Awwwards)
Otimize os assets: converta PNGs→WebP/AVIF (<300 KB), comprima/recodifique os vídeos, sirva `poster` adequado, corrija `loading="lazy"`/`preload`, e elimine animações infinitas que travam a renderização. Mire Lighthouse Performance ≥ 90 e LCP < 2,5s.

## FASE 4 — IMPLEMENTAÇÃO VISUAL
Aplique a direção escolhida ao código real (`styles.css`/`index.html`) usando **`impeccable-design-polish`**: tipografia, ritmo vertical, grid, detalhes de borda/sombra, estados de hover/focus, dark sections, layout responsivo impecável (mobile-first).

## FASE 5 — MOVIMENTO E MICRO-INTERAÇÕES (o "wow" controlado)
Use **`emilkowalski-motion`** para micro-interações com bom gosto e **`gsap-scrolltrigger`** + **`gsap-core`** para revelações ligadas a scroll, parallax sutil e seções "pinned" nos momentos-chave. Respeite `prefers-reduced-motion`. Nada de movimento gratuito — cada animação serve à narrativa.

## FASE 6 — VALIDAÇÃO E PROVA
Para CADA mudança, rode a página via **`/run`** e prove com screenshots (desktop + mobile via resize), console limpo, e re-checagem de acessibilidade. Faça uma autoavaliação final contra a rubrica Awwwards com a nota antes/depois por critério.

---

## REGRAS DE EXECUÇÃO
- Trabalhe incrementalmente; ao fim de cada fase, mostre antes/depois e aguarde meu OK.
- Não invente conteúdo factual sobre o produto — se faltar dado (números, logos reais de clientes), me pergunte.
- Toda alteração de UI deve ir no código-fonte (não só no preview); valide rodando.
- Mantenha PT-BR e a identidade da marca UpWeb.
- Priorize impacto: performance + hero + prova social primeiro.

Comece pela **FASE 0** e me entregue o diagnóstico.
