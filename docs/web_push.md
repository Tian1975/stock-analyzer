# Web Push (notificacions natives, sense obrir l'app)

## Com funciona (arquitectura sense servidor)

```
PWA (Safari/iPhone)
  │ 1. Demana permís + genera subscripció (endpoint xifrat únic)
  ▼
Modal amb el JSON de la subscripció → còpia manual, un sol cop
  │ 2. Enganxes el JSON a config/push_subscriptions.json (repo)
  ▼
alerts.py (GitHub Actions, cada dia)
  │ 3. Llegeix subscripcions + detecta alertes (igual que Fase 1)
  ▼
pywebpush + VAPID → envia directament a Apple/Google Push Service
  │
  ▼
Notificació nativa al mòbil (encara que la PWA estigui tancada)
```

## Setup inicial (un sol cop)

### 1. Configurar els secrets de GitHub

Al repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Nom del secret | Valor |
|---|---|
| `VAPID_PRIVATE_KEY` | *(el valor que Claude t'ha donat per xat — mai el posis al codi)* |
| `VAPID_CLAIMS_EMAIL` | `mailto:el-teu-email@exemple.com` (qualsevol email vàlid, Apple ho exigeix per identificar l'emissor) |

### 2. Activar les notificacions des de la PWA

1. Obre la PWA **des de la icona de la pantalla d'inici** (no des de Safari normal — a iOS, Web Push només funciona en apps instal·lades)
2. Toca **"🔔 Activar notificacions"** a la pantalla d'inici
3. Accepta el permís de notificacions
4. Es mostrarà un quadre amb un text llarg (JSON) — toca **"📋 Copiar"**
5. Vés al repo de GitHub → `config/push_subscriptions.json` → edita'l
6. Enganxa el JSON copiat dins de `[ ]` (si ja hi ha altres subscripcions, separa-les amb comes)
7. Fes "Commit"

### 3. Provar-ho

Executa `workflow_dispatch` del "Daily Stock Download". Si hi ha alguna alerta real, hauries de rebre una notificació nativa al mòbil en unes desenes de segons, sense obrir l'app.

## Limitacions conegudes

- **Només funciona amb la PWA afegida a la pantalla d'inici** (iOS 16.4+). Des de Safari normal, l'API de Push no està disponible.
- **Una subscripció per dispositiu**: si reinstal·les la PWA o canvies de mòbil, cal repetir el setup (pas 2).
- **`config/push_subscriptions.json` és senzill però manual**: no hi ha manera d'eliminar una subscripció caducada automàticament; si deixes de rebre notificacions, torna a fer el setup i substitueix l'entrada antiga.
- La clau **privada** VAPID viu només com a Secret de GitHub — mai apareix al codi ni als logs. La clau **pública** sí que és pública per disseny (va incrustada a `app.js`, és segur).

## Fitxers relacionats

| Fitxer | Responsabilitat |
|---|---|
| `app/app.js` (`setupPushNotifications`, `showPushSubscriptionModal`) | Demana permís, genera la subscripció, la mostra per copiar |
| `app/sw.js` (`push`, `notificationclick`) | Rep el push i mostra la notificació nativa; obre l'app en tocar-la |
| `config/push_subscriptions.json` | Llista de subscripcions (repo, editat manualment) |
| `src/alerts.py` (`send_web_push`) | Envia el push real via `pywebpush` quan hi ha alertes |
