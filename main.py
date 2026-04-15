import flet as ft
from datetime import datetime
import logica
import notificador
import json
import os


def cargar_inventario():
    if os.path.exists("inventario.json"):
        with open("inventario.json", "r") as f:
            return json.load(f)

    return {
        "159": {
            "nombre": "Glucosa (GLUC3)",
            "presentacion": "Cartucho 800 pruebas",
            "en_uso": 1,
            "stock_nuevo": 5,
            "caducidad": "2026-05-20",
            "tipo": "reactivo"
        },
        "G-01": {
            "nombre": "Guantes de Nitrilo",
            "presentacion": "Caja 100 pz",
            "en_uso": 0,
            "stock_nuevo": 10,
            "caducidad": None,
            "tipo": "consumible"
        }
    }


STOCK_ACTUAL = cargar_inventario()


def guardar_inventario(datos):
    with open("inventario.json", "w") as f:
        json.dump(datos, f, indent=4)


def main(page: ft.Page):
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

    def mostrar_pantalla_seleccion():
        page.clean()
        opciones_clinicas = ["Clínica de Especialidades Condesa",
                             "Clínica de Especialidades Condesa Iztapalapa"]
        ac_clinica = ft.AutoComplete(suggestions=[ft.AutoCompleteSuggestion(
            key=c, value=c) for c in opciones_clinicas])

        def confirmar_seleccion(e):
            nonlocal unidad_seleccionada
            if ac_clinica.value:
                unidad_seleccionada = ac_clinica.value
                mostrar_menu_principal()
            else:
                page.snack_bar = ft.SnackBar(
                    ft.Text("⚠️ Selecciona una clínica válida"))
                page.snack_bar.open = True
                page.update()

        page.add(
            ft.Text("Sistema de Inventario", size=30, weight="bold"),
            ft.Text("Escriba el nombre de la unidad:"),
            ac_clinica,
            ft.ElevatedButton(
                "Continuar", on_click=confirmar_seleccion, icon="arrow_forward")
        )

    def mostrar_menu_principal():
        page.clean()
        lista_alertas = logica.verificar_alertas(STOCK_ACTUAL)
        columnas_alertas = [
            ft.Text(msj, color="orange", weight="bold", size=12) for msj in lista_alertas]

        page.add(
            ft.Text(f"Unidad: {unidad_seleccionada}",
                    size=18, weight="bold", color="blue"),
            ft.Container(content=ft.Column(columnas_alertas), visible=len(
                lista_alertas) > 0, padding=10, bgcolor="#FFF3E0", border_radius=10),
            ft.Divider(),
            ft.ElevatedButton("REALIZAR PEDIDO", icon=ft.Icons.ADD,
                              on_click=lambda _: mostrar_pantalla_pedido(), width=300, height=60),
            ft.ElevatedButton("GESTIONAR INVENTARIO", icon=ft.Icons.INVENTORY,
                              on_click=lambda _: mostrar_pantalla_inventario(), width=300, height=60),
            ft.TextButton("Cambiar de Clínica", on_click=reiniciar_app)
        )

    def mostrar_pantalla_pedido():
        page.clean()
        lbl_stock = ft.Text("Stock actual: --", italic=True, color="grey")
        txt_piezas = ft.TextField(
            label="Piezas solicitadas", width=150, keyboard_type="number")
        tabla_resumen = ft.DataTable(columns=[ft.DataColumn(ft.Text("Producto")), ft.DataColumn(
            ft.Text("Cant.")), ft.DataColumn(ft.Text("Borrar"))], rows=[])

        def actualizar_tabla():
            tabla_resumen.rows.clear()
            for i, item in enumerate(lista_pedido):
                btn_del = ft.Container(content=ft.Text("X", color="white", weight="bold"), bgcolor="red",
                                       padding=5, border_radius=5, on_click=lambda _, idx=i: eliminar_de_lista(idx))
                tabla_resumen.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(
                    item["Producto"])), ft.DataCell(ft.Text(item["Cantidad"])), ft.DataCell(btn_del)]))
            page.update()

        def eliminar_de_lista(idx):
            lista_pedido.pop(idx)
            actualizar_tabla()

        def al_seleccionar_reactivo(e):
            nombre = ac_reactivo.value
            info = STOCK_ACTUAL.get(nombre, {})
            stock = info.get("stock_nuevo", info.get("stock", 0))
            lbl_stock.value = f"Hay en stock: {stock}"
            page.update()

        ac_reactivo = ft.AutoComplete(suggestions=[ft.AutoCompleteSuggestion(
            key=k, value=k) for k in STOCK_ACTUAL.keys()], on_select=al_seleccionar_reactivo)

        def agregar_al_carrito(e):
            if ac_reactivo.value and txt_piezas.value:
                lista_pedido.append(
                    {"Producto": ac_reactivo.value, "Cantidad": txt_piezas.value})
                ac_reactivo.value, txt_piezas.value, lbl_stock.value = "", "", "Hay en stock: --"
                actualizar_tabla()

        def finalizar_pedido_click(e):
            if not lista_pedido:
                return
            page.snack_bar = ft.SnackBar(ft.Text("Enviando pedido..."))
            page.snack_bar.open = True
            page.update()
            try:
                archivo = None
                for item in lista_pedido:
                    datos = {"Fecha": datetime.now().strftime("%Y-%m-%d"), "Unidad": unidad_seleccionada,
                             "Producto": item["Producto"], "Cantidad": item["Cantidad"], "Estatus": "Pendiente"}
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
            ft.IconButton(icon=ft.Icons.ARROW_BACK,
                          on_click=lambda _: mostrar_menu_principal()),
            ft.Text(f"Pedido para: {unidad_seleccionada}",
                    size=20, weight="bold"),
            ac_reactivo, lbl_stock, txt_piezas,
            ft.ElevatedButton("Agregar a la lista", icon="add",
                              on_click=agregar_al_carrito),
            ft.Divider(), tabla_resumen, ft.Divider(),
            ft.ElevatedButton("ENVIAR PEDIDO", icon="send", bgcolor="green",
                              color="white", on_click=finalizar_pedido_click)
        )

    def mostrar_pantalla_inventario():
        page.clean()

        def ajustar_stock(nombre_reactivo, cambio):
            STOCK_ACTUAL[nombre_reactivo]["stock_nuevo"] += cambio
            if STOCK_ACTUAL[nombre_reactivo]["stock_nuevo"] < 0:
                STOCK_ACTUAL[nombre_reactivo]["stock_nuevo"] = 0
            guardar_inventario(STOCK_ACTUAL)
            logica.registrar_evento_ml(
                unidad_seleccionada, nombre_reactivo, cambio)
            mostrar_pantalla_inventario()

        page.add(ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: mostrar_menu_principal(
        )), ft.Text("Gestión de Inventario Físico", size=24, weight="bold"), ft.Divider())

        for ref, datos in STOCK_ACTUAL.items():
            page.add(
                ft.Container(
                    content=ft.Column([
                        ft.Row([ft.Text(f"{datos['nombre']}", weight="bold", size=16, expand=True), ft.Text(
                            f"Ref: {ref}", size=12, color="grey")]),
                        ft.Row([ft.Text(f"En Uso: {datos['en_uso']}", size=14), ft.Text(f"Stock: {datos['stock_nuevo']}", size=14, weight="bold"), ft.Text(
                            f"Vence: {datos['caducidad'] or 'N/A'}", size=12, italic=True)], alignment="spaceBetween"),
                        ft.Row([ft.IconButton(ft.Icons.REMOVE_CIRCLE, icon_color="red", on_click=lambda _, r=ref: ajustar_stock(r, -1)), ft.Text(str(datos['stock_nuevo']),
                               size=20, weight="bold"), ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color="green", on_click=lambda _, r=ref: ajustar_stock(r, 1))], alignment="center"),
                    ]),
                    padding=15, border=ft.border.all(1, "lightgrey"), border_radius=10, margin=ft.margin.only(bottom=10)
                )
            )

        def finalizar_auditoria_click(e):
            archivo = logica.exportar_auditoria_completa(
                unidad_seleccionada, STOCK_ACTUAL)
            page.snack_bar = ft.SnackBar(ft.Text(
                f"✅ Auditoría guardada como: {archivo}" if archivo else "❌ Error al guardar"), bgcolor="green" if archivo else "red")
            page.snack_bar.open = True
            page.update()

        page.add(ft.Divider(), ft.ElevatedButton("GENERAR REPORTE DE CAMPO", icon=ft.Icons.FILE_DOWNLOAD,
                 on_click=finalizar_auditoria_click, bgcolor=ft.Colors.BLUE_900, color="white", width=400, height=50))
        page.update()

    mostrar_pantalla_seleccion()


ft.app(target=main)
