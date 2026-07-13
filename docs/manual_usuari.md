# Manual d'ús — Stock Analyzer (guia per a principiants)

Aquest manual assumeix que no has invertit mai i que vols entendre-ho tot
pas a pas. No hi ha preguntes "massa bàsiques" — si alguna cosa no queda
clara, és culpa del manual, no teva.

---

## 0. Abans de res: què és això i què NO és

**És:** una eina que cada dia mira 79 empreses reals, els calcula un munt de
números tècnics i financers, i te'ls resumeix en una puntuació fàcil
d'entendre (0 a 100) i una explicació en català de per què.

**NO és:**
- Un assessor financer. Ningú aquí et diu "compra això" amb garanties.
- Una màquina de predir el futur. Els números es basen en el passat i el
  present; el mercat pot fer qualsevol cosa demà.
- Segur. **Invertir sempre comporta risc de perdre diners**, per bo que
  sembli un score.

Pensa-ho com un termòmetre molt bo, no com un metge. Et diu la temperatura
amb precisió; la decisió de què fer amb aquesta informació sempre és teva.

---

## 1. Glossari mínim (paraules que trobaràs pertot arreu)

| Terme | Què vol dir, en pla senzill |
|---|---|
| **Ticker** | El "nom curt" d'una empresa a borsa. Ex: `AAPL` = Apple, `BBVA.MC` = BBVA a la borsa de Madrid |
| **Score / puntuació** | Nota de 0 a 100. Com més alta, més "bones senyals" té ara mateix segons les regles de l'app |
| **RSI** | Un número de 0 a 100 que mesura si una acció "s'ha mogut massa de pressa" recentment. >70 = ha pujat molt de pressa (risc de frenada). <30 = ha caigut molt de pressa (risc de rebot, però també de seguir caient) |
| **SMA20 / SMA50 / SMA200** | La mitjana del preu dels últims 20/50/200 dies. Si el preu actual és per sobre de totes tres i estan ordenades (20>50>200), és senyal de tendència alcista sostinguda, no un simple rebot d'un dia |
| **MACD** | Un indicador que compara mitjanes a curt i mitjà termini per veure si l'impuls (momentum) és a favor o en contra |
| **PER** | Preu / Beneficis. Diu quantes vegades els beneficis anuals estàs pagant per l'acció. Més alt = més "car" en relació al que guanya l'empresa (però un PER alt no sempre és dolent, depèn del sector) |
| **Volatilitat** | Com de "nerviosa" es mou l'acció. Alta volatilitat = pujades i baixades més brusques, en totes dues direccions |
| **Risc (a l'app)** | Baix / Moderat / Alt. Combina volatilitat + beta + ATR. **No té res a veure amb si l'empresa és "bona" o "dolenta"** — una empresa excel·lent pot tenir risc alt simplement perquè es mou molt |
| **Confiança de dades** | % de dades que teníem disponibles per calcular el score. 100% = tot complet. Si baixa (ex. 67%), vol dir que faltaven alguns fonamentals aquell dia — el score és menys fiable, no necessàriament pitjor |

---

## 2. Els 3 horitzons: quin score mirar segons el que vulguis fer

L'app no dona un sol número — en dona tres, perquè "bo" depèn de quant
temps penses mantenir la inversió.

| Horitzó | Es fixa sobretot en... | Útil si... |
|---|---|---|
| **Curt termini** | Si està pujant ARA MATEIX (momentum, tendència) | Vols entrar i sortir en dies/setmanes |
| **Mitjà termini** (el que veus per defecte) | Equilibri entre tendència, momentum, qualitat i preu | No tens clar l'horitzó, o vols alguna cosa "raonable" en general |
| **Llarg termini** | Si l'empresa és sòlida i barata (qualitat, valoració, creixement) | Vols comprar i oblidar-te'n uns quants anys |

**Regla senzilla:** si ets principiant i no tens pressa, el llarg termini
sol ser el més "perdonador" amb els errors de moment d'entrada — però també
el que triga més a donar resultats.

---

## 3. Com llegir la fitxa d'una empresa (pas a pas)

Quan toques una empresa, veuràs de dalt a baix:

1. **L'anell gran amb un número (0-100)**: el score de mitjà termini.
   Verd = bo (≥66), groc = regular (40-65), vermell = fluix (<40).
2. **El preu actual i la data de les dades.**
3. **"Fa X dies al Top 10"**: quant de temps porta entre les 10 millors de
   tot l'univers. Molts dies seguits = tendència més consolidada, no un
   pic d'un sol dia.
4. **El gràfic petit (sparkline)**: l'evolució del score els últims dies.
   Línia verda pujant = millorant. Vermella baixant = empitjorant.
5. **Les 3 barres d'horitzó** (curt/mitjà/llarg): compara't-los. Si els
   tres són semblants, el senyal és consistent. Si el curt és molt alt
   però el llarg molt baix, vol dir "puja ara però és cara/fluixa a
   llarg termini" — típic d'una moda passatgera.
6. **Els 6 subscores** (Momentum, Tendència, Valoració, Qualitat,
   Creixement, Risc): el desglossament del número gran.
7. **L'etiqueta de risc + confiança de dades.**
8. **"Per què aquesta puntuació"**: la llista amb ✔ i ⚠️. **Aquesta és la
   part més important per a un principiant** — llegeix-la sempre abans
   de fer res.
9. **El botó daurat "Veure cotització i operar"**: t'hi porta a mirar
   l'acció en detall (veure secció 6).

---

## 4. Quan té sentit "comprar" (llegir el senyal, no una ordre)

No hi ha cap botó de comprar dins d'aquesta app — i és a propòsit. El que
fas és mirar aquests senyals i decidir tu:

**Senyals a favor (✔):**
- Score alt (>70) a l'horitzó que t'interessa
- ✔ SMA20 > SMA50 > SMA200 (tendència alcista real, no soroll d'un dia)
- RSI entre 40-65 (encara hi ha marge, no ha pujat ja massa)
- Risc "baix" o "moderat" si ets principiant (l'alt és per a qui pot
  assumir moviments forts)
- Confiança de dades alta (>90%)

**Senyals que criden a anar amb compte (⚠️, no necessàriament "no"):**
- RSI > 70: ja ha pujat molt, entrar ara és més arriscat perquè pot
  "refredar-se"
- Score de llarg termini molt baix encara que el curt sigui alt: pot ser
  una pujada de curt recorregut
- Volatilitat elevada esmentada a l'explicació

**El més important:** cap senyal aïllat és una garantia. Mira'ls tots
junts, i si encara tens dubtes, **no facis res** — no invertir també és
una opció vàlida, sobretot quan comences.

---

## 5. Quan té sentit "vendre" (per a una posició que ja tens)

Si ja tens accions d'una empresa que segueixes, vigila aquests senyals a
la seva fitxa:

- ⚠️ **RSI > 70 de forma sostinguda** (uns quants dies seguits, no un de
  sol) → zona de sobrecompra, el marge de pujar més es redueix
- ⚠️ **"Tendència baixista" apareix a l'explicació** (SMA20 < SMA50 <
  SMA200) → el suport tècnic que la mantenia s'ha trencat
- **El score de mitjà termini cau dia rere dia** al gràfic (sparkline
  vermell descendent)
- **Surt del Top 10** quan hi havia estat molts dies seguits (l'app t'ho
  notifica automàticament, veure secció 7)

De nou: són **senyals d'alerta perquè hi paris atenció i revisis**, no
ordres de venda automàtiques. Decideix sempre segons la teva pròpia
situació (per exemple, si tens pèrdues o guanys, els teus objectius, etc.)

---

## 6. El botó "Veure cotització i operar" — com funciona i com configurar-lo

Aquest botó daurat, a la fitxa de cada empresa, t'obre una pàgina externa
amb la cotització d'aquella empresa.

**Per defecte** t'envia a **Yahoo Finance** (gratuït, sense registre,
només informatiu — no hi pots comprar ni vendre res, només consultar).

**Si en el futur tries un broker** (una plataforma des d'on comprar/vendre
accions de veritat), pots configurar el botó perquè t'hi porti directament:

1. A la fitxa de qualsevol empresa, toca **"⚙️ Configurar el meu broker"**
2. Enganxa la URL de cerca del teu broker, posant `{TICKER}` on aniria
   el símbol de l'empresa (per exemple, si el teu broker cerca accions amb
   una URL com `https://elteubroker.com/cerca?simbol=AAPL`, hauries de
   posar `https://elteubroker.com/cerca?simbol={TICKER}`)
3. Toca "Desar"

**Important sobre triar un broker:** aquesta app no en recomana cap ni té
cap acord amb ningú — la tria és totalment teva. Coses a mirar abans de
triar-ne un: si està regulat (a Espanya, per la CNMV), quines comissions
cobra per compra/venda i per mantenir els diners, i si el idioma/suport
et resulta còmode. Pren-te temps per comparar-ne uns quants abans de
decidir; no cal fer-ho ara mateix.

---

## 6bis. El botó "🤖 Analitzar amb IA"

A cada fitxa d'empresa hi ha un botó daurat que et porta a `claude.ai` amb
un resum complet de l'empresa (score, subscores, checklist, explicació,
"què vigilar") ja copiat al porta-retalls.

**Com fer-ho servir:**
1. Toca "🤖 Analitzar amb IA →"
2. S'obre `claude.ai` en una pestanya nova
3. Enganxa el text (ja el tens copiat)
4. Pregunta el que vulguis — per exemple "Quines preguntes hauria de fer-me
   abans de considerar aquesta empresa?"

Això **no envia res automàticament** ni es connecta a cap API — només
prepara el text i t'obre la conversa perquè hi enganxis tu mateix. Zero
cost afegit, funciona sempre.

## 7. Les alertes: què vol dir cadascuna i què hauries de fer

L'app et pot avisar de dues maneres (Issues de GitHub i notificacions
push natives). Aquestes són totes les alertes possibles i què signifiquen:

| Alerta | Què vol dir | Què fer |
|---|---|---|
| 🚀 **Entra al Top 3** | Una de les teves empreses seguides és ara mateix de les 3 millors de tot l'univers | Val la pena mirar-la amb calma — és un senyal fort |
| 📈 **Entra al Top 10** | Igual, però una mica menys exclusiu | Mira-la, sense presses |
| 📉 **Surt del Top 10** | Ha empitjorat prou per sortir de les millors 10 | Revisa si encara la vols mantenir/seguir |
| ⚠️ **RSI sobrecomprat (>70)** | Ha pujat molt de pressa recentment | Si la tens: considera si és moment de recollir guanys. Si no la tens: entrar ara és més arriscat |
| ⚠️ **RSI sobrevenut (<30)** | Ha caigut molt de pressa | Pot ser una oportunitat... o pot seguir caient. Mira per què ha caigut abans de res |
| ⚠️ **Trencament de tendència** | SMA20 ha baixat per sota de SMA50 | Senyal d'alerta tècnica, sol precedir caigudes més grans |
| 🟡 **Score cau ≥5 punts** | Deteriorament moderat, "vigila-la" | No cal actuar ja, però para-hi atenció els pròxims dies |
| 🔴 **Score cau ≥10 punts** | Deteriorament clar, "revisa-la" | Mira l'explicació de la fitxa per entendre per què |
| ℹ️ **Confiança de dades baixa** | Falten dades fonamentals aquell dia | Alerta tècnica, no de mercat — el score és menys fiable temporalment |
| 🔥 **Descoberta (Top 10 per primera vegada)** | Una empresa que NO segueixes ha entrat al Top 10 | Curiositat, no obligació — pots mirar-la i decidir si l'afegeixes als teus favorits |

Cada alerta, tant si arriba per email/Issue com per notificació push,
porta un enllaç **"Veure fitxa"** que et porta directament a la fitxa
d'aquella empresa dins la PWA, amb tota l'explicació.

### Com configurar quines empreses vigilen les alertes

Edita el fitxer `config/favorites.txt` al repo de GitHub (un ticker per
línia). **Això és diferent** dels favorits (★) que marques dins la PWA,
que només serveixen per organitzar la pantalla d'inici — els d'alertes
són els que el sistema vigila activament cada dia.

---

## 8. Rutina diària recomanada (30 segons)

1. Si t'arriba una notificació push, toca-la — et porta directament a la
   fitxa rellevant
2. Si no, obre l'app (dades actualitzades cada dia laborable a la nit)
3. Mira "⭐ Favorits" primer
4. Un cop d'ull al "🔥 Top oportunitats"
5. Si alguna cosa et crida l'atenció, entra a la fitxa i **llegeix
   l'explicació sencera** abans de decidir res

---

## 9. Advertència final (de veritat important)

- Els scores es basen en dades històriques i regles predefinides —
  **no prediuen el futur**.
- Un score alt no garanteix pujada. Un score baix no garanteix baixada.
- El mercat sempre comporta risc real de perdre diners, incloent-hi la
  possibilitat de perdre'ls tots.
- Aquesta eina és un **suport** a la teva pròpia anàlisi i decisió, mai
  un substitut. Si mai tens dubtes seriosos sobre com invertir els teus
  estalvis, parlar amb un assessor financer professional i regulat és
  sempre una opció raonable, especialment quan comences.
