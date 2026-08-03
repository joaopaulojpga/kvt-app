# Canoa Clube — Appweb (MVP em NiceGUI)

## O que mudou em relação à versão Streamlit

- **A camada de regras de negócio não mudou nem uma linha**: `db.py`,
  `credits.py`, `payouts.py`, `reservations.py`, `expansion.py`,
  `attendance.py`, `classes.py`, `auth.py`, `seed.py` são exatamente os
  mesmos arquivos, copiados sem alteração. Todos os testes de negócio
  (`test_business_rules.py`, `test_integration.py`, `test_ajustes.py`)
  continuam passando sem qualquer ajuste.
- **Só as telas foram reescritas**, agora em NiceGUI (Python + Tailwind
  CSS por baixo), com visual mais próximo dos protótipos do PRD: sidebar
  navy, cards, badges coloridos, tipografia mais cuidada.
- `theme.py` — paleta de cores (mesma do PRD) e CSS global.
- `layout.py` — sidebar + topbar compartilhados entre as telas logadas.
- `ui_helpers.py` — componentes pequenos reutilizáveis (card, badge, títulos).

## Importante: onde isso é hospedado agora

O Streamlit Community Cloud (que usamos para validar o MVP) **não roda
NiceGUI** — ele é uma hospedagem específica para apps Streamlit. Para
validar esta versão ao vivo, precisamos usar o Render (a mesma
hospedagem já planejada para a versão definitiva) — o plano gratuito
dele serve perfeitamente para essa validação, sem custo, antes de
decidirmos migrar para o plano pago.

## Testes automatizados

```bash
python3 test_business_rules.py   # regras de crédito e repasse (inalteradas)
python3 test_integration.py      # fluxo completo (inalterado)
python3 test_ajustes.py          # ajustes da última rodada (inalterado)
python3 test_ui_smoke.py         # carrega as 7 telas com dados de exemplo
```

## Como rodar localmente

```bash
pip install -r requirements.txt
python3 app.py
```

Abre automaticamente em `http://localhost:8080`.

Login de demonstração (criado automaticamente):
- Instrutor: `joao@canoaclube.com` / senha `123456`
- Gestor: `gestor@canoaclube.com` / senha `123456`
- Ou cadastre um aluno novo pela própria tela Home.

## Limitação honesta deste ambiente de desenvolvimento

Este ambiente onde o código é escrito não tem acesso à internet para
instalar o NiceGUI de verdade — então não consigo abrir o app num
navegador de verdade e clicar nas telas antes de te enviar. O que eu
faço para compensar isso:

1. Toda a lógica de negócio (a parte que decide dinheiro, crédito,
   repasse) é validada por testes automatizados que rodam de verdade
   aqui, sem precisar do navegador.
2. Simulo a biblioteca NiceGUI inteira (um "dublê") e chamo a função
   de cada uma das 7 telas com dados de exemplo, pra pegar erros de
   código antes de te mandar.
3. Ainda assim, a validação final — "isso está bonito e funciona
   clicando de verdade" — só acontece quando o app está no ar e você
   testa. Se algo quebrar ou ficar estranho visualmente, me manda o
   print ou a mensagem de erro que eu ajusto rápido, do mesmo jeito
   que fizemos com a versão Streamlit.
