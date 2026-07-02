"""
Módulo de transformación de órdenes según reglas de negocio
"""
import re
import sys
import pandas as pd
from config import (
    SHINE_TASK_MAP,
    SHINE_CLIENT_MAP,
    SHINE_SUBDIVISION_MAP,
    APEX_INSTRUCTION_REGEX
)

def log(msg):
    """Log que SÍ se ve en Streamlit Cloud"""
    sys.stderr.write(f"{msg}\n")
    sys.stderr.flush()


def transformar_ordenes(df_raw: pd.DataFrame, config: str) -> pd.DataFrame:
    """
    Transforma el DataFrame crudo según las reglas del cliente
    """
    try:
        log(f"📊 DataFrame RAW: {len(df_raw)} filas, {len(df_raw.columns)} columnas")
        log(f"📋 Primeras 5 filas del RAW:")
        for i in range(min(5, len(df_raw))):
            log(f"   Fila {i}: {list(df_raw.iloc[i])[:5]}...")

        header_row_idx = None
        for i in range(min(100, len(df_raw))):
            row_values = [str(x) for x in df_raw.iloc[i]]
            for val in row_values:
                if 'Builder Order' in val and len(val) < 100:
                    header_row_idx = i
                    log(f"📋 HEADERS ENCONTRADOS EN FILA: {i}")
                    log(f"📋 Headers: {row_values[:10]}")
                    break
            if header_row_idx is not None:
                break

        if header_row_idx is None:
            raise Exception("No se encontró la fila de headers con 'Builder Order #'")

        headers = [str(x).strip().replace('\n', ' ') for x in df_raw.iloc[header_row_idx]]
        df = df_raw.iloc[header_row_idx + 1:].reset_index(drop=True)
        df.columns = headers
        log(f"📊 DataFrame de datos: {len(df)} filas desde fila {header_row_idx + 1}")

        df = df.map(lambda v: str(v).strip().replace('\n', ' '))

        log(f"✅ COLUMNAS DESPUÉS DE ASIGNAR: {list(df.columns)}")

        rename_map = {
            'Builder Order #': 'Number order',
            'Account': 'Client Name',
            'Subdivision': 'Job title',
            'Lot / Block Plan/Elv/Swing': 'lote number',
            'Job Address': 'Job Address',
            'Task Task Filter': 'instruction',
            'Total Excl Tax': 'total',
            'Request Acknowledged Actual': 'Start Date'
        }

        df.rename(columns=rename_map, inplace=True)
        log(f"✅ DESPUÉS DE RENOMBRAR: {list(df.columns)}")

        drop_cols = [c for c in df.columns if any(x in c for x in ['Supplier Order', 'Order Status', 'Builder Status'])]
        df.drop(columns=drop_cols, inplace=True)

        if 'Start Date' in df.columns:
            df['Start Date'] = df['Start Date'].apply(
                lambda x: re.search(r"\d{1,2}/\d{1,2}/\d{4}", x).group(0)
                if re.search(r"\d{1,2}/\d{1,2}/\d{4}", x) else ''
            )
        else:
            date_cols = [col for col in df.columns if 'date' in col.lower() or 'request' in col.lower() or 'acknowledged' in col.lower()]
            log(f"⚠️ 'Start Date' no encontrada. Columnas con fecha disponibles: {date_cols}")

            if date_cols:
                df['Start Date'] = df[date_cols[0]].apply(
                    lambda x: re.search(r"\d{1,2}/\d{1,2}/\d{4}", str(x)).group(0)
                    if re.search(r"\d{1,2}/\d{1,2}/\d{4}", str(x)) else ''
                )
            else:
                df['Start Date'] = ''

        df['Full Property Address'] = df['Job Address']\
            .str.replace("Lennar Options from CRM", "", regex=False)\
            .str.strip()
        df.drop(columns=['Job Address'], inplace=True)

        df['Client Name'] = df['Client Name'].apply(
            lambda x: next((rep for pat, rep in SHINE_CLIENT_MAP.items() if re.match(pat, x)), x)
        )

        df['instruction'] = df['instruction']\
            .str.replace(r"\s*[\(\[].*?[\)\]]", "", regex=True)\
            .str.strip()
        df['instruction'] = df['instruction'].apply(lambda x: SHINE_TASK_MAP.get(x, x))

        if config == 'Apex':
            df['instruction'] = df['instruction'].str.replace(r'^Concrete Labor -\s*', '', regex=True)
            for pattern, repl in APEX_INSTRUCTION_REGEX:
                df['instruction'] = df['instruction'].str.replace(pattern, repl, regex=True)

        df['job_title_clean'] = df['Job title']\
            .str.replace(r'^GAL\s*-\s*', '', regex=True)\
            .str.replace(r'\s*-\s*\d+$', '', regex=True)\
            .str.strip()

        df['lote number'] = df['lote number'].str.partition('/')[0].str.strip()

        df['Job title Final'] = df.apply(
            lambda r: f"{r['instruction']} / LOT {r['lote number']} / {r['job_title_clean']} / {r['Number order']}",
            axis=1
        )

        df = df[
            df['Number order'].notna() &
            df['Number order'].str.strip().ne('') &
            (df['Number order'].str.lower() != 'nan')
        ]

        final = df[['Client Name', 'Job title Final', 'Full Property Address', 'total', 'Start Date']]
        final = final[~final.apply(lambda row: row.astype(str).str.lower().eq('nan').any(), axis=1)]

        final = final[
            ~final['total'].str.contains('No orders found', case=False, na=False) &
            ~final['total'].str.lower().str.contains('function|script|var |return', case=False, na=False)
        ]

        final = final[
            final['total'].str.contains(r'[\$\d]', regex=True, na=False)
        ]

        log(f"✅ Procesamiento completado: {len(final)} órdenes")
        return final

    except Exception as e:
        log(f"❌ Error en transformación: {str(e)}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise Exception(f"Error al procesar órdenes: {str(e)}")
