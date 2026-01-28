import datetime as dt
from dataclasses import dataclass

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Calendario judicial - Andalucía y Madrid",
    page_icon="⚖️",
)


@dataclass(frozen=True)
class ProcedureRule:
    name: str
    exclude_august: bool
    include_weekends: bool
    include_december_24_31: bool


PROCEDURE_RULES = {
    "Civil": ProcedureRule(
        name="Civil",
        exclude_august=True,
        include_weekends=False,
        include_december_24_31=False,
    ),
    "Contencioso-administrativo": ProcedureRule(
        name="Contencioso-administrativo",
        exclude_august=True,
        include_weekends=False,
        include_december_24_31=False,
    ),
    "Social": ProcedureRule(
        name="Social",
        exclude_august=True,
        include_weekends=False,
        include_december_24_31=False,
    ),
    "Penal": ProcedureRule(
        name="Penal",
        exclude_august=False,
        include_weekends=False,
        include_december_24_31=False,
    ),
}


MADRID_PARTIES = [
    "Alcalá de Henares",
    "Alcobendas",
    "Arganda del Rey",
    "Aranjuez",
    "Collado Villalba",
    "Coslada",
    "Fuenlabrada",
    "Getafe",
    "Leganés",
    "Madrid",
    "Móstoles",
    "Navalcarnero",
    "Parla",
    "Pozuelo de Alarcón",
    "San Lorenzo de El Escorial",
    "Torrejón de Ardoz",
    "Valdemoro",
]

ANDALUCIA_PROVINCES = [
    "Almería",
    "Cádiz",
    "Córdoba",
    "Granada",
    "Huelva",
    "Jaén",
    "Málaga",
    "Sevilla",
]


NATIONAL_HOLIDAYS = [
    (1, 1, "Año Nuevo"),
    (1, 6, "Epifanía del Señor"),
    (5, 1, "Fiesta del Trabajo"),
    (8, 15, "Asunción de la Virgen"),
    (10, 12, "Fiesta Nacional de España"),
    (11, 1, "Todos los Santos"),
    (12, 6, "Día de la Constitución"),
    (12, 8, "Inmaculada Concepción"),
    (12, 25, "Navidad"),
]

REGIONAL_HOLIDAYS = {
    "Madrid": [(5, 2, "Fiesta de la Comunidad de Madrid")],
    "Andalucía": [(2, 28, "Día de Andalucía")],
}


def easter_sunday(year: int) -> dt.date:
    """Anonymous Gregorian algorithm."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return dt.date(year, month, day)


def regional_holidays(region: str) -> list[tuple[int, int, str]]:
    return REGIONAL_HOLIDAYS.get(region, [])


def judicial_holidays(year: int, region: str) -> list[tuple[dt.date, str]]:
    holidays = []
    for month, day, name in NATIONAL_HOLIDAYS:
        holidays.append((dt.date(year, month, day), name))

    for month, day, name in regional_holidays(region):
        holidays.append((dt.date(year, month, day), name))

    easter = easter_sunday(year)
    holy_thursday = easter - dt.timedelta(days=3)
    good_friday = easter - dt.timedelta(days=2)
    holidays.append((holy_thursday, "Jueves Santo"))
    holidays.append((good_friday, "Viernes Santo"))

    return holidays


def parse_custom_holidays(raw_text: str) -> list[dt.date]:
    if not raw_text.strip():
        return []

    dates: list[dt.date] = []
    for chunk in raw_text.split(","):
        value = chunk.strip()
        if not value:
            continue
        try:
            dates.append(dt.date.fromisoformat(value))
        except ValueError:
            st.warning(
                f"No se pudo interpretar la fecha '{value}'. Usa el formato AAAA-MM-DD.")
    return dates


def is_working_day(date: dt.date, holidays: set[dt.date], rule: ProcedureRule) -> bool:
    if not rule.include_weekends and date.weekday() >= 5:
        return False

    if not rule.include_december_24_31 and (date.month, date.day) in {(12, 24), (12, 31)}:
        return False

    if rule.exclude_august and date.month == 8:
        return False

    if date in holidays:
        return False

    return True


st.title("⚖️ Calculadora de días hábiles judiciales")
st.markdown(
    """
    Calcula los días hábiles judiciales en España para Andalucía y Madrid.
    El cálculo se ajusta al **tipo de procedimiento** y permite añadir festivos locales
    del partido judicial.
    """
)

st.info(
    """
    **Nota**: Los calendarios judiciales pueden variar por acuerdos locales.
    Este cálculo aplica festivos nacionales, autonómicos (Andalucía/Madrid),
    Jueves y Viernes Santo, y los criterios del procedimiento.
    Añade festivos municipales si es necesario.
    """
)

col_a, col_b, col_c = st.columns(3)

with col_a:
    region = st.selectbox("Comunidad autónoma", ["Andalucía", "Madrid"])

with col_b:
    procedure = st.selectbox("Tipo de procedimiento", list(PROCEDURE_RULES.keys()))

with col_c:
    if region == "Madrid":
        selected_party = st.selectbox("Partido judicial", MADRID_PARTIES + ["Otro"])
        if selected_party == "Otro":
            party = st.text_input(
                "Partido judicial (opcional)",
                placeholder="Ej. San Martín de Valdeiglesias...",
            )
        else:
            party = selected_party
    else:
        province = st.selectbox("Provincia", ANDALUCIA_PROVINCES)
        party = st.text_input(
            "Partido judicial (opcional)",
            placeholder="Ej. Sevilla, Málaga, Almería...",
        )

custom_holidays_input = st.text_area(
    "Festivos locales (opcional, separados por coma, formato AAAA-MM-DD)",
    placeholder="2024-06-13, 2024-09-24",
)

range_col_a, range_col_b = st.columns(2)

def default_dates() -> tuple[dt.date, dt.date]:
    today = dt.date.today()
    start_date = dt.date(today.year, 1, 1)
    end_date = dt.date(today.year, 12, 31)
    return start_date, end_date


with range_col_a:
    start_date = st.date_input("Fecha de inicio", value=default_dates()[0])
with range_col_b:
    end_date = st.date_input("Fecha de fin", value=default_dates()[1])

if start_date > end_date:
    st.error("La fecha de inicio no puede ser posterior a la fecha de fin.")
    st.stop()

rule = PROCEDURE_RULES[procedure]

custom_holidays = parse_custom_holidays(custom_holidays_input)

years = range(start_date.year, end_date.year + 1)
holiday_details = []
for year in years:
    holiday_details.extend(judicial_holidays(year, region))

holiday_dates = {date for date, _ in holiday_details}
holiday_dates.update(custom_holidays)

calendar = pd.date_range(start=start_date, end=end_date, freq="D")

def build_calendar_frame() -> pd.DataFrame:
    weekdays = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    rows = []
    for day in calendar:
        date = day.date()
        reason = ""
        if date in holiday_dates:
            reason = "Festivo"
        elif not rule.include_weekends and date.weekday() >= 5:
            reason = "Fin de semana"
        elif rule.exclude_august and date.month == 8:
            reason = "Agosto inhábil"
        elif not rule.include_december_24_31 and (date.month, date.day) in {(12, 24), (12, 31)}:
            reason = "Inhábil 24/31 dic."

        rows.append(
            {
                "Fecha": date,
                "Día": weekdays[date.weekday()],
                "Hábil": is_working_day(date, holiday_dates, rule),
                "Motivo no hábil": reason,
            }
        )
    return pd.DataFrame(rows)


calendar_df = build_calendar_frame()

working_days = calendar_df[calendar_df["Hábil"]]
non_working_days = calendar_df[~calendar_df["Hábil"]]
holiday_count = sum(1 for day in calendar if day.date() in holiday_dates)

st.subheader("Resumen")

summary_cols = st.columns(4)
summary_cols[0].metric("Total días", len(calendar_df))
summary_cols[1].metric("Días hábiles", len(working_days))
summary_cols[2].metric("Días inhábiles", len(non_working_days))
summary_cols[3].metric("Festivos oficiales/locales", holiday_count)

if region == "Andalucía":
    st.markdown(
        f"**Provincia:** {province}  \n**Partido judicial:** {party if party else 'Sin especificar'}"
    )
else:
    st.markdown(
        f"**Partido judicial:** {party if party else 'Sin especificar'}"
    )

st.subheader("Detalle de días")

st.dataframe(
    calendar_df,
    width="stretch",
    height=420,
)

st.download_button(
    "Descargar calendario (CSV)",
    data=calendar_df.to_csv(index=False).encode("utf-8"),
    file_name="calendario_judicial.csv",
    mime="text/csv",
)

st.subheader("Festivos considerados")

holiday_df = pd.DataFrame(
    sorted(holiday_dates),
    columns=["Fecha"],
)

holiday_df["Tipo"] = holiday_df["Fecha"].apply(
    lambda date: "Local" if date in custom_holidays else "Oficial"
)

st.dataframe(holiday_df, width="stretch", height=240)

st.caption(
    "Este cálculo es orientativo. Verifica siempre los acuerdos de los órganos judiciales."
)
