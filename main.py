import flet as ft
from datetime import datetime
import logica 
import notificador

# Base de datos simulada de Stock (Actualizada con 5 reactivos)
STOCK_ACTUAL = {
    "Reactivo A (Glucosa)": 15,
    "Reactivo B (Urea)": 8,
    "Reactivo C (Creatinina)": 0,
    "Reactivo D (Colesterol)": 20,
    "Reactivo E (Triglicéridos)": 5,
}

def main(page: ft.Page):
    page.title = "Gestión de Reactivos - Condesa"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 450
    page.window_height = 850
    page.padding = 20
    
    # Variables de estado
    unidad_seleccionada = ""
    lista_pedido = []

    # --- NAVEGACIÓN ---
    def reiniciar_app(e):
        nonlocal lista_pedido, unidad_seleccionada
        lista_pedido.clear()
        unidad_seleccionada = ""
        mostrar_pantalla_seleccion()

    # --- PANTALLA 1: SELECCIÓN (Usando AutoComplete funcional) ---
    def mostrar_pantalla_seleccion():
        page.clean()
        opciones_clinicas = [
            "Clínica de Especialidades Condesa",
            "Clínica de Especialidades Condesa Iztapalapa"
        ]
        
        ac_clinica = ft.AutoComplete(
            suggestions=[ft.AutoCompleteSuggestion(key=c, value=c) for c in opciones_clinicas]
        )

        def confirmar_seleccion(e):
            nonlocal unidad_seleccionada
            if ac_clinica.value:
                unidad_seleccionada = ac_clinica.value
                mostrar_menu_principal()
            else:
                page.snack_bar = ft.SnackBar(ft.Text("⚠️ Selecciona una clínica válida"))
                page.snack_bar.open = True
                page.update()

        # Estructura plana: elementos pasados directamente a page.add
        page.add(
            ft.Text("Sistema de Inventario", size=30, weight="bold"),
            ft.Text("Escriba el nombre de la unidad:"),
            ac_clinica,
            ft.ElevatedButton("Continuar", on_click=confirmar_seleccion, icon="arrow_forward")
        )

    # --- PANTALLA 2: MENÚ ---
    def mostrar_menu_principal():
        page.clean()
        page.add(
            ft.Text(f"Unidad: {unidad_seleccionada}", size=18, weight="bold", color="blue"),
            ft.Divider(),
            ft.ElevatedButton(
                "REALIZAR PEDIDO", 
                icon="shopping_cart", 
                on_click=lambda _: mostrar_pantalla_pedido(),
                width=300, height=60
            ),
            ft.ElevatedButton(
                "GESTIONAR INVENTARIO", 
                icon="inventory", 
                on_click=lambda _: mostrar_pantalla_inventario(),
                width=300, height=60
            ),
            ft.TextButton("Cambiar de Clínica", on_click=reiniciar_app)
        )

    # --- PANTALLA 3: PEDIDO ---
    def mostrar_pantalla_pedido():
        page.clean()
        
        lbl_stock = ft.Text("Stock actual: --", italic=True, color="grey")
        txt_piezas = ft.TextField(label="Piezas solicitadas", width=150, keyboard_type="number")
        
        tabla_resumen = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Producto")),
                ft.DataColumn(ft.Text("Cant.")),
                ft.DataColumn(ft.Text("Borrar")),
            ],
            rows=[]
        )

        def actualizar_tabla():
            tabla_resumen.rows.clear()
            for i, item in enumerate(lista_pedido):
                # Botón de borrar minimalista (X)
                btn_del = ft.Container(
                    content=ft.Text("X", color="white", weight="bold"),
                    bgcolor="red",
                    padding=5,
                    border_radius=5,
                    on_click=lambda _, idx=i: eliminar_de_lista(idx)
                )
                tabla_resumen.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(item["Producto"])),
                        ft.DataCell(ft.Text(item["Cantidad"])),
                        ft.DataCell(btn_del),
                    ])
                )
            page.update()

        def eliminar_de_lista(idx):
            lista_pedido.pop(idx)
            actualizar_tabla()

        def al_seleccionar_reactivo(e):
            nombre = ac_reactivo.value
            stock = STOCK_ACTUAL.get(nombre, "0")
            lbl_stock.value = f"Hay en stock: {stock}"
            page.update()

        ac_reactivo = ft.AutoComplete(
            suggestions=[ft.AutoCompleteSuggestion(key=k, value=k) for k in STOCK_ACTUAL.keys()],
            on_select=al_seleccionar_reactivo
        )

        def agregar_al_carrito(e):
            if ac_reactivo.value and txt_piezas.value:
                lista_pedido.append({"Producto": ac_reactivo.value, "Cantidad": txt_piezas.value})
                ac_reactivo.value = ""
                txt_piezas.value = ""
                lbl_stock.value = "Hay en stock: --"
                actualizar_tabla()

        def finalizar_pedido_click(e):
            if not lista_pedido: return
            page.snack_bar = ft.SnackBar(ft.Text("Enviando pedido..."))
            page.snack_bar.open = True
            page.update()
            try: 
                archivo = None
                for item in lista_pedido:
                    datos = {
                        "Fecha": datetime.now().strftime("%Y-%m-%d"),
                        "Unidad": unidad_seleccionada,
                        "Producto": item["Producto"],
                        "Cantidad": item["Cantidad"],
                        "Estatus": "Pendiente"
                    }
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

        # IMPORTANTE: Agregamos elementos uno por uno (Estructura Plana)
        page.add(
            ft.IconButton(icon="arrow_back", on_click=lambda _: mostrar_menu_principal()),
            ft.Text(f"Pedido para: {unidad_seleccionada}", size=20, weight="bold"),
            ft.Text("Seleccione Producto:"),
            ac_reactivo,
            lbl_stock,
            txt_piezas,
            ft.ElevatedButton("Agregar a la lista", icon="add", on_click=agregar_al_carrito),
            ft.Divider(),
            ft.Text("Resumen del pedido:", weight="bold"),
            tabla_resumen,
            ft.Divider(),
            ft.ElevatedButton("FINALIZAR ENVÍO", icon="send", bgcolor="green", color="white", on_click=finalizar_pedido_click)
        )

    # --- PANTALLA 4: INVENTARIO ---
    def mostrar_pantalla_inventario():
        page.clean()
        page.add(
            ft.IconButton(icon="arrow_back", on_click=lambda _: mostrar_menu_principal()),
            ft.Text("Módulo de Inventario", size=20, weight="bold"),
            ft.Text("Próximo paso: Gestión de caducidades.", italic=True)
        )

    mostrar_pantalla_seleccion()

ft.app(target=main)