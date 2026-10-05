import requests, csv, os
from datetime import datetime, timedelta

TG_TOKEN = os.getenv("8970734723:AAHBEsffgIT-ut5I47P0bj6xfcwwFUdf1-0")
TG_CHAT = os.getenv("8894963961")
LOG = "btc_final.csv"
JAHR_LOG = "btc_jahres_gedaechtnis.csv"
MARKT_LOG = "markt_chancen.csv"

def tg(txt):
    try:
        url = "https://api.telegram.org/bot" + TG_TOKEN + "/sendMessage"
        requests.post(url, data=dict(chat_id=TG_CHAT, text=txt), timeout=25)
        print("TG OK")
    except Exception as e:
        print(f"TG Fehler {e}")

def save(p, a):
    try:
        with open(LOG, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "BTC", p, a])
    except: pass

def save_jahr(heute, vor_1_jahr, jahres_avg):
    try:
        plus = round((heute/vor_1_jahr-1)*100,1) if vor_1_jahr>0 else 0
        with open(JAHR_LOG, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([datetime.now().strftime("%Y-%m-%d"), int(heute), int(vor_1_jahr), int(jahres_avg), plus])
    except: pass

def save_markt(coin, preis, change, grund):
    try:
        with open(MARKT_LOG, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), coin, preis, f"{change:.2f}", grund])
    except: pass

def get_stimmung():
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        return int(r.json()["data"][0]["value"])
    except: return 50

def get_jahres_rueckblick():
    try:
        heute = datetime.utcnow()
        vor_1_jahr_dt = heute - timedelta(days=365)
        url = f"https://api.exchange.coinbase.com/products/BTC-EUR/candles?granularity=86400&start={vor_1_jahr_dt.isoformat()}&end={(vor_1_jahr_dt+timedelta(days=1)).isoformat()}"
        data = requests.get(url, timeout=15).json()
        preis_vor_1_jahr = float(data[0][4]) if data and len(data)>0 else 0
        url2 = f"https://api.exchange.coinbase.com/products/BTC-EUR/candles?granularity=86400&start={(heute-timedelta(days=365)).isoformat()}&end={heute.isoformat()}"
        data2 = requests.get(url2, timeout=20).json()
        avg = sum([float(x[4]) for x in data2]) / len(data2) if data2 and len(data2)>10 else 0
        return preis_vor_1_jahr, avg
    except Exception as e:
        print("Jahr Fehler", e)
        return 0,0

def get_zeilen():
    try: return len(open(LOG,"r",encoding="utf-8").readlines())-1
    except: return 0

def vorhersage_machen(preis_now, angst_now, jahres_trend):
    try:
        rows = list(csv.DictReader(open(LOG,"r",encoding="utf-8")))
    except: return None, 0
    if len(rows) < 20: return None, len(rows)
    aehnlich = []
    for r in rows[-1000:]:
        try:
            if abs(int(float(r["angst"])) - angst_now) <= 6:
                aehnlich.append(float(r["preis"]))
        except: pass
    if len(aehnlich) < 5: return None, len(rows)
    avg = sum(aehnlich)/len(aehnlich)
    prognose = avg
    if angst_now < 20: prognose = preis_now * 1.03
    elif angst_now < 35: prognose = preis_now * 1.015
    elif angst_now > 80: prognose = preis_now * 0.985
    if jahres_trend > 40: prognose *= 1.005
    return prognose, len(rows)

def scanne_gesamten_markt(angst):
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=eur&order=market_cap_desc&per_page=60&page=1&price_change_percentage=24h"
        coins = requests.get(url, timeout=20).json()
        chancen = []
        for c in coins:
            try:
                sym = c["symbol"].upper()
                preis = c["current_price"]
                change = c.get("price_change_percentage_24h") or 0
                score = 0
                grund = ""
                if angst < 30 and -15 < change < -3:
                    score = (30-angst) + abs(change)*2
                    grund = f"Panik {angst} + Dip {change:.1f}% = Rebound Chance"
                elif -20 < change < -7:
                    score = abs(change)*1.5
                    grund = f"Ueberverkauft {change:.1f}%"
                elif angst >= 30 and -8 < change < -3 and c["market_cap"] > 1000000000:
                    score = abs(change)
                    grund = f"Gesunder Dip {change:.1f}% bei Big Cap"
                if score > 0:
                    chancen.append((sym, preis, change, grund, score, c["name"]))
            except: pass
        chancen.sort(key=lambda x: x[4], reverse=True)
        top3 = chancen[:3]
        for sym, preis, change, grund, score, name in top3:
            save_markt(sym, preis, change, grund)
        return top3
    except Exception as e:
        print("Markt Fehler", e)
        return []

def ein_check(mit_jahr=False, cache=[0,0]):
    try:
        pr = float(requests.get("https://api.exchange.coinbase.com/products/BTC-EUR/ticker", timeout=10).json()["price"])
        ag = get_stimmung()
        save(pr, ag)

        if mit_jahr:
            try:
                heute_str = datetime.now().strftime("%Y-%m-%d")
                schon = heute_str in open(JAHR_LOG,"r",encoding="utf-8").read()
            except: schon=False
            if not schon:
                v1, avg = get_jahres_rueckblick()
                if v1 > 0:
                    save_jahr(pr, v1, avg)
                    cache[0]=v1
                    cache[1]=avg
            else:
                try:
                    last = list(csv.DictReader(open(JAHR_LOG,"r",encoding="utf-8")))[-1]
                    cache[0]=float(last["vor_1_jahr"])
                    cache[1]=float(last["jahres_avg"])
                except: pass

        trend = (pr/cache[0]-1)*100 if cache[0]>0 else 0
        prognose, zeilen = vorhersage_machen(pr, ag, trend)
        top = scanne_gesamten_markt(ag)

        txt = "DEIN BITCOIN BLICK FUER MORGEN:\n"
        txt += f"BTC Preis: {int(pr)} Euro\n"
        if ag < 20: txt += f"Stimmung: Extreme Panik {ag} 😱 Alle haben Angst -> oft gute Kauf Zeit\n"
        elif ag < 40: txt += f"Stimmung: Angst {ag} -> unsicher\n"
        elif ag < 60: txt += f"Stimmung: Normal {ag}\n"
        else: txt += f"Stimmung: Gierig {ag} -> alle wollen kaufen\n"

        if prognose is None:
            txt += f"\nIch habe {zeilen} Mal so was gesehen\n"
            txt += f"Ich lerne noch, brauche {20-zeilen} Zeilen mehr\n"
        else:
            diff = prognose-pr
            proz = diff/pr*100
            txt += f"\nMeine 24h Schaetzung: {int(prognose)} Euro ({proz:+.1f}%)\n"
            txt += f"Ich habe {zeilen} Mal so was gesehen\n"

        txt += "\n--- MARKT CHANCEN SCAN (Top 50) ---\n"
        if not top:
            txt += "Gerade keine klaren Dips - Markt ruhig\n"
        else:
            for i, (sym, preis, change, grund, score, name) in enumerate(top,1):
                txt += f"{i}. {sym} ({name}) - {preis:.4f}€ ({change:+.1f}%)\n"
                txt += f" Grund: {grund}\n"

        txt += f"\nTagebuch: {zeilen} Zeilen + Jahres-Gedaechtnis aktiv"
        tg(txt)
        print(f"OK {zeilen} Zeilen {len(top)} Chancen Trend {trend:.1f}%")
    except Exception as e:
        print("Fehler", e)
        tg(f"Fehler: {e}")

if not os.path.exists(LOG):
    open(LOG,"w",newline="",encoding="utf-8").write("zeit,coin,preis,angst\n")
if not os.path.exists(JAHR_LOG):
    open(JAHR_LOG,"w",newline="",encoding="utf-8").write("datum,heute,vor_1_jahr,jahres_avg,plus_prozent\n")
if not os.path.exists(MARKT_LOG):
    open(MARKT_LOG,"w",newline="",encoding="utf-8").write("zeit,coin,preis,change_24h,grund\n")

ein_check(mit_jahr=True)
print("Fertig")
