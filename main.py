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
            val = e.control.value.replace("-", "")
            if len(val) >= 2: val = val[:2] + "-" + val[2:]
            if len(val) >= 5: val = val[:5] + "-" + val[5:]
            e.control.value = val[:10]
            actualizar_dato(ref, "caducidad", e.control.value)
            page.update()

        def eliminar_item(ref):
            if ref in sesion_auditoria:
                del sesion_auditoria[ref]
                actualizar_lista_visual()

        def finalizar_auditoria_click(e):
            # Esta es la función que guarda y regresa al menú
            ruta = logica.exportar_auditoria_roche(unidad_seleccionada, sesion_auditoria)
            if ruta:
                page.snack_bar = ft.SnackBar(ft.Text(f"✅ Reporte guardado: {ruta}"), bgcolor="green")
                page.snack_bar.open = True
                mostrar_menu_principal() # Regresa al inicio
            else:
                page.snack_bar = ft.SnackBar(ft.Text("❌ Error al guardar"), bgcolor="red")
                page.snack_bar.open = True
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
                    "ref": ref_id, # Guardamos la referencia real aparte
                    "nombre": info.get("alias", "Sin nombre"),
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
                    on_change=lambda e, r=id_unico: formatear_fecha(e, r),
                )

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
        opciones_full = [f"{ref} | {info.get('alias', '')}" for ref, info in CATALOGO.items()]

        def filtrar_busqueda(e):
            texto = e.control.value.lower()
            if len(texto) > 0:
                # El secreto aquí es actualizar 'suggestions' y llamar a page.update()
                ac_busqueda.suggestions = [
                    ft.AutoCompleteSuggestion(key=opt, value=opt) 
                    for opt in opciones_full if texto in opt.lower()
                ]
            else:
                ac_busqueda.suggestions = []
            page.update()

        ac_busqueda = ft.AutoComplete(
            on_select=agregar_al_inventario,
            on_change=filtrar_busqueda
        )

        contenedor_lista = ft.Column(scroll="auto", expand=True)

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
                on_click=finalizar_auditoria_click, # <--- AHORA SÍ VINCULADO
                bgcolor=ft.Colors.BLUE_900,
                color="white", width=400, height=50
            )
        )

    def mostrar_pantalla_pedido():
        page.clean()
        lbl_stock = ft.Text("Stock actual: --", italic=True, color="grey")
        txt_piezas = ft.TextField(label="Piezas solicitadas", width=150, keyboard_type="number")
        tabla_resumen = ft.DataTable(columns=[ft.DataColumn(ft.Text("Producto")), ft.DataColumn(ft.Text("Cant.")), ft.DataColumn(ft.Text("Borrar"))], rows=[])

        def actualizar_tabla():
            tabla_resumen.rows.clear()
            for i, item in enumerate(lista_pedido):
                btn_del = ft.IconButton(icon=ft.Icons.DELETE, icon_color="red", on_click=lambda _, idx=i: eliminar_de_lista(idx))
                tabla_resumen.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(item["Producto"])), ft.DataCell(ft.Text(item["Cantidad"])), ft.DataCell(btn_del)]))
            page.update()

        def eliminar_de_lista(idx):
            lista_pedido.pop(idx)
            actualizar_tabla()

        def al_seleccionar_reactivo(e):
            nombre = ac_reactivo.value
            info = STOCK_ACTUAL.get(nombre, {})
            stock = info.get("stock_nuevo", 0)
            lbl_stock.value = f"Hay en stock: {stock}"
            page.update()

        ac_reactivo = ft.AutoComplete(suggestions=[ft.AutoCompleteSuggestion(key=k, value=k) for k in STOCK_ACTUAL.keys()], on_select=al_seleccionar_reactivo)

        def agregar_al_carrito(e):
            if ac_reactivo.value and txt_piezas.value:
                lista_pedido.append({"Producto": ac_reactivo.value, "Cantidad": txt_piezas.value})
                ac_reactivo.value, txt_piezas.value, lbl_stock.value = "", "", "Hay en stock: --"
                actualizar_tabla()

        def enviar_pedido_click(e):
            if not lista_pedido: return
            page.snack_bar = ft.SnackBar(ft.Text("Enviando pedido..."))
            page.snack_bar.open = True
            page.update()
            try:
                archivo = None
                for item in lista_pedido:
                    datos = {"Fecha": datetime.now().strftime("%Y-%m-%d"), "Unidad": unidad_seleccionada, "Producto": item["Producto"], "Cantidad": item["Cantidad"], "Estatus": "Pendiente"}
                    archivo = logica.guardar_pedido(datos)
                if archivo:
                    notificador.enviar_por_correo(archivo)
                page.snack_bar = ft.SnackBar(ft.Text("✅ Pedido enviado"))
                page.snack_bar.open = True
                mostrar_menu_principal()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"❌ Error: {str(ex)}"))
                page.snack_bar.open = True
                page.update()

        page.add(
            ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: mostrar_menu_principal()),
            ft.Text(f"Pedido para: {unidad_seleccionada}", size=20, weight="bold"),
            ac_reactivo, lbl_stock, txt_piezas,
            ft.FilledButton("Agregar a la lista", icon="add", on_click=agregar_al_carrito),
            ft.Divider(), tabla_resumen, ft.Divider(),
            ft.FilledButton("ENVIAR PEDIDO", icon="send", bgcolor="green", color="white", on_click=enviar_pedido_click)
        )

    mostrar_pantalla_seleccion()

ft.run(main)