# Canoa Clube — Appweb (NiceGUI + Supabase + Mercado Pago + Resend)

## O que mudou nesta rodada

- **Banco de dados real**: `db.py` agora conecta no Postgres do Supabase
  quando a variável `DATABASE_URL` existir; sem ela, continua caindo
  para SQLite local (útil para testes). Nenhum outro arquivo de regra
  de negócio precisou mudar.
- **Pagamento real**: `payments.py` integra com o Mercado Pago
  (Checkout Pro). Ao clicar em "Comprar", o aluno é redirecionado para
  a página do Mercado Pago (Pix ou cartão); a confirmação chega via
  webhook, que é quem realmente credita os créditos — nunca confiamos
  só no redirecionamento de volta.
- **E-mail real**: `mailer.py` integra com o Resend. Dispara e-mail de
  confirmação de compra e de notificação de expansão de vaga pendente
  para o instrutor responsável.

## Variáveis de ambiente a configurar no Render

No painel do seu serviço no Render → **Environment** → adicione:

| Variável | Valor | Onde conseguir |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:SUASENHA%40CODIFICADA@db.buvecxnldoawufswjzwq.supabase.co:5432/postgres` | Supabase → Connect → Connection string (ver nota abaixo) |
| `MERCADOPAGO_ACCESS_TOKEN` | seu Access Token de produção | Mercado Pago → Developers → Credenciais |
| `RESEND_API_KEY` | sua API Key | Resend → API Keys |
| `RESEND_FROM` | ex: `Canoa Clube <onboarding@resend.dev>` | ver nota sobre domínio abaixo |
| `APP_BASE_URL` | a URL pública do seu app, ex: `https://kvt-app.onrender.com` | a mesma do seu app no Render |
| `NICEGUI_STORAGE_SECRET` | qualquer texto aleatório | você mesmo inventa (já configuramos isso antes) |

**Nota sobre o `DATABASE_URL`:** se a conexão falhar (erro do tipo
"could not translate host name"), o endereço direto do Supabase pode
não estar resolvendo — nesse caso, pegue a string da aba **"Session
pooler"** em vez de "Direct connection" no painel do Supabase (ela tem
um formato de endereço diferente, mais novo) e use essa no lugar.

**Nota sobre o `RESEND_FROM`:** por padrão, o Resend permite enviar de
`onboarding@resend.dev` mesmo sem domínio próprio configurado (bom
para teste). Quando quiserem um remetente com a cara do clube (tipo
`contato@canoaclube.com.br`), é só configurar o domínio no Resend e
trocar essa variável.

## Configuração adicional no painel do Mercado Pago

Para o webhook funcionar, normalmente não precisa configurar nada
manualmente — o Mercado Pago usa a `notification_url` que já mandamos
em cada preferência de pagamento. Se quiser configurar mesmo assim,
vá em **Developers → Webhooks** e aponte para:
`https://SEU-APP.onrender.com/webhook/mercadopago`

## Testes automatizados

```bash
python3 test_business_rules.py
python3 test_integration.py
python3 test_ajustes.py
python3 test_ui_smoke.py
```

Todos rodam contra SQLite local — não precisam de nenhuma das contas
externas para passar.

## Limitação honesta desta rodada

Diferente da lógica de negócio (crédito, repasse, aprovação de vaga),
que é 100% testável sem depender de internet, **esta parte não dá para
testar de ponta a ponta aqui no meu ambiente** — conectar no Supabase
de verdade, chamar a API do Mercado Pago e enviar e-mail pelo Resend
exigem acesso à internet, que não tenho neste sandbox. Escrevi o
código com bastante cuidado (tratamento de erro, mensagens claras
quando algo falha), mas a validação final — "o pagamento realmente
libera o crédito", "o e-mail realmente chega" — só acontece quando
você testar ao vivo. Se algo falhar, me manda a mensagem de erro (ou
os logs do Render) que eu ajusto rápido.

## Como rodar localmente

```bash
pip install -r requirements.txt
python3 app.py
```

Sem as variáveis de ambiente configuradas, roda em modo "simulado"
local (SQLite, sem pagamento/e-mail reais) — útil para continuar
testando a navegação sem gastar nada.
