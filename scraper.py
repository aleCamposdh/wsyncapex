"""
Módulo de extracción de órdenes de SupplyPro usando Playwright
"""
import pandas as pd
import asyncio
import sys
from playwright.async_api import async_playwright
from config import SUPPLYPRO_URL

def log(msg):
    """Log que SÍ se ve en Streamlit Cloud"""
    sys.stderr.write(f"{msg}\n")
    sys.stderr.flush()


async def extraer_ordenes(username: str, password: str) -> pd.DataFrame:
    """
    Extrae las órdenes de SupplyPro usando credenciales específicas
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        try:
            log(f"🔗 Navegando a SupplyPro...")
            await page.goto(SUPPLYPRO_URL, wait_until='networkidle', timeout=60000)
            log(f"✅ Página cargada: {page.url}")

            log(f"📝 Llenando formulario de login...")
            await page.wait_for_selector('#user_name', state='visible', timeout=15000)
            await page.type('#user_name', username, delay=100)

            await page.wait_for_selector('#password', state='visible', timeout=15000)
            await page.type('#password', password, delay=100)

            log(f"✅ Credenciales ingresadas")

            log(f"🚀 Enviando login...")
            submit_button = await page.query_selector('input[type="submit"]')

            await submit_button.click()
            log(f"⏳ Esperando navegación después del login...")
            await page.wait_for_load_state('networkidle', timeout=60000)
            await page.wait_for_timeout(5000)

            current_url = page.url
            log(f"📍 URL después del login: {current_url}")

            if 'Login.asp' in current_url:
                if 'force_signon=Y' in current_url or 'force%5Fsignon=Y' in current_url:
                    log(f"⚠️ Sesión activa detectada, forzando nuevo login...")

                    try:
                        force_button = await page.query_selector('input[type="submit"]')
                        if force_button:
                            await force_button.click()
                            log(f"✅ Click en forzar login enviado")
                            await page.wait_for_load_state('networkidle', timeout=60000)
                            await page.wait_for_timeout(3000)

                            current_url = page.url
                            log(f"📍 URL después de forzar login: {current_url}")

                            if 'Login.asp' in current_url:
                                raise Exception("❌ No se pudo forzar el login. Cierra otras sesiones de SupplyPro con este usuario.")
                        else:
                            raise Exception("❌ No se encontró el botón para forzar login.")
                    except Exception as e:
                        raise Exception(f"❌ Error al forzar login: {str(e)}")

                else:
                    page_text = await page.content()

                    if 'invalid' in page_text.lower() or 'incorrect' in page_text.lower():
                        raise Exception("❌ Credenciales incorrectas. Verifica usuario y contraseña.")
                    elif 'locked' in page_text.lower() or 'disabled' in page_text.lower():
                        raise Exception("❌ La cuenta puede estar bloqueada o deshabilitada.")
                    else:
                        log(f"⚠️ DEBUG: Username usado: {username}")
                        log(f"⚠️ DEBUG: URL actual: {current_url}")
                        error_elements = await page.query_selector_all('.error, .alert, .warning, [class*="error"], [class*="alert"]')
                        if error_elements:
                            for elem in error_elements[:3]:
                                text = await elem.text_content()
                                if text and text.strip():
                                    log(f"⚠️ Mensaje en página: {text.strip()}")

                        raise Exception("❌ El login no se completó. Verifica que las credenciales sean correctas en config.py")

            log(f"✅ Login exitoso")

            print(f"🔍 Buscando link 'Newly Received Orders'...")

            await page.wait_for_timeout(5000)

            orden_clickeado = False

            try:
                link = page.locator('a:has-text("Newly Received Orders")').first
                if await link.count() > 0:
                    print(f"✅ Link encontrado (método 1)")
                    await link.click(timeout=10000)
                    orden_clickeado = True
            except Exception as e:
                print(f"⚠️ Método 1 falló: {str(e)}")

            if not orden_clickeado:
                try:
                    all_links = await page.query_selector_all('a')
                    for link in all_links:
                        text = await link.text_content()
                        if text and 'Newly Received Orders' in text:
                            print(f"✅ Link encontrado (método 2)")
                            await link.click()
                            orden_clickeado = True
                            break
                except Exception as e:
                    print(f"⚠️ Método 2 falló: {str(e)}")

            if not orden_clickeado:
                try:
                    print(f"🔍 Intentando click en 'Orders' primero...")
                    orders_link = page.locator('a:has-text("Orders")').first
                    if await orders_link.count() > 0:
                        await orders_link.click(timeout=10000)
                        await page.wait_for_load_state('networkidle', timeout=30000)
                        await page.wait_for_timeout(3000)
                        print(f"✅ Click en 'Orders' exitoso")

                        received_link = page.locator('a:has-text("Received")').first
                        if await received_link.count() > 0:
                            print(f"✅ Link 'Received' encontrado")
                            await received_link.click(timeout=10000)
                            orden_clickeado = True
                except Exception as e:
                    print(f"⚠️ Método 3 falló: {str(e)}")

            if not orden_clickeado:
                all_links = await page.query_selector_all('a')
                links_text = []
                for link in all_links[:20]:
                    text = await link.text_content()
                    if text:
                        links_text.append(text.strip())

                raise Exception(f"❌ No se encontró el link 'Newly Received Orders'. Links disponibles: {', '.join(links_text[:10])}")

            print(f"⏳ Esperando página de órdenes...")
            await page.wait_for_load_state('networkidle', timeout=60000)
            await page.wait_for_timeout(3000)

            print(f"🔍 Buscando filtro de órdenes...")
            await page.wait_for_selector('select[name="ref_epo_filter"]', state='visible', timeout=30000)
            print(f"✅ Filtro encontrado")

            print(f"⚙️ Aplicando filtro...")
            await page.select_option('select[name="ref_epo_filter"]', label='Show All Except EPOs')
            await page.wait_for_timeout(5000)
            await page.wait_for_load_state('networkidle', timeout=30000)
            print(f"✅ Filtro aplicado")

            try:
                rpp = await page.query_selector('select[name="rowsPerPage"], select[name="rows_per_page"], select[name="RowsPerPage"]')
                if rpp:
                    options = await rpp.query_selector_all('option')
                    values = [await o.get_attribute('value') for o in options]
                    target = '200' if '200' in values else (values[-1] if values else None)
                    if target:
                        await rpp.select_option(value=target)
                        await page.wait_for_load_state('networkidle', timeout=30000)
                        await page.wait_for_timeout(3000)
                        print(f"✅ Filas por página ajustado a {target}")
            except Exception as rpp_err:
                print(f"⚠️ No se pudo ajustar filas por página: {rpp_err}")

            print(f"📊 Extrayendo tabla de órdenes...")
            table_element = await page.query_selector('//th[contains(normalize-space(.), "Builder")]/ancestor::table')

            if not table_element:
                raise Exception("❌ No se encontró la tabla de órdenes. Puede que no haya órdenes disponibles.")

            table_html = await table_element.inner_html()
            full_table_html = f"<table>{table_html}</table>"

            from io import StringIO
            import tempfile
            import os

            df = pd.read_html(StringIO(full_table_html), header=None)[0]
            print(f"✅ Extraídas {len(df)} filas")

            temp_csv = tempfile.mktemp(suffix='.csv')
            df.to_csv(temp_csv, index=False, encoding='utf-8-sig', header=False)
            print(f"✅ Guardado a CSV temporal")

            df_final = pd.read_csv(temp_csv, header=None, dtype=str, encoding='utf-8-sig')
            print(f"✅ Releído desde CSV: {len(df_final)} filas")

            try:
                os.remove(temp_csv)
            except:
                pass

            print("🔍 Diagnosticando elementos de aceptación...")
            try:
                all_inputs = await page.query_selector_all('input[type="checkbox"]')
                print(f"  checkboxes encontrados: {len(all_inputs)}")
                for inp in all_inputs[:5]:
                    name = await inp.get_attribute('name') or ''
                    id_  = await inp.get_attribute('id') or ''
                    print(f"    checkbox name={name!r} id={id_!r}")

                all_selects = await page.query_selector_all('select')
                print(f"  selects encontrados: {len(all_selects)}")
                for s in all_selects:
                    name = await s.get_attribute('name') or ''
                    opts = await s.query_selector_all('option')
                    opt_texts = []
                    for o in opts:
                        t = await o.text_content()
                        opt_texts.append((t or '').strip())
                    print(f"    select name={name!r} opciones={opt_texts}")

                all_btns = await page.query_selector_all('input[type="submit"], input[type="button"], button')
                print(f"  botones encontrados: {len(all_btns)}")
                for b in all_btns:
                    val  = await b.get_attribute('value') or ''
                    txt  = await b.text_content() or ''
                    name = await b.get_attribute('name') or ''
                    print(f"    btn value={val!r} text={txt.strip()!r} name={name!r}")

                try:
                    await page.screenshot(path='/tmp/debug_accept.png', full_page=False)
                    print("  Screenshot guardado en /tmp/debug_accept.png")
                except Exception:
                    pass

                header_cb = None
                if all_inputs:
                    header_cb = all_inputs[0]
                    name = await header_cb.get_attribute('name') or ''
                    print(f"✅ Usando primer checkbox (name={name!r}) como header")
                    await header_cb.click()
                    await page.wait_for_timeout(800)

                action_selected = False
                for s in all_selects:
                    opts = await s.query_selector_all('option')
                    for opt in opts:
                        txt = (await opt.text_content() or '').strip()
                        if 'Accept Selected Orders' in txt:
                            val = await opt.get_attribute('value') or txt
                            await s.select_option(value=val)
                            action_selected = True
                            sname = await s.get_attribute('name') or ''
                            print(f"✅ Acción seleccionada en select name={sname!r} value={val!r}")
                            break
                    if action_selected:
                        break

                if not action_selected:
                    print("⚠️ No se encontró 'Accept Selected Orders' en ningún select")
                else:
                    await page.wait_for_timeout(500)
                    updated = False
                    for b in all_btns:
                        val = (await b.get_attribute('value') or '').strip()
                        txt = (await b.text_content() or '').strip()
                        if val == 'Update' or txt == 'Update':
                            await b.click()
                            updated = True
                            print(f"✅ Click en Update (value={val!r})")
                            break

                    if updated:
                        await page.wait_for_load_state('networkidle', timeout=30000)
                        await page.wait_for_timeout(2000)
                        print("✅ Órdenes aceptadas exitosamente")
                    else:
                        print("⚠️ No se encontró el botón Update")

            except Exception as accept_err:
                print(f"⚠️ Error al aceptar órdenes (extracción OK): {accept_err}")

            try:
                await page.click('text=Sign Out', timeout=5000)
                await page.wait_for_timeout(1000)
            except:
                pass

            return df_final

        except Exception as e:
            try:
                screenshot_bytes = await page.screenshot(full_page=True)
                with open('/tmp/error_screenshot.png', 'wb') as f:
                    f.write(screenshot_bytes)
                error_msg = f"{str(e)}\n\n[DEBUG] Screenshot guardado en /tmp/error_screenshot.png"
            except:
                error_msg = str(e)

            raise Exception(error_msg)

        finally:
            await browser.close()


def ejecutar_extraccion(username: str, password: str) -> pd.DataFrame:
    """Wrapper síncrono para la función asíncrona de extracción."""
    return asyncio.run(extraer_ordenes(username, password))
