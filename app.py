from fastapi import FastAPI
from pydantic import BaseModel
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import json
from datetime import datetime

app = FastAPI()

# Cargar credenciales desde variable de entorno
creds_json = json.loads(os.environ["GOOGLE_CREDENTIALS"])
credentials = service_account.Credentials.from_service_account_info(
    creds_json,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

service = build("sheets", "v4", credentials=credentials)

SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]

class Gasto(BaseModel):
    fecha: str
    monto: float
    descripcion: str

@app.post("/agregar-gasto")
def agregar_gasto(gasto: Gasto):
    fecha_obj = datetime.strptime(gasto.fecha, "%d/%m/%Y")
    dia = fecha_obj.day
    mes_nombre = fecha_obj.strftime("%B %Y")

    # Traducir mes a español manualmente
    meses = {
        "January": "Enero",
        "February": "Febrero",
        "March": "Marzo",
        "April": "Abril",
        "May": "Mayo",
        "June": "Junio",
        "July": "Julio",
        "August": "Agosto",
        "September": "Septiembre",
        "October": "Octubre",
        "November": "Noviembre",
        "December": "Diciembre"
    }

    mes_hoja = meses[fecha_obj.strftime("%B")] + " " + str(fecha_obj.year)

    fila = 3 + ((dia - 1) // 2)
    columna_detalle = "M" if dia % 2 != 0 else "N"
    celda_detalle = f"'{mes_hoja}'!{columna_detalle}{fila}"
    celda_total = f"'{mes_hoja}'!O{fila}"

    # Leer total actual
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=celda_total
    ).execute()

    valores = result.get("values", [])
    total_actual = float(valores[0][0]) if valores else 0

    nuevo_total = total_actual + gasto.monto

    # Actualizar total
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=celda_total,
        valueInputOption="RAW",
        body={"values": [[nuevo_total]]}
    ).execute()

    # Leer detalle actual
    result_detalle = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=celda_detalle
    ).execute()

    detalle_actual = result_detalle.get("values", [])
    texto_actual = detalle_actual[0][0] if detalle_actual else ""

    nuevo_texto = texto_actual + f"\n+ ${gasto.monto} {gasto.descripcion}"

    # Actualizar detalle
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=celda_detalle,
        valueInputOption="RAW",
        body={"values": [[nuevo_texto]]}
    ).execute()

    return {"status": "ok", "nuevo_total": nuevo_total}
