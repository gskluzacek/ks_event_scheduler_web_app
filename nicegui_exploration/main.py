from nicegui import ui


def main():
    ui.label('Hello NiceGUI!')
    ui.button('BUTTON', on_click=lambda: ui.notify('button was pressed'))

    ui.run()


if __name__ in {"__main__", "__mp_main__"}:
    main()
