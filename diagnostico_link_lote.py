#!/usr/bin/env python3
import json, os, re, shutil, time
from playwright.sync_api import sync_playwright

COOKIES=os.path.expanduser('~/.hermes/ml-affiliate/cookies_portal.json')
SRC=os.path.expanduser('~/divulgacao/roteiro_2026-08-12.json')
OUT='/tmp/diagnostico_meli_lote.txt'
PROFILE='/tmp/ml-link-diagnostico-profile'
try: shutil.rmtree(PROFILE)
except FileNotFoundError: pass

def main():
    data=json.load(open(SRC)); url=data['ofertas'][0]['link']
    cookies=json.load(open(COOKIES))
    # Cookie-Editor usa valores em minúsculas; Playwright exige Strict/Lax/None.
    for c in cookies:
        if c.get('sameSite'):
            c['sameSite']={'strict':'Strict','lax':'Lax','no_restriction':'None'}.get(str(c['sameSite']).lower(), 'Lax')
        else:
            c.pop('sameSite', None)
        c.pop('storeId', None)
    with sync_playwright() as p:
        ctx=p.chromium.launch_persistent_context(PROFILE,headless=True,viewport={'width':1280,'height':900},locale='pt-BR',args=['--disable-blink-features=AutomationControlled'])
        page=ctx.new_page()
        page.goto('https://www.mercadolivre.com.br',wait_until='domcontentloaded',timeout=45000)
        ctx.add_cookies(cookies)
        page.goto('https://www.mercadolivre.com.br/afiliados/hub?is_affiliate=true',wait_until='domcontentloaded',timeout=45000)
        page.wait_for_timeout(8000)
        before=page.locator('body').inner_text()[:12000]
        with open(OUT,'w') as f:
            f.write('BEFORE\n'+before+'\n\n')
            f.write('TEXTAREAS '+str(page.locator('textarea').count())+'\n')
            f.write('BUTTONS\n')
            for i in range(page.locator('button').count()):
                b=page.locator('button').nth(i)
                f.write(str(i)+' '+(b.inner_text() or '')+' aria='+str(b.get_attribute('aria-label'))+' title='+str(b.get_attribute('title'))+'\n')
        for text in ['Gerador de links','Gerar links','Criar links']:
            loc=page.get_by_text(text,exact=False)
            if loc.count():
                try: loc.first.click(force=True); page.wait_for_timeout(5000); break
                except Exception: pass
        ta=page.locator('textarea:visible').first
        if not ta.count():
            with open(OUT,'a') as f: f.write('\nNO_VISIBLE_TEXTAREA\n'+page.locator('body').inner_text()[:15000])
            ctx.close(); return
        ta.fill(url)
        page.wait_for_timeout(1000)
        clicked=False
        for text in ['Gerar','Criar']:
            loc=page.get_by_role('button',name=re.compile(text,re.I))
            if loc.count():
                try: loc.first.click(force=True); clicked=True; break
                except Exception: pass
        for i in range(12):
            page.wait_for_timeout(10000)
            html=page.locator('body').inner_text()
            m=re.findall(r'https?://meli\.la/\w+',html)
            if m:
                with open(OUT,'a') as f: f.write('\nFOUND '+str(m)+'\n'+html[:20000])
                break
        else:
            with open(OUT,'a') as f: f.write('\nNO_LINKS clicked='+str(clicked)+'\n'+page.locator('body').inner_text()[:30000]+'\nHTML_SNIP\n'+page.content()[:50000])
        ctx.close()

if __name__=='__main__': main()
