import flet as ft
from datetime import datetime
import logica
import notificador
import json
import os

# Configuración de archivos
ARCHIVO_EXCEL_CATALOGO = "catalogo_inventario_condesas.xlsx"

def cargar_inventario():
    if os.path.exists("inventario.json"):
        with open("inventario.json", "r") as f:
            return json.load(f)
    return {}

def guardar_inventario(datos):
    with open("inventario.json", "w") as f:
        json.dump(datos, f, indent=4)

STOCK_ACTUAL = cargar_inventario()

def mostrar_ventana_pedidos(page, sugerencias):
    # Lista visual de los pedidos
    lista_pedidos_ui = ft.Column(spacing=10, scroll=ft.ScrollMode.ALWAYS, height=400)
    
    if not sugerencias:
        lista_pedidos_ui.controls.append(ft.Text("✅ Todo el stock está en niveles óptimos."))
    else:
        # Agrupamos por analizador para la prioridad visual
        analizador_actual = ""
        for s in sugerencias:
            if s["analizador"] != analizador_actual:
                analizador_actual = s["analizador"]
                lista_pedidos_ui.controls.append(
                    ft.Text(f"--- {analizador_actual} ---", weight="bold", color="blue")
                )
            
            # Tarjeta de sugerencia
            lista_pedidos_ui.controls.append(
                ft.ListTile(
                    title=ft.Text(f"{s['nombre']} (Ref: {s['ref']})"),
                    subtitle=ft.Text(f"Actual: {s['actual']} | Mín: {s['minimo']}"),
                    trailing=ft.Text(f"Pedir: {s['pedir_cajas']} cja(s)", weight="bold", size=16),
                )
            )

    def enviar_pedido_click(e):
        # Aquí irá la lógica de enviar por correo en la siguiente sesión
        print("Enviando correo...")
        dlg_pedidos.open = False
        page.update()

    dlg_pedidos = ft.AlertDialog(
        title=ft.Text("Sugerencia de Pedido"),
        content=ft.Container(content=lista_pedidos_ui, width=500),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: setattr(dlg_pedidos, "open", False)),
            ft.FilledButton("Confirmar y Enviar", icon=ft.Icons.EMAIL, on_click=enviar_pedido_click)
        ],
    )

    page.dialog = dlg_pedidos
    dlg_pedidos.open = True
    page.update()


async def main(page: ft.Page):
    page.title = "Gestión de Reactivos - Condesa"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 450
    page.window_height = 850
    page.padding = 20

    unidad_seleccionada = ""
    lista_pedido = []

    def reiniciar_app(e):
        nonlocal lista_pedido, unidad_seleccionada
        lista_pedido.clear()
        unidad_seleccionada = ""
        mostrar_pantalla_seleccion()

    # --- PANTALLAS ---

    def mostrar_pantalla_seleccion():
        page.clean()
        opciones_clinicas = ["Clínica de Especialidades Condesa", "Clínica de Especialidades Condesa Iztapalapa"]
        ac_clinica = ft.AutoComplete(suggestions=[ft.AutoCompleteSuggestion(key=c, value=c) for c in opciones_clinicas])

        def confirmar_seleccion(e):
            nonlocal unidad_seleccionada
            if ac_clinica.value:
                unidad_seleccionada = ac_clinica.value
                mostrar_menu_principal()
            else:
                page.snack_bar = ft.SnackBar(ft.Text("⚠️ Selecciona una clínica válida"))
                page.snack_bar.open = True
            page.update()

        page.add(
            ft.Text("Sistema de Inventario", size=30, weight="bold"),
            ft.Text("Escriba el nombre de la unidad:"),
            ac_clinica,
            ft.FilledButton("Continuar", on_click=confirmar_seleccion, icon="arrow_forward")
        )

    def mostrar_menu_principal():
        page.clean()
        
        page.add(ft.Text(f"Unidad: {unidad_seleccionada}", size=20, weight="bold"))
        page.add(ft.Divider())
        page.add(ft.Text("Alertas de Inventario (Último Reporte):", size=16, weight="w500"))

        alertas_actualizadas = logica.obtener_alertas_desde_excel(unidad_seleccionada)
    
        lista_alertas = ft.Column(spacing=5)
        for mensaje in alertas_actualizadas:
            color = "red" if "❌" in mensaje else ("orange" if "⚠️" in mensaje else "green")
            lista_alertas.controls.append(
                ft.Text(mensaje, color=color, size=13, weight="w400")
            )
        
        page.add(lista_alertas)
        
            
        page.add(
            ft.Divider(),
            ft.FilledButton("REALIZAR PEDIDO", icon=ft.Icons.ADD,
                             on_click=lambda _: mostrar_pantalla_pedido(), width=300, height=60),
            ft.FilledButton("GESTIONAR INVENTARIO", icon=ft.Icons.INVENTORY,
                              on_click=lambda _: mostrar_pantalla_inventario(), width=300, height=60),
            ft.TextButton("Cambiar de Clínica", on_click=reiniciar_app)
        )
        page.update()

    def mostrar_pantalla_inventario():
        page.clean()
        CATALOGO = logica.obtener_catalogo()
        sesion_auditoria = {}
        
        # --- FUNCIONES DE APOYO ---
        def actualizar_dato(ref, campo, valor):
            try:
                if ref in sesion_auditoria:
                    if campo in ["en_uso", "stock_nuevo"]:
                        # 1. Quitamos cualquier espacio
                        # 2. Convertimos a float primero por si el usuario puso un punto por error
                        # 3. Lo convertimos a int para eliminar el decimal
                        valor_limpio = int(float(valor)) if valor and str(valor).strip() != "" else 0
                        sesion_auditoria[ref][campo] = valor_limpio
                    else:
                        sesion_auditoria[ref][campo] = valor
            except:
                # Si el usuario escribe algo que no es un número (como letras), lo ponemos en 0
                if campo in ["en_uso", "stock_nuevo"]:
                    sesion_auditoria[ref][campo] = 0

        def formatear_fecha(e, ref):
            valor = e.control.value
            
            # --- 1. LÓGICA DE BORRADO ---
            if len(valor) < getattr(e.control, "_last_len", 0):
                e.control._last_len = len(valor)
                actualizar_dato(ref, "caducidad", valor)
                page.update()
                return

            # --- 2. LÓGICA DE ESCRITURA (MÁSCARA) ---
            solo_numeros = "".join(filter(str.isdigit, valor))
            nuevo_valor = ""

            if len(solo_numeros) > 0:
                nuevo_valor = solo_numeros[:2]
                if len(solo_numeros) > 2:
                    nuevo_valor += "-" + solo_numeros[2:4]
                if len(solo_numeros) > 4:
                    nuevo_valor += "-" + solo_numeros[4:8]

            nuevo_valor = nuevo_valor[:10]

            # --- 3. ACTUALIZACIÓN ---
            e.control.value = nuevo_valor
            e.control._last_len = len(nuevo_valor)
            actualizar_dato(ref, "caducidad", nuevo_valor)
            page.update()

        def eliminar_item(ref):
            if ref in sesion_auditoria:
                del sesion_auditoria[ref]
                actualizar_lista_visual()

        def finalizar_auditoria_click(e):
            
            ruta = logica.exportar_auditoria_roche(unidad_seleccionada, sesion_auditoria)
            
            sugerencias = logica.calcular_sugerencia_pedido(sesion_auditoria)
            
            mostrar_ventana_pedidos(page, sugerencias)
            
            page.snack_bar = ft.SnackBar(ft.Text(f"Inventario guardado en: {ruta}"))
            page.snack_bar.open = True
            mostrar_menu_principal() 
            page.update()

        def agregar_al_inventario(e):
            seleccion = e.control.value
            if " | " not in seleccion: return
            ref_id = seleccion.split(" | ")[0].strip()

            if ref_id in CATALOGO:
                info = CATALOGO[ref_id]
                repeticiones = sum(1 for k in sesion_auditoria if k.startswith(ref_id))
                nueva_llave = f"{ref_id}#{repeticiones + 1}"

                sesion_auditoria[nueva_llave] = {
                    "ref": ref_id,
                    "nombre": info.get("Alias", "Sin nombre"), # "Alias" con A mayúscula
                    "en_uso": 0,
                    "stock_nuevo": 0,
                    "caducidad": ""
                }
                ac_busqueda.value = ""
                actualizar_lista_visual()
            page.update()

        def actualizar_lista_visual():
            contenedor_lista.controls.clear()
            for id_unico, datos in sesion_auditoria.items():
                val_en_uso = str(int(datos["en_uso"])) if datos["en_uso"] != 0 else ""
                val_stock = str(int(datos["stock_nuevo"])) if datos["stock_nuevo"] != 0 else ""

                txt_lote = ft.TextField(
                    label="Lote",
                    hint_text="Número de lote",
                    value=datos.get("lote", ""),
                    width=100,
                    text_size=12,
                    on_change=lambda e, r=id_unico: actualizar_dato(r, "lote", e.control.value)
                )

                txt_en_uso = ft.TextField(
                    label="A bordo",
                    hint_text="En uso",
                    value=val_en_uso,
                    width=150,
                    text_size=12,
                    keyboard_type=ft.KeyboardType.NUMBER,
                    on_change=lambda e, r=id_unico: actualizar_dato(r, "en_uso", e.control.value),
                )

                txt_stock = ft.TextField(
                    label="Nuevos",
                    hint_text="Cartchos cerrados",
                    value=val_stock,
                    width=150,
                    text_size=12,
                    keyboard_type=ft.KeyboardType.NUMBER,
                    on_change=lambda e, r=id_unico: actualizar_dato(r, "stock_nuevo", e.control.value),
                )

                txt_caducidad = ft.TextField(
                    label="Caducidad",
                    hint_text="DD-MM-AAAA",
                    value=datos["caducidad"],
                    width=150,
                    text_size=12,
                    # Mantenemos tu estructura de lambda para el id_unico
                    on_change=lambda e, r=id_unico: formatear_fecha(e, r),
                )
                
                txt_caducidad._last_len = len(datos["caducidad"])

                # Configuración de saltos con ENTER
                async def saltar_a_stock(e):
                    await txt_stock.focus()

                async def saltar_a_caducidad(e):
                    await txt_caducidad.focus()

                txt_en_uso.on_submit = saltar_a_stock
                txt_stock.on_submit = saltar_a_caducidad

                contenedor_lista.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"{datos['nombre']}", weight="bold", expand=True, size=14),
                                ft.IconButton(
                                    ft.Icons.DELETE_OUTLINE, 
                                    icon_color="red",
                                    on_click=lambda _, r=id_unico: eliminar_item(r))
                            ]),
                            ft.Row([
                                txt_en_uso,
                                txt_stock,
                                txt_lote,
                                txt_caducidad
                            ], alignment="spaceBetween"),
                        ]),
                        padding=10, border=ft.Border.all(1, "lightgrey"), border_radius=10, margin=5
                    )
                )
            page.update()

        # --- LÓGICA DE BÚSQUEDA ---
        def filtrar_busqueda(e):
            texto = e.control.value.lower()
            CATALOGO = logica.obtener_catalogo() # Refrescamos el catálogo
            
            sugerencias_nuevas = []
            
            if len(texto) > 0:
                for ref, info in CATALOGO.items():
                    # Obtenemos alias y referencia para comparar
                    alias = str(info.get("Alias", "")).lower()
                    referencia = str(ref).lower()
                    
                    # Si el texto está en el Alias o en la Referencia
                    if texto in alias or texto in referencia:
                        texto_opcion = f"{ref} | {info.get('Alias', 'Sin nombre')}"
                        sugerencias_nuevas.append(
                            ft.AutoCompleteSuggestion(key=texto_opcion, value=texto_opcion)
                        )
                
                ac_busqueda.suggestions = sugerencias_nuevas
            else:
                ac_busqueda.suggestions = []
            
            page.update()

        
        ac_busqueda = ft.AutoComplete(
            on_select=agregar_al_inventario,
            on_change=filtrar_busqueda
        )

        contenedor_lista = ft.Column(scroll="auto", expand=True)

        # 2. AL FINAL, cuando ya existen, los agregamos a la página
        page.add(
            ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: mostrar_menu_principal()),
            ft.Text(f"Inventario: {unidad_seleccionada}", size=22, weight="bold"),
            ac_busqueda,
            ft.Divider(),
            contenedor_lista,
            ft.Divider(),
            ft.FilledButton(
                "GENERAR REPORTE DE CAMPO",
                icon=ft.Icons.FILE_DOWNLOAD,
                on_click=finalizar_auditoria_click,
                bgcolor=ft.Colors.BLUE_900,
                color="white", width=400, height=50
            )
        )

    def mostrar_pantalla_pedido():
        page.clean()
        catalogo = logica.obtener_catalogo()
        ultimo_inv = logica.obtener_ultimo_inventario_dict(unidad_seleccionada)
        lista_carrito = []

        lbl_resumen = ft.Text("Seleccione un reactivo", color="blue_grey", size=12)
        txt_cant = ft.TextField(label="Cajas a pedir", width=150, keyboard_type="number")
        tabla = ft.DataTable(columns=[ft.DataColumn(ft.Text("Producto")), ft.DataColumn(ft.Text("Cant.")), ft.DataColumn(ft.Text("X"))])

        def actualizar_u():
            tabla.rows = [ft.DataRow(cells=[
                ft.DataCell(ft.Text(i["Alias"])), ft.DataCell(ft.Text(i["Cantidad"])),
                ft.DataCell(ft.IconButton(ft.Icons.DELETE, on_click=lambda _, idx=n: eliminar(idx)))
            ]) for n, i in enumerate(lista_carrito)]
            page.update()

        def eliminar(idx):
            lista_carrito.pop(idx); actualizar_u()

        def al_seleccionar(e):
            # Usamos tu lógica: el valor viene como "REF | ALIAS"
            if " | " in e.control.value:
                ref = e.control.value.split(" | ")[0].strip()
                inv = ultimo_inv.get(ref, {"A Bordo": 0, "Nuevos": 0, "Total Real": 0})
                lbl_resumen.value = f"STOCK ACTUAL: {inv['Nuevos']} Cajas | {inv['A Bordo']} en uso | TOTAL: {inv['Total Real']} pruebas"
                page.update()

        # --- TU FUNCIÓN DE FILTRADO ADAPTADA ---
        def filtrar_busqueda_pedido(e):
            texto = e.control.value.lower()
            # No hace falta refrescar el catálogo aquí porque ya lo tenemos arriba
            sugerencias_nuevas = []
            
            if len(texto) > 0:
                for ref, info in catalogo.items():
                    alias = str(info.get("Alias", "")).lower()
                    referencia = str(ref).lower()
                    
                    if texto in alias or texto in referencia:
                        texto_opcion = f"{ref} | {info.get('Alias', 'Sin nombre')}"
                        sugerencias_nuevas.append(
                            ft.AutoCompleteSuggestion(key=texto_opcion, value=texto_opcion)
                        )
                ac_busqueda.suggestions = sugerencias_nuevas
            else:
                ac_busqueda.suggestions = []
            page.update()

        ac_busqueda = ft.AutoComplete(
            on_select=al_seleccionar,
            on_change=filtrar_busqueda_pedido
        )

        def agregar(e):
            # Validamos que el valor tenga el formato "REF | ALIAS" antes de procesar
            if ac_busqueda.value and " | " in ac_busqueda.value and txt_cant.value:
                partes = ac_busqueda.value.split(" | ")
                ref = partes[0].strip()
                alias = partes[1].strip()
                
                lista_carrito.append({
                    "Referencia": ref, 
                    "Alias": alias, 
                    "Cantidad": txt_cant.value
                })
                ac_busqueda.value = ""; txt_cant.value = ""; lbl_resumen.value = "Seleccione un reactivo"
                actualizar_u()

        def enviar_click(e):
            if not lista_carrito: return
            
            # 1. Generamos el Excel
            ruta_xlsx = logica.procesar_y_guardar_pedido_final(unidad_seleccionada, lista_carrito)
            
            if ruta_xlsx:
                # 2. Generamos el PDF basado en ese Excel
                ruta_pdf = logica.convertir_excel_a_pdf(ruta_xlsx)
                
                # 3. Enviamos ambos
                archivos_a_enviar = [r for r in [ruta_xlsx, ruta_pdf] if r]
                
                if notificador.enviar_por_correo(archivos_a_enviar, unidad_seleccionada):
                    page.snack_bar = ft.SnackBar(ft.Text("✅ Pedido enviado (Excel + PDF)"))
                    page.snack_bar.open = True
                    mostrar_menu_principal()
                else:
                    page.snack_bar = ft.SnackBar(ft.Text("❌ Error al enviar correo"))
                    page.snack_bar.open = True
            page.update()

        page.add(
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: mostrar_menu_principal()), ft.Text("Nuevo Pedido", size=20)]),
            ft.Column([
                ft.Text("Buscador Dual (Referencia o Nombre):"), 
                ac_busqueda, 
                lbl_resumen, 
                txt_cant,
                ft.FilledButton("Agregar al Carrito", icon="add", on_click=agregar)
            ]),
            ft.Divider(), 
            tabla, 
            ft.Divider(),
            ft.FilledButton("ENVIAR PEDIDO", icon="send", bgcolor="green", color="white", on_click=enviar_click)
        )

    mostrar_pantalla_seleccion()

ft.run(main)