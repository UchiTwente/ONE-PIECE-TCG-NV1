"""One Piece TCG: official downloadable Cardmarket guide, with weekly price history.

Downloads publicly available Cardmarket JSON. A GitHub Pages deployment can preserve
up to 26 weekly price points per exact Cardmarket idProduct from the previously
published historical feed. No account data or collection inventories are sent.
"""
import json
import os
import pathlib
import re
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request

ROOT = pathlib.Path(__file__).resolve().parent
URLS = {
    'products': 'https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_18.json',
    'prices': 'https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_18.json',
}
CODE = re.compile(r'\b(?:OP|EB|PRB|ST)\d{2}-\d{3}\b', re.I)

def download(url, timeout=110):
    req = Request(url, headers={'User-Agent': 'OnePieceCollectionPersonal/1.0 (+weekly public-price-index)'})
    with urlopen(req, timeout=timeout) as response:
        return json.load(response)

def records(obj, *keys):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for key in keys:
            if isinstance(obj.get(key), list):
                return obj[key]
    raise ValueError('Schéma JSON non reconnu : cotations anciennes non écrasées')

def week_of(date):
    date = date.astimezone(timezone.utc)
    return (date - timedelta(days=date.weekday())).strftime('%Y-%m-%d')

def history_url():
    repo = os.getenv('GITHUB_REPOSITORY', '').split('/')
    if len(repo) != 2 or not all(re.fullmatch(r'[a-zA-Z0-9_.-]+', x) for x in repo):
        return None
    return f'https://{repo[0].lower()}.github.io/{repo[1]}/prix_historique_cardmarket.json'

def merge_history(old, stamp, current, max_weeks=26):
    old_weeks = old.get('weeks', []) if isinstance(old, dict) else []
    old_by_product = old.get('byProduct', {}) if isinstance(old, dict) else {}
    old_weeks = [x for x in old_weeks if isinstance(x, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', x)]
    weeks = sorted(set(old_weeks + [stamp]))[-max_weeks:]
    by_id = {}
    for pid in set(current) | set(old_by_product):
        prior = old_by_product.get(pid, [])
        known = {w: prior[i] for i, w in enumerate(old_weeks) if i < len(prior) and isinstance(prior[i], (int,float))}
        if pid in current:
            known[stamp] = current[pid]
        vals = [known.get(w) for w in weeks]
        if any(v is not None for v in vals):
            by_id[pid] = vals
    return {'format': 'onepiece-cardmarket-weekly-v1', 'weeks': weeks, 'byProduct': by_id}

def run():
    product_data = download(URLS['products'])
    price_data = download(URLS['prices'])
    products=[]
    for p in records(product_data,'products','productList','items','data'):
        name=p.get('name','')
        if isinstance(name,dict): name=name.get('1') or name.get('en') or ''
        if not isinstance(name,str) or not CODE.search(name):continue
        pid=p.get('idProduct')
        if pid is None:continue
        products.append({'idProduct':pid,'name':name,'idExpansion':p.get('idExpansion')})
    approved={str(p['idProduct']) for p in products}
    prices=[]
    today={}
    for row in records(price_data,'priceGuides','priceGuide','prices','items','data'):
        pid=str(row.get('idProduct',''))
        if pid not in approved:continue
        price={k:row.get(k) for k in ['idProduct','trend','low','avg','avg7','avg30']}
        prices.append(price)
        raw=row.get('trend')
        if raw is None:raw=row.get('avg7')
        if raw is None:raw=row.get('avg')
        try:
            v=float(raw)
            if 0<=v<1000000:today[pid]=round(v,2)
        except (TypeError,ValueError):pass
    if len(products)<100 or len(prices)<100 or len(today)<100:
        raise ValueError(f'Guide insuffisant ({len(products)} produits, {len(prices)} prix) : aucune écriture')
    now=datetime.now(timezone.utc)
    price_out={
       'observed_at':now.isoformat(),'source':'Cardmarket — fichiers publics One Piece (jeu 18)',
       'products':products,'priceGuides':prices,'createdAt':price_data.get('createdAt') if isinstance(price_data,dict) else None
    }
    # Les anciens relevés restent dans le dépôt, indépendamment de GitHub Pages.
    prior=ROOT/'prix_historique_cardmarket.json'
    old={}
    if prior.exists():
        old=json.loads(prior.read_text(encoding='utf-8'))
        if not isinstance(old,dict) or not isinstance(old.get('weeks'),list) or not isinstance(old.get('byProduct'),dict):
            raise ValueError('Historique existant invalide : aucune écriture')
    history=merge_history(old,week_of(now),today)
    # Écriture seulement après validation intégrale.
    (ROOT/'prix_cardmarket.json').write_text(json.dumps(price_out,ensure_ascii=False,separators=(',',':')),encoding='utf8')
    prior.write_text(json.dumps(history,ensure_ascii=False,separators=(',',':')),encoding='utf8')
    print(f'{len(products)} produits; {len(prices)} prix, {len(history["weeks"])} semaines d’historique publiées.')

if __name__=='__main__': run()
